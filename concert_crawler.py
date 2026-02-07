"""
台灣演唱會資訊爬蟲
專注 KKTIX 與 年代售票 (ticket.com.tw)
整合 Google Gemini AI 解析 HTML
"""
import argparse
import glob
import os
import sys
import time
import json
from datetime import datetime
from typing import List, Dict

import pandas as pd
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Gemini AI 整合
import google.generativeai as genai

gemini_model = None


def get_gemini_model():
    """Lazily init Gemini model using env var GEMINI_API_KEY."""
    global gemini_model
    if gemini_model:
        return gemini_model

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("  ⚠ 未設定 GEMINI_API_KEY，跳過 Gemini 解析")
        return None

    try:
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        return gemini_model
    except Exception as e:
        print(f"  ⚠ Gemini 初始化失敗: {e}")
        return None


def parse_html_with_gemini(html_content: str, site_name: str) -> List[dict]:
    """使用 Gemini AI 直接解析 HTML 提取演唱會資訊"""
    if not html_content or len(html_content) < 100:
        return []

    model = get_gemini_model()
    if not model:
        return []

    try:
        prompt = f"""
請從以下 HTML 中提取所有演唱會或音樂會資訊。
網站: {site_name}

返回格式必須是 JSON 數組，每個物件包含：
{{"artist": "藝人名稱", "date": "日期時間或'未公布'", "venue": "地點或'未公布'", "url": "連結"}}

只返回有效的 JSON 數組，不要任何其他文字、解釋或 markdown。
如果找不到任何演唱會資訊，返回空數組 []

HTML 內容（前 3000 字）：
{html_content[:3000]}
"""
        response = model.generate_content(prompt)

        response_text = response.text.strip()

        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.split('```')[0]

        response_text = response_text.strip()

        if not response_text or response_text == '[]':
            return []

        try:
            concerts = json.loads(response_text)
        except json.JSONDecodeError:
            concerts = [json.loads(response_text)]

        valid_concerts = []
        if isinstance(concerts, list):
            for item in concerts:
                if isinstance(item, dict) and item.get('artist') and item.get('url'):
                    valid_concerts.append({
                        '演出藝人': str(item.get('artist', '未知')).strip(),
                        '演出時間': str(item.get('date', '未公布')).strip(),
                        '演出地點': str(item.get('venue', '未公布')).strip(),
                        '網址': str(item.get('url', '')).strip(),
                    })

        return valid_concerts
    except Exception as e:
        print(f"  ✗ Gemini 解析失敗: {type(e).__name__}: {str(e)[:100]}")
        return []


def launch_browser_with_fallback(playwright_instance, force_headful=False):
    """Try multiple launch strategies to bypass strict environments."""
    if force_headful:
        # 當需要手動驗證時，優先嘗試 headful 模式
        attempts = [
            {"headless": False, "args": ["--disable-blink-features=AutomationControlled"]},
            {"channel": "chrome", "headless": False},
            {"channel": "msedge", "headless": False},
            {"headless": True},
        ]
    else:
        attempts = [
            {"headless": True, "args": ["--disable-blink-features=AutomationControlled"]},
            {"channel": "chrome", "headless": True},
            {"channel": "msedge", "headless": True},
            {"headless": False},
            {"channel": "chrome", "headless": False},
            {"channel": "msedge", "headless": False},
        ]
    last_error = None
    for opts in attempts:
        try:
            return playwright_instance.chromium.launch(**opts)
        except Exception as e:
            last_error = e
            continue
    raise last_error if last_error else RuntimeError("Playwright launch failed")


def load_state_if_exists(path: str):
    return path if os.path.exists(path) else None


def wait_manual_verification(message="請在開啟的瀏覽器完成驗證/登入後按 Enter 繼續..."):
    try:
        input(message)
    except (EOFError, KeyboardInterrupt):
        # 非互動環境或使用者中斷則略過
        pass


