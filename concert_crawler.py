"""
台灣演唱會資訊爬蟲
專注 KKTIX 與 年代售票 (ticket.com.tw)
"""
import argparse
import glob
import os
import sys
import time
from datetime import datetime
from typing import List

import pandas as pd
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


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


class ConcertCrawler:
    """基底爬蟲類別"""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        self.concerts: List[dict] = []
        self.base_url = ""
        self.site_name = ""

    def crawl(self) -> List[dict]:
        raise NotImplementedError


class KKTIXCrawler(ConcertCrawler):
    """KKTIX 爬蟲 (等級1)"""

    def __init__(self):
        super().__init__()
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
                r = requests.get(ju, headers=self.headers, timeout=10)
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
                    rr = requests.get(lu, headers=self.headers, timeout=10)
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
                            page.goto(pub_url, timeout=60000, wait_until="domcontentloaded")
                            try:
                                page.wait_for_load_state("networkidle", timeout=10000)
                            except Exception:
                                page.wait_for_timeout(5000)  # 給更多時間載入
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
                                pg.goto(url, timeout=60000, wait_until="domcontentloaded")
                                try:
                                    pg.wait_for_load_state("networkidle", timeout=10000)
                                except Exception:
                                    pg.wait_for_timeout(3000)
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

    def __init__(self):
        super().__init__()
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
                resp = requests.get(lu, headers=self.headers, timeout=10)
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
                    page.goto(f"{self.base_url}/Concert", timeout=60000, wait_until="domcontentloaded")
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        page.wait_for_timeout(5000)
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
                        dresp = requests.get(link, headers=self.headers, timeout=10)
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
    """iNDIEVOX 爬蟲 (等級1)"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.indievox.com"
        self.site_name = "iNDIEVOX"

    def crawl(self) -> List[dict]:
        print(f"\n[等級1] 開始爬取 {self.site_name}...")
        self.concerts = []

        try:
            url = f"{self.base_url}/activity/list"
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                return self._fallback_placeholder()

            soup = BeautifulSoup(resp.text, "lxml")
            # 直接抓活動詳情連結
            links = soup.select("a[href*='/activity/detail/']")

            for a in links[:20]:  # 限制20筆
                try:
                    link = a.get("href") if a else ""
                    if link and not link.startswith("http"):
                        link = self.base_url + link

                    # 從連結的文字取得基本資訊
                    text = a.get_text(strip=True)
                    # 格式通常是：日期 標題
                    parts = text.split(maxsplit=2)
                    date = parts[0] if parts else ""
                    title = parts[2] if len(parts) > 2 else text

                    if link:
                        self.concerts.append(
                            {
                                "來源網站": self.site_name,
                                "演出藝人": title or "未知藝人",
                                "演出時間": date or "未公布",
                                "演出地點": "未公布",
                                "網址": link,
                                "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            }
                        )
                except Exception:
                    continue

            print(f"✓ {self.site_name} 爬取完成，共 {len(self.concerts)} 筆資料")
        except Exception as e:
            print(f"✗ {self.site_name} 爬取失敗: {e}")

        if not self.concerts:
            return self._fallback_placeholder()
        return self.concerts

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
                "網址": self.base_url + "/activity/list",
                "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        return self.concerts


class BooksTicketCrawler(ConcertCrawler):
    """博客來售票爬蟲 (等級1) - 使用可抓取的頁面"""

    def __init__(self):
        super().__init__()
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

    def __init__(self):
        self.all_concerts: List[dict] = []
        self.level1_crawlers = [
            IndievoxCrawler(),
            BooksTicketCrawler(),
            # KKTIXCrawler(),  # 需登入，暫時停用
            # TicketCrawler(),  # Cloudflare封鎖，暫時停用
        ]

    def crawl_by_level(self, level: int = 1, delay: int = 1) -> List[dict]:
        if level != 1:
            print("只支援等級1 (KKTIX + 年代) 爬取")
            return []
        for crawler in self.level1_crawlers:
            concerts = crawler.crawl()
            self.all_concerts.extend(concerts)
            time.sleep(delay)
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
    parser.add_argument("--mode", default="level1", help="目前僅支援 level1 (KKTIX + 年代)")
    parser.add_argument("--format", default="excel", choices=["excel", "json", "both"], help="輸出格式")
    parser.add_argument("--delay", default=1, type=int, help="爬蟲間延遲秒數")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manager = ConcertCrawlerManager()

    if args.mode not in ("level1", "1"):
        print("目前只執行等級1：KKTIX + 年代售票")

    manager.crawl_by_level(1, delay=args.delay)
    manager.save_results(fmt=args.format)


if __name__ == "__main__":
    # 防止 Windows 預設編碼問題
    if hasattr(sys, "setdefaultencoding"):
        try:
            sys.setdefaultencoding("utf-8")
        except Exception:
            pass
    main()