def parse_detail_html_with_gemini(html: str, site_name: str, timeout: int = 30) -> Dict:
    """
    使用 Google Gemini AI 解析 HTML 並提取演唱會資訊
    
    Args:
        html: HTML 內容
        site_name: 網站名稱 (用於提示詞)
        timeout: 超時秒數
    
    Returns:
        {
            "藝人": "...",
            "時間": "...",
            "地點": "...",
            "票價": "...",
            "簡介": "..."
        }
    """
    try:
        prompt = f"""
請從以下 {site_name} 網站的 HTML 中提取演唱會資訊。
返回一個 JSON 物件，包含以下欄位（如果找不到則填 "未公布"）：
- 藝人: 演出藝人名稱
- 時間: 演出時間（格式: YYYY/MM/DD HH:MM）
- 地點: 演出地點/場地
- 票價: 票價資訊
- 簡介: 演唱會簡介

HTML 內容：
{html[:5000]}

只返回 JSON，不要其他文字。
"""
        model = get_gemini_model()
        if not model:
            return {}
        response = model.generate_content(prompt)
        try:
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            # 如果 AI 返回的不是純 JSON，嘗試提取 JSON 部分
            import re
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
    except Exception as e:
        print(f"  ⚠ Gemini 解析失敗: {e}")
        return {}


class ConcertCrawler:
    """基底爬蟲類別"""

    def __init__(self, timeout: int = 10):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        }
        self.concerts: List[dict] = []
        self.base_url = ""
        self.site_name = ""
        # 每站點請求逾時（秒）
        self.timeout = timeout

    def crawl(self) -> List[dict]:
        raise NotImplementedError


class KKTIXCrawler(ConcertCrawler):
    """KKTIX 爬蟲 (等級1)"""

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.base_url = "https://kktix.com"
        self.site_name = "KKTIX"

    def crawl(self) -> List[dict]:
        print(f"\n[等級1] 開始爬取 {self.site_name}...")
        self.concerts = []
        state_file = "ticket_state.json"
        headless_env = os.getenv("PLAYWRIGHT_HEADLESS", "1")
        force_headful = headless_env.strip() == "0"
        state_file = "kktix_state.json"
        headless_env = os.getenv("PLAYWRIGHT_HEADLESS", "1")
        force_headful = headless_env.strip() == "0"

        json_urls = [
            f"{self.base_url}/events.json?per_page=50",
            f"{self.base_url}/events.json",
            f"{self.base_url}/events.json?locale=zh-TW",
            f"{self.base_url}/events.json?locale=zh",
        ]
        for ju in json_urls:
            try:
                r = requests.get(ju, headers=self.headers, timeout=self.timeout)
                if r.status_code != 200:
                    continue
                payload = r.json()
                items = payload if isinstance(payload, list) else payload.get("data") or payload.get("events") or []
                for it in items:
                    title = (it.get("title") or it.get("name") or "").strip()
                    date = (it.get("start_at") or it.get("time") or it.get("time_range") or "").strip()
                    venue = it.get("venue")
                    if isinstance(venue, dict):
                        venue = venue.get("name")
                    venue = (venue or it.get("location") or "").strip()
                    url = (it.get("url") or it.get("event_url") or it.get("web_url") or "").strip()
                    if url and not url.startswith("http"):
                        url = self.base_url + url
                    if not url:
                        slug = it.get("slug") or it.get("id")
                        url = f"{self.base_url}/events/{slug}" if slug else self.base_url
                    if any([title, date, venue, url]):
                        self.concerts.append(
                            {
                                "來源網站": self.site_name,
                                "演出藝人": title or "未知藝人",
                                "演出時間": date or "未公布",
                                "演出地點": venue or "未公布",
                                "網址": url,
                                "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            }
                        )
                if self.concerts:
                    break
            except Exception:
                continue

        if not self.concerts:
            list_urls = [f"{self.base_url}/events", f"{self.base_url}/events?category=music"]
            for lu in list_urls:
                try:
                    rr = requests.get(lu, headers=self.headers, timeout=self.timeout)
                    if rr.status_code != 200:
                        continue
                    soup = BeautifulSoup(rr.text, "lxml")
                    cards = soup.select(
                        "article.event, div.event-item, li.event-item, div.card, article.card, ul.events-list li"
                    )
                    for ev in cards:
                        a = ev.find("a")
                        url = a.get("href") if a else ""
                        if url and not url.startswith("http"):
                            url = self.base_url + url
                        title_el = ev.find(["h3", "h2", "h4"])
                        title = title_el.get_text(strip=True) if title_el else ""
                        time_el = ev.find("time")
                        date = time_el.get("datetime") if (time_el and time_el.get("datetime")) else ""
                        if not date:
                            dt_el = ev.select_one(".date, .time")
                            date = dt_el.get_text(strip=True) if dt_el else ""
                        ven_el = ev.select_one(".venue, .place, .location")
                        venue = ven_el.get_text(strip=True) if ven_el else ""
                        if any([title, date, venue, url]):
                            self.concerts.append(
                                {
                                    "來源網站": self.site_name,
                                    "演出藝人": title or "未知藝人",
                                    "演出時間": date or "未公布",
                                    "演出地點": venue or "未公布",
                                    "網址": url or self.base_url,
                                    "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                }
                            )
                    if self.concerts:
                        break
                except Exception:
                    continue

        if not self.concerts:
            try:
                # 嘗試多個不需登入的公開頁面
                public_urls = [
                    f"{self.base_url}",  # 首頁
                    f"{self.base_url}/explore",  # 探索頁
                    f"{self.base_url}/events",  # 活動列表
                ]
                soup = None
                for pub_url in public_urls:
                    try:
                        with sync_playwright() as p:
                            browser = launch_browser_with_fallback(p, force_headful=force_headful)
                            context = browser.new_context(storage_state=load_state_if_exists(state_file))
                            page = context.new_page()
                            page.goto(pub_url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
                            try:
                                page.wait_for_load_state("networkidle", timeout=self.timeout * 1000)
                            except Exception:
                                page.wait_for_timeout(min(5000, self.timeout * 1000))  # 給更多時間載入
                            soup = BeautifulSoup(page.content(), "lxml")
                            context.storage_state(path=state_file)
                            browser.close()
                            # 檢查是否有活動連結
                            test_links = soup.select("a[href*='/events/']")
                            if test_links:
                                print(f"  ✓ 在 {pub_url} 找到 {len(test_links)} 個活動連結")
                                break
                    except Exception as e:
                        print(f"  ⚠ {pub_url} 失敗: {e}")
                        continue
                
                if not soup:
                    raise RuntimeError("無法載入任何 KKTIX 頁面")
                links = soup.select("a[href*='/events/']")[:15]
                for a in links:
                    url = a.get("href") or ""
                    if url and not url.startswith("http"):
                        url = self.base_url + url
                    title = a.get_text(strip=True)
                    date = venue = ""
                    if url:
                        try:
                            with sync_playwright() as p:
                                browser = launch_browser_with_fallback(p, force_headful=force_headful)
                                context = browser.new_context(storage_state=load_state_if_exists(state_file))
                                pg = context.new_page()
                                pg.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
                                try:
                                    pg.wait_for_load_state("networkidle", timeout=self.timeout * 1000)
                                except Exception:
                                    pg.wait_for_timeout(min(3000, self.timeout * 1000))
                                detail = BeautifulSoup(pg.content(), "lxml")
                                context.storage_state(path=state_file)
                                browser.close()
                            t_el = detail.select_one("time[datetime], .event-date, .date, .time")
                            date = t_el.get("datetime") if (t_el and t_el.has_attr("datetime")) else (
                                t_el.get_text(strip=True) if t_el else ""
                            )
                            v_el = detail.select_one(".venue, .place, .location, .event-venue")
                            venue = v_el.get_text(strip=True) if v_el else ""
                            if not title:
                                t2 = detail.select_one("h1, .event-title, .page-title")
                                title = t2.get_text(strip=True) if t2 else title
                        except Exception:
                            pass
                    if any([title, date, venue, url]):
                        self.concerts.append(
                            {
                                "來源網站": self.site_name,
                                "演出藝人": title or "未知藝人",
                                "演出時間": date or "未公布",
                                "演出地點": venue or "未公布",
                                "網址": url or self.base_url,
                                "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            }
                        )
            except Exception as e:
                print(f"  ⚠ KKTIX Playwright 失敗: {e}")

        print(f"✓ {self.site_name} 爬取完成，共 {len(self.concerts)} 筆資料")
        if not self.concerts:
            self.concerts.append(
                {
                    "來源網站": self.site_name,
                    "演出藝人": "（待公佈）",
                    "演出時間": "未公布",
                    "演出地點": "未公布",
                    "網址": self.base_url + "/events",
                    "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        return self.concerts


class TicketCrawler(ConcertCrawler):
    """年代售票爬蟲 (等級1)"""

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.base_url = "https://ticket.com.tw"
        self.site_name = "年代售票"

    def crawl(self) -> List[dict]:
        print(f"\n[等級1] 開始爬取 {self.site_name}...")
        self.concerts = []

        list_urls = [
            f"{self.base_url}/Concert",
            f"{self.base_url}/category/Concert",
            f"{self.base_url}/search?type=concert",
        ]
        html = None
        for lu in list_urls:
            try:
                resp = requests.get(lu, headers=self.headers, timeout=self.timeout)
                if resp.status_code == 200 and "html" in resp.headers.get("Content-Type", "").lower():
                    html = resp.text
                    break
            except Exception:
                continue

        if not html:
            try:
                with sync_playwright() as p:
                    browser = launch_browser_with_fallback(p, force_headful=force_headful)
                    context = browser.new_context(storage_state=load_state_if_exists(state_file))
                    page = context.new_page()
                    page.goto(f"{self.base_url}/Concert", timeout=self.timeout * 1000, wait_until="domcontentloaded")
                    try:
                        page.wait_for_load_state("networkidle", timeout=self.timeout * 1000)
                    except Exception:
                        page.wait_for_timeout(min(5000, self.timeout * 1000))
                    html = page.content()
                    context.storage_state(path=state_file)
                    browser.close()
            except Exception as e:
                print(f"✗ 無法取得年代售票列表頁: {e}")
                return self._fallback_placeholder()

        soup = BeautifulSoup(html, "lxml")
        candidates = []
        candidates.extend(soup.select("div.concert-item, li.concert-item"))
        candidates.extend(soup.select("div.item, li.item"))
        candidates.extend(soup.select("div.event, li.event"))
        candidates = candidates or soup.select("a[href*='/activity/']")

        def norm(el):
            return el.get_text(strip=True) if el else ""

        for c in candidates:
            try:
                a = c.find("a") or (c if c.name == "a" else None)
                link = a.get("href") if a else ""
                if link and not link.startswith("http"):
                    link = self.base_url + link
                title = norm(c.find("h4")) or norm(c.find("h3")) or norm(c.find("h2"))
                date = norm(c.select_one(".date")) or norm(c.select_one(".time"))
                venue = norm(c.select_one(".place")) or norm(c.select_one(".venue"))

                if link and (not title or not date or not venue):
                    try:
                        dresp = requests.get(link, headers=self.headers, timeout=self.timeout)
                        if dresp.status_code == 200:
                            dsoup = BeautifulSoup(dresp.text, "lxml")
                            title = title or norm(dsoup.select_one("h1, h2.page-title"))
                            date = date or norm(dsoup.select_one(".date, .event-date, time"))
                            venue = venue or norm(dsoup.select_one(".place, .venue, .location"))
                    except Exception:
                        pass

                if not any([title, date, venue, link]):
                    continue
                self.concerts.append(
                    {
                        "來源網站": self.site_name,
                        "演出藝人": title or "未知藝人",
                        "演出時間": date or "未公布",
                        "演出地點": venue or "未公布",
                        "網址": link or self.base_url,
                        "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
            except Exception as e:
                print(f"  ⚠ 解析單筆資料時發生錯誤: {e}")
                continue

        print(f"✓ {self.site_name} 爬取完成，共 {len(self.concerts)} 筆資料")
        if not self.concerts:
            return self._fallback_placeholder()
        return self.concerts

    def _fallback_placeholder(self) -> List[dict]:
        self.concerts.append(
            {
                "來源網站": self.site_name,
                "演出藝人": "（待公佈）",
                "演出時間": "未公布",
                "演出地點": "未公布",
                "網址": self.base_url + "/Concert",
                "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        return self.concerts


class IndievoxCrawler(ConcertCrawler):
    """iNDIEVOX 爬蟲 (等級1) - 使用 API 或簡化抓取"""

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.base_url = "https://www.indievox.com"
        self.site_name = "iNDIEVOX"

    def crawl(self) -> List[dict]:
        print(f"\n[等級1] 開始爬取 {self.site_name}...")
        self.concerts = []

        try:
            url = f"{self.base_url}/activity/list"
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200:
                return self._fallback_placeholder()

            # 先嘗試非 AI 解析：直接找活動列表的 anchor
            soup = BeautifulSoup(resp.text, "lxml")
            links = soup.select('a[href*="/activity/"]')
            for a in links[:12]:
                link = a.get("href") or ""
                if link and not link.startswith("http"):
                    link = self.base_url + link
                title = a.get_text(strip=True)
                date = venue = ""
                # 嘗試從附近節點取日期/地點
                parent = a.find_parent(["div", "li", "article"]) or a.parent
                if parent:
                    dt = parent.select_one('.date, .time')
                    vn = parent.select_one('.venue, .location, .place')
                    date = (dt.get_text(strip=True) if dt else "")
                    venue = (vn.get_text(strip=True) if vn else "")

                self.concerts.append({
                    "來源網站": self.site_name,
                    "演出藝人": title or "未知藝人",
                    "演出時間": date or "未公布",
                    "演出地點": venue or "未公布",
                    "網址": link or self.base_url,
                    "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

            # 若清單仍為空，最後再用 AI 嘗試補充
            if not self.concerts:
                concerts_from_ai = parse_html_with_gemini(resp.text, self.site_name)
                for concert in concerts_from_ai:
                    if concert.get('演出藝人'):
                        self.concerts.append(
                            {
                                "來源網站": self.site_name,
                                "演出藝人": concert.get('演出藝人', '未知藝人'),
                                "演出時間": concert.get('演出時間', '未公布'),
                                "演出地點": concert.get('演出地點', '未公布'),
                                "網址": concert.get('網址', self.base_url),
                                "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            }
                        )

            print(f"✓ {self.site_name} 爬取完成，共 {len(self.concerts)} 筆資料")
        except Exception as e:
            print(f"✗ {self.site_name} 爬取失敗: {e}")

        if not self.concerts:
            return self._fallback_placeholder()
        return self.concerts

    def _extract_detail(self, detail_url: str) -> dict:
        """從詳細頁面抽取完整資訊（標題、日期、場地）"""
        try:
            resp = requests.get(detail_url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                return {}
            
            soup = BeautifulSoup(resp.text, "lxml")
            info = {}
            
            # 抓取標題
            title_el = soup.select_one('h1, .page-title, h2.title')
            if title_el:
                info['title'] = title_el.get_text(strip=True)
            
            # 從表格或資訊區域抓取日期和地點
            # 找所有 tr 行
            rows = soup.find_all('tr')
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    
                    # 判斷是日期還是地點
                    if any(kw in label for kw in ['時間', 'Time', '日期', 'Date']):
                        if value and value != '未公布':
                            info['date'] = value
                    elif any(kw in label for kw in ['地點', 'Venue', '場地', 'Location']):
                        if value and value != '未公布':
                            info['venue'] = value
            
            # 如果沒找到，用其他方法
            if 'date' not in info:
                date_el = soup.select_one('.date, .event-date, time')
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    if date_text:
                        info['date'] = date_text
            
            if 'venue' not in info:
                venue_el = soup.select_one('.venue, .location, .place')
                if venue_el:
                    venue_text = venue_el.get_text(strip=True)
                    if venue_text and venue_text != '未公布':
                        info['venue'] = venue_text
            
            return info
        except Exception as e:
            return {}

    def _fallback_placeholder(self) -> List[dict]:
        self.concerts.append(
            {
                "來源網站": self.site_name,
                "演出藝人": "（待公佈）",
                "演出時間": "未公布",
                "演出地點": "未公布",
                "網址": self.base_url + "/activity/list",
                "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        return self.concerts


class AccupassCrawler(ConcertCrawler):
    """Accupass 活動通爬蟲 (等級2) - 使用 Gemini AI 解析詳細資訊"""

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.base_url = "https://www.accupass.com"
        self.site_name = "Accupass 活動通"

    def crawl(self) -> List[dict]:
        print(f"\n[等級2] 開始爬取 {self.site_name}...")
        self.concerts = []

        # 搜尋相關關鍵字的活動
        search_keywords = ["演唱會", "音樂會"]
        
        for keyword in search_keywords:
            try:
                # Accupass 搜尋 URL
                url = f"{self.base_url}/search?q={keyword}"
                resp = requests.get(url, headers=self.headers, timeout=self.timeout)
                if resp.status_code != 200:
                    continue

                # 先用非 AI 解析：抓取活動連結
                soup = BeautifulSoup(resp.text, "lxml")
                anchors = soup.select('a[href*="/event/"], a[href*="/go/"], a[href*="/activity/"]')
                for a in anchors[:10]:
                    link = a.get("href") or ""
                    if link and not link.startswith("http"):
                        link = self.base_url + link
                    title = a.get_text(strip=True)
                    date = venue = ""
                    parent = a.find_parent(["div", "li", "article"]) or a.parent
                    if parent:
                        dt = parent.select_one('.date, .time')
                        vn = parent.select_one('.venue, .location, .place')
                        date = (dt.get_text(strip=True) if dt else "")
                        venue = (vn.get_text(strip=True) if vn else "")

                    self.concerts.append({
                        "來源網站": self.site_name,
                        "演出藝人": title or "未知",
                        "演出時間": date or "未公布",
                        "演出地點": venue or "未公布",
                        "網址": link or self.base_url,
                        "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })

                # 若仍為空，才嘗試 AI 解析
                if not self.concerts:
                    concerts_from_ai = parse_html_with_gemini(resp.text, self.site_name)
                    for concert in concerts_from_ai:
                        if concert.get('演出藝人'):
                            self.concerts.append(
                                {
                                    "來源網站": self.site_name,
                                    "演出藝人": concert.get('演出藝人', '未知'),
                                    "演出時間": concert.get('演出時間', '未公布'),
                                    "演出地點": concert.get('演出地點', '未公布'),
                                    "網址": concert.get('網址', self.base_url),
                                    "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                }
                            )
                
                # 如果已取得足夠資料
                if len(self.concerts) >= 5:
                    break
                    
            except Exception as e:
                continue

        print(f"✓ {self.site_name} 爬取完成，共 {len(self.concerts)} 筆資料")
        
        if not self.concerts:
            return self._fallback_placeholder()
        return self.concerts

    def _fallback_placeholder(self) -> List[dict]:
        self.concerts.append(
            {
                "來源網站": self.site_name,
                "演出藝人": "（待公佈）",
                "演出時間": "未公布",
                "演出地點": "未公布",
                "網址": self.base_url,
                "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        return self.concerts


class BooksTicketCrawler(ConcertCrawler):
    """博客來售票爬蟲 (等級1) - 使用可抓取的頁面"""

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.base_url = "https://tickets.books.com.tw"
        self.site_name = "博客來售票"

    def crawl(self) -> List[dict]:
        print(f"\n[等級1] 開始爬取 {self.site_name}...")
        self.concerts = []

        # 博客來目前難以直接爬取，標記為待開發並返回佔位資料
        print(f"  ℹ {self.site_name} 需進一步研究反爬機制，暫時返回佔位資料")
        return self._fallback_placeholder()

    def _fallback_placeholder(self) -> List[dict]:
        self.concerts.append(
            {
                "來源網站": self.site_name,
                "演出藝人": "（待開發）",
                "演出時間": "未公布",
                "演出地點": "未公布",
                "網址": self.base_url,
                "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        return self.concerts


class ConcertCrawlerManager:
    """演唱會爬蟲管理器"""

    def __init__(self, per_site_timeout: int = 10):
        self.all_concerts: List[dict] = []
        # 等級定義：
        # 1 = 主流售票：拓元/年代/KKTIX（核心流量）
        # 2 = 次主流與獨立：Indievox、Accupass 等
        # 3 = 補充/佔位：博客來（待開發）
        self.level1_crawlers = [KKTIXCrawler(timeout=per_site_timeout), TicketCrawler(timeout=per_site_timeout)]
        self.level2_crawlers = [IndievoxCrawler(timeout=per_site_timeout), AccupassCrawler(timeout=per_site_timeout)]
        self.level3_crawlers = [BooksTicketCrawler(timeout=per_site_timeout)]

    def _run_crawlers(self, crawlers: List[ConcertCrawler], delay: int) -> None:
        for crawler in crawlers:
            concerts = crawler.crawl()
            self.all_concerts.extend(concerts)
            time.sleep(delay)

    def crawl_by_level(self, level: int | str = 1, delay: int = 1) -> List[dict]:
        level_str = str(level)
        self.all_concerts = []

        if level_str in ("1", "level1"):
            self._run_crawlers(self.level1_crawlers, delay)
        elif level_str in ("2", "level2"):
            self._run_crawlers(self.level2_crawlers, delay)
        elif level_str in ("3", "level3"):
            self._run_crawlers(self.level3_crawlers, delay)
        elif level_str in ("all", "*", "0"):
            self._run_crawlers(self.level1_crawlers + self.level2_crawlers + self.level3_crawlers, delay)
        else:
            print("未支援的等級，請使用 1 / 2 / 3 / all")
            return []

        return self.all_concerts

    def save_results(self, fmt: str = "excel") -> str:
        columns = ["來源網站", "演出藝人", "演出時間", "演出地點", "網址", "爬取時間"]
        df = pd.DataFrame(self.all_concerts, columns=columns)
        df = df.drop_duplicates(subset=["演出藝人", "演出時間", "演出地點"])

        for old in glob.glob("演唱會資訊彙整_*.xlsx"):
            try:
                os.remove(old)
            except Exception:
                pass

        filename_base = f"演唱會資訊彙整_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if fmt in ("excel", "both"):
            excel_path = f"{filename_base}.xlsx"
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="全部演唱會", index=False)
                if not df.empty:
                    for site in df["來源網站"].unique():
                        sheet_name = site[:31]
                        df[df["來源網站"] == site].to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"✓ 已儲存到 Excel: {excel_path}")

        if fmt in ("json", "both"):
            json_path = f"{filename_base}.json"
            df.to_json(json_path, orient="records", force_ascii=False, indent=2)
            print(f"✓ 已儲存到 JSON: {json_path}")

        return filename_base


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="台灣演唱會爬蟲")
    parser.add_argument(
        "--mode",
        default="all",
        help="等級：1=主流(拓元/年代/KKTIX)、2=次主流(Indievox/Accupass)、3=補充、all=全部"
    )
    parser.add_argument("--format", default="excel", choices=["excel", "json", "both"], help="輸出格式")
    parser.add_argument("--delay", default=1, type=int, help="爬蟲間延遲秒數")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manager = ConcertCrawlerManager()

    manager.crawl_by_level(args.mode, delay=args.delay)
    manager.save_results(fmt=args.format)


if __name__ == "__main__":
    # 防止 Windows 預設編碼問題
    if hasattr(sys, "setdefaultencoding"):
        try:
            sys.setdefaultencoding("utf-8")
        except Exception:
            pass
    main()