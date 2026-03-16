"""
台灣演唱會資訊爬蟲
專注 KKTIX 與 年代售票 (ticket.com.tw)
整合 Google Gemini AI 解析 HTML
"""
import argparse
import glob
import os
import re
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


def clean_field(value: str, default: str = "未公布") -> str:
    text = str(value or "").strip()
    return text if text else default


def extract_labeled_value(text: str, labels: List[str], max_len: int = 160) -> str:
    if not text:
        return ""
    for label in labels:
        pattern = rf"(?:{label})\s*[:：｜|]\s*([^\n\r]{{1,{max_len}}})"
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip()
    return ""


def extract_labeled_block(text: str, labels: List[str], stop_labels: List[str], max_lines: int = 4) -> str:
    lines = [line.strip() for line in str(text or "").splitlines()]
    for i, line in enumerate(lines):
        for label in labels:
            if re.match(rf"^{re.escape(label)}\s*(?:[:：｜|])?\s*$", line) or re.match(rf"^{re.escape(label)}\s*[:：｜|]\s*.+$", line):
                value = re.sub(rf"^{re.escape(label)}\s*[:：｜|]?\s*", "", line).strip()
                collected = [value] if value else []
                for next_line in lines[i + 1:i + 1 + max_lines]:
                    if any(re.match(rf"^{re.escape(sl)}\s*[:：｜|]?", next_line) for sl in stop_labels):
                        break
                    if next_line:
                        collected.append(next_line)
                return " ".join(x for x in collected if x).strip()
    return ""


def clean_artist_text(text: str) -> str:
    value = clean_field(text, "未知藝人")
    value = re.sub(r"[、,/\s]+$", "", value).strip()
    return value or "未知藝人"


def extract_sale_time(text: str) -> str:
    labeled = extract_labeled_value(text, ["啟售時間", "售票時間", "開賣時間", "啟售", "開賣", "售票"], 80)
    if labeled:
        return labeled
    match = re.search(r"(?:啟售|開賣|售票(?:時間)?)\s*[:：]?\s*(20\d{2}[\./年-]\d{1,2}[\./月-]\d{1,2}(?:日)?(?:\s*\d{1,2}:\d{2})?)", text, re.I)
    if not match:
        match = re.search(r"((?:\d{1,2}[\./]\d{1,2})(?:\s*[（\(][^）\)]*[）\)])?(?:\s*(?:上午|下午|中午|晚上))?\s*\d{1,2}:\d{2}[^\n\r]{0,20}(?:開賣|啟售|售票))", text, re.I)
    return match.group(1).strip() if match else "未公布"


def extract_price_text(text: str) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    candidates = []

    labeled = extract_labeled_value(text, ["票價", "Price", "PRICE"], 200)
    if labeled:
        candidates.append(labeled)

    line_keywords = ["票價", "NT$", "免費", "預售", "現場票", "早鳥票", "學生票", "VIP", "VVIP", "元"]
    for line in lines:
        if any(keyword.lower() in line.lower() for keyword in line_keywords):
            if re.fullmatch(r"[\d\s:./-]+", line):
                continue
            cleaned = re.sub(r"^(票價|Price|PRICE)\s*[:：]\s*", "", line, flags=re.I).strip()
            if cleaned and cleaned not in candidates:
                candidates.append(cleaned)

    if candidates:
        return "、".join(candidates[:3])[:200]

    matches = re.findall(r"(?:NT\$\s*\d{2,5}(?:\s*[-~～]\s*NT\$?\s*\d{2,5})?(?:元)?)|免費", text, re.I)
    cleaned = []
    for m in matches:
        value = m.strip()
        if value not in cleaned:
            cleaned.append(value)
    return "、".join(cleaned[:5]) if cleaned else "未公布"


def extract_ticket_types(text: str) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    labeled = extract_labeled_value(text, ["票種", "Ticket Type", "票券種類"], 200)
    found = []
    if labeled:
        found.append(labeled)

    keywords = [
        "VIP", "VVIP", "GA", "早鳥票", "早鳥", "預售票", "預售", "全票", "一般票", "現場票", "現場",
        "學生票", "雙人票", "身障票", "搖滾區", "站票", "座票", "自由入座", "對號座", "單人票",
        "套票", "優惠套票", "預購票", "Door Ticket", "Pre-sale", "Accessibility Ticket",
        "A區", "B區", "C區", "D區", "E區", "F區", "G區"
    ]
    for line in lines:
        for keyword in keywords:
            if keyword.lower() in line.lower() and keyword not in found:
                found.append(keyword)

    return "、".join(found[:10]) if found else "未公布"


def extract_ticket_types_from_price(price_text: str) -> str:
    if not price_text or price_text == "未公布":
        return "未公布"
    found = []
    keywords = [
        "VIP", "VVIP", "早鳥票", "早鳥", "預售單人票", "預售雙人套票", "預售票", "預售", "預購票",
        "現場票", "現場", "學生票", "身障票", "單人票", "雙人票", "套票", "優惠套票", "全票", "一般票",
        "Door Ticket", "Pre-sale", "Accessibility Ticket", "A區", "B區", "C區", "D區", "E區", "F區", "G區"
    ]
    for keyword in keywords:
        if keyword.lower() in price_text.lower() and keyword not in found:
            found.append(keyword)
    if not found:
        numbered_tiers = re.findall(r"\b\d{3,5}\b", price_text)
        if len(set(numbered_tiers)) >= 2:
            found.append("全票")
    return "、".join(found[:10]) if found else "未公布"


def extract_address_from_text(text: str) -> str:
    raw = str(text or "")
    labeled = extract_labeled_value(raw, ["地址", "Address"], 160)
    if labeled and not _is_fake_address(labeled):
        return labeled
    m = re.search(r"[（\(]([^（）\(\)]{4,120}(?:市|縣)[^（）\(\)]{0,80})[）\)]", raw)
    if m:
        candidate = m.group(1).strip()
        if not _is_fake_address(candidate):
            return candidate
    m = re.search(r"((?:台|臺)[^\s，。]{0,20}(?:市|縣)[^\s，。]{0,40}(?:路|街|大道|段|巷|弄)[^\s，。]{0,20}號?)", raw)
    if m:
        candidate = m.group(1).strip()
        if not _is_fake_address(candidate):
            return candidate
    return ""


def split_venue_and_address(venue_text: str, extra_text: str = "") -> tuple[str, str]:
    venue_raw = clean_field(venue_text, "未公布")
    if venue_raw == "未公布":
        addr = extract_address_from_text(extra_text)
        return venue_raw, (addr if addr and not _is_fake_address(addr) else "未公布")

    m = re.match(r"^(.*?)\s*[（\(]\s*([^）\)]{4,160})\s*[）\)]\s*$", venue_raw)
    if m:
        venue = clean_field(m.group(1), "未公布")
        addr_candidate = clean_field(m.group(2), "未公布")
        addr = addr_candidate if not _is_fake_address(addr_candidate) else "未公布"
        return venue, addr

    addr = extract_address_from_text(extra_text)
    return venue_raw, (clean_field(addr) if addr and not _is_fake_address(addr) else "未公布")


def build_event_record(source: str, artist: str, sale_time: str = "未公布", event_time: str = "未公布",
                       venue: str = "未公布", price: str = "未公布", ticket_types: str = "未公布",
                       url: str = "", crawl_time: str | None = None,
                       event_name: str | None = None, address: str = "未公布") -> Dict:
    crawl_time = crawl_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    artist = clean_field(artist, "未知藝人")
    event_name = clean_field(event_name or artist)
    sale_time = clean_field(sale_time)
    event_time = clean_field(event_time)
    venue = clean_field(venue)
    address = clean_field(address)
    price = clean_field(price)
    ticket_types = clean_field(ticket_types)
    url = clean_field(url, "")

    return {
        "來源網站": source,
        "活動名稱": event_name,
        "藝人": artist,
        "搶票時間": sale_time,
        "活動時間": event_time,
        "活動地點": venue,
        "活動地址": address,
        "票價": price,
        "票種": ticket_types,
        "網址": url,
        "爬取時間": crawl_time,
        # 相容舊欄位
        "演出藝人": artist,
        "演出時間": event_time,
        "演出地點": venue,
    }


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\u3000", " ")).strip()


def _trim_by_markers(text: str, markers: List[str]) -> str:
    value = str(text or "")
    for marker in markers:
        if marker in value:
            value = value.split(marker)[0].strip()
    return value


def normalize_sale_time(value: str) -> str:
    text = _normalize_spaces(value)
    if not text or text == "未公布":
        return "未公布"
    text = _trim_by_markers(text, ["主辦", "備註", "注意事項", "※", "⦿", "| iNDIEVOX"])
    pattern = r"(20\d{2}[/\.-]\d{1,2}[/\.-]\d{1,2}(?:（[^）]*）|\([^\)]*\))?\s*\d{1,2}:\d{2}(?:\s*(?:開始販售|開賣|啟售))?)"
    m = re.search(pattern, text)
    if m:
        return _normalize_spaces(m.group(1))
    m = re.search(r"(20\d{2}[/\.-]\d{1,2}[/\.-]\d{1,2}(?:（[^）]*）|\([^\)]*\))?)", text)
    if m:
        return _normalize_spaces(m.group(1))
    return text[:80]


def normalize_event_time(value: str) -> str:
    text = _normalize_spaces(value)
    if not text or text == "未公布":
        return "未公布"
    text = _trim_by_markers(text, ["主辦", "備註", "注意事項", "※", "⦿", "| iNDIEVOX"])
    m = re.search(r"(20\d{2}[/\.-]\d{1,2}[/\.-]\d{1,2}(?:~\d{1,2})?(?:\s*\([^\)]*\)|\s*（[^）]*）)?(?:\s*\d{1,2}:\d{2}(?:\s*[ap]m)?(?:~\d{1,2}:\d{2}(?:\s*[ap]m)?)?)?)", text, re.I)
    if m:
        return _normalize_spaces(m.group(1))
    return text[:100]


def normalize_venue(value: str) -> str:
    text = _normalize_spaces(value)
    if not text or text == "未公布":
        return "未公布"
    text = _trim_by_markers(text, ["演出者", "票價", "主辦", "備註", "注意事項", "※", "⦿", "| iNDIEVOX"])
    return text[:120] if text else "未公布"


def _is_fake_address(addr: str) -> bool:
    """判斷是否為已知的頁尾/公司固定地址，不代表實際活動場地。"""
    if not addr:
        return True
    for fake in _KNOWN_FAKE_ADDRESSES:
        if fake in addr:
            return True
    return False


def normalize_address(value: str) -> str:
    text = _normalize_spaces(value)
    if not text or text == "未公布":
        return "未公布"
    if _is_fake_address(text):
        return "未提供"
    text = _trim_by_markers(text, ["演出者", "票價", "主辦", "備註", "注意事項", "※", "⦿", "| iNDIEVOX"])
    return text[:160] if text else "未公布"


def normalize_price(value: str) -> str:
    text = _normalize_spaces(value)
    if not text or text == "未公布":
        return "未公布"
    text = _trim_by_markers(text, ["主辦", "備註", "注意事項", "※", "⦿", "| iNDIEVOX"])
    text = re.sub(r"^票價\s*[:：]?\s*", "", text, flags=re.I)
    if "免費" in text:
        return "免費"

    chunks = re.split(r"[\/|｜]|、", text)
    useful = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if any(k in chunk for k in ["預售", "現場", "早鳥", "VIP", "VVIP", "學生", "身障", "套票", "單人", "雙人", "A區", "B區", "C區", "D區"]):
            useful.append(chunk)
            continue
        if re.search(r"\d{2,5}", chunk):
            useful.append(chunk)

    if useful:
        cleaned = " / ".join(dict.fromkeys(useful))
        return cleaned[:200]

    nums = re.findall(r"\d{2,5}", text)
    if nums:
        uniq = []
        for num in nums:
            if num not in uniq:
                uniq.append(num)
        return "、".join(uniq[:12])
    return "未公布"


def normalize_ticket_types(value: str, price: str) -> str:
    text = _normalize_spaces(value)
    if not text or text == "未公布":
        text = extract_ticket_types_from_price(price)
    if not text or text == "未公布":
        return "未公布"
    tokens = re.split(r"[、,/|｜\s]+", text)
    keep_keywords = ["VIP", "VVIP", "早鳥", "預售", "現場票", "現場", "學生票", "身障票", "單人票", "雙人票", "套票", "優惠套票", "全票", "一般票", "Pre-sale", "Door Ticket", "Accessibility Ticket", "A區", "B區", "C區", "D區", "E區", "F區", "G區"]
    kept = []
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        matched = next((kw for kw in keep_keywords if kw.lower() in token.lower()), None)
        if matched and matched not in kept:
            kept.append(matched)
    return "、".join(kept) if kept else "未公布"


def normalize_record(record: Dict) -> Dict:
    source = clean_field(record.get("來源網站"), "未知")
    event_name = clean_field(record.get("活動名稱") or record.get("藝人") or record.get("演出藝人"), "未公布")
    artist = clean_artist_text(record.get("藝人") or record.get("演出藝人") or "未知藝人")
    sale_time = normalize_sale_time(record.get("搶票時間", "未公布"))
    event_time = normalize_event_time(record.get("活動時間") or record.get("演出時間") or "未公布")
    venue_raw = record.get("活動地點") or record.get("演出地點") or "未公布"
    venue = normalize_venue(venue_raw)
    address = normalize_address(record.get("活動地址") or extract_address_from_text(venue_raw) or "未公布")
    price = normalize_price(record.get("票價", "未公布"))
    ticket_types = normalize_ticket_types(record.get("票種", "未公布"), price)
    url = clean_field(record.get("網址"), "")
    crawl_time = clean_field(record.get("爬取時間"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return build_event_record(
        source=source,
        artist=artist,
        event_name=event_name,
        sale_time=sale_time,
        event_time=event_time,
        venue=venue,
        address=address,
        price=price,
        ticket_types=ticket_types,
        url=url,
        crawl_time=crawl_time,
    )


def is_valid_concert_record(record: Dict) -> bool:
    artist = str(record.get("藝人") or record.get("演出藝人") or "").lower()
    venue = str(record.get("活動地點") or record.get("演出地點") or "").lower()
    source = str(record.get("來源網站") or "")

    if not artist:
        return False

    blocked_keywords = [
        "postcard kit", "商品", "旅遊", "出海一日遊", "自由行", "機加酒", "四日", "五日"
    ]
    if any(keyword in artist for keyword in blocked_keywords):
        return False
    if venue in ["商品", "周邊", "未分類"]:
        return False

    if source == "年代售票":
        if any(keyword in artist for keyword in ["周邊", "商品", "套裝"]):
            return False

    return True


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

    def _extract_links_from_html(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "lxml")
        urls = set()
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            if href.startswith("javascript:") or href.startswith("mailto:"):
                continue
            if href.startswith("/"):
                full_url = self.base_url + href
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = self.base_url + "/" + href.lstrip("./")

            u = full_url.lower()
            if "ticket.com.tw" not in u:
                continue
            if any(x in u for x in ["login", "member", "register", "search", "sitemap", "faq", "news"]):
                continue
            if "utk0108" in u or "type=4" in u:
                continue
            if "/utk01/" in u or "/utk13/" in u:
                continue
            if any(x in u for x in ["/utk02/", "/utk03/", "/dm/", "/show/", "/activity/"]):
                urls.add(full_url)
        return list(urls)

    def _is_invalid_title(self, title: str) -> bool:
        if not title:
            return True
        normalized = re.sub(r"\s+", "", title).lower()
        bad_tokens = ["檢核錯誤清單", "檢核錯誤", "錯誤", "error", "notfound", "系統訊息"]
        return any(token in normalized for token in bad_tokens)

    def _extract_list_events(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "lxml")
        events = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            if href.startswith("/"):
                link = self.base_url + href
            elif href.startswith("http"):
                link = href
            else:
                link = self.base_url + "/" + href.lstrip("./")

            low = link.lower()
            if "ticket.com.tw" not in low:
                continue
            if "utk0108" in low or "type=4" in low:
                continue
            if "/utk01/" in low or "/utk13/" in low:
                continue
            if not any(x in low for x in ["/utk02/", "/utk03/", "/dm/", "/show/"]):
                continue

            title = a.get_text(" ", strip=True)
            if not title or len(title) < 4:
                continue
            if any(bad in title.lower() for bad in ["首頁", "會員", "登入", "註冊", "客服"]) or self._is_invalid_title(title):
                continue

            parent = a.find_parent(["li", "div", "article", "tr", "section"]) or a
            context_text = parent.get_text(" ", strip=True)
            date = self._extract_date(context_text)

            venue = "未公布"
            venue_match = re.search(r"(?:地點|場地|Venue|Location)\s*[:：]\s*([^\n\r]{2,60})", context_text, re.I)
            if venue_match:
                venue = venue_match.group(1).strip()

            key = (title.strip(), date.strip(), link.strip())
            if key in seen:
                continue
            seen.add(key)
            events.append(
                build_event_record(
                    source=self.site_name,
                    artist=title,
                    event_time=date or "未公布",
                    venue=venue,
                    url=link,
                )
            )

        return events

    def _extract_date(self, text: str) -> str:
        if not text:
            return "未公布"
        patterns = [
            r"(20\d{2}[\./-]\d{1,2}[\./-]\d{1,2}(?:\s*\d{1,2}:\d{2})?)",
            r"(20\d{2}年\d{1,2}月\d{1,2}日(?:\s*\d{1,2}:\d{2})?)",
            r"(\d{1,2}/\d{1,2}(?:\s*\d{1,2}:\d{2})?)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                return m.group(1).strip()
        return "未公布"

    def _extract_venue(self, soup: BeautifulSoup, full_text: str) -> str:
        venue_selectors = [
            ".venue", ".place", ".location", ".event-place", ".hall", "[class*='venue']", "[class*='place']"
        ]
        for sel in venue_selectors:
            el = soup.select_one(sel)
            if el:
                value = el.get_text(" ", strip=True)
                if value and len(value) >= 2:
                    return value[:80]

        match = re.search(r"(?:地點|場地|演出地點|Venue|Location)\s*[:：]\s*([^\n\r]{2,60})", full_text, re.I)
        if match:
            return match.group(1).strip()
        return "未公布"

    def _fetch_event_detail(self, url: str) -> Dict:
        try:
            detail_headers = {
                **self.headers,
                "Referer": f"{self.base_url}/Concert",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
            resp = requests.get(url, headers=detail_headers, timeout=self.timeout)
            if resp.status_code != 200:
                return {}
            resp.encoding = resp.apparent_encoding or resp.encoding

            if "403" in resp.text[:1200] and "錯誤" in resp.text[:1200]:
                return {}

            soup = BeautifulSoup(resp.text, "lxml")
            full_text = soup.get_text("\n", strip=True)

            title_el = soup.select_one("h1, h2, .title, .event-title, [class*='title']")
            title = title_el.get_text(" ", strip=True) if title_el else ""
            if not title and soup.title:
                title = re.split(r"[-｜|]", soup.title.get_text(strip=True))[0].strip()

            if self._is_invalid_title(title):
                return {}

            date = self._extract_date(full_text)
            venue = self._extract_venue(soup, full_text)
            venue, address = split_venue_and_address(venue, full_text)
            artist = extract_labeled_value(full_text, ["演出者", "演出藝人", "Artist"], 100) or title
            sale_time = extract_sale_time(full_text)
            price = "未公布"
            ticket_types = extract_ticket_types(full_text)

            table_rows = soup.select("table tr")
            for tr in table_rows:
                cells = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
                if len(cells) >= 3 and any("Date and Time" in c or "活動日期" in c for c in cells):
                    continue
                if len(cells) >= 3:
                    row_date, row_venue, row_price = cells[0].strip(), cells[1].strip(), cells[2].strip()
                    if row_date and row_date != "未公布":
                        date = row_date
                    if row_venue and row_venue != "未公布":
                        venue, address = split_venue_and_address(row_venue, full_text)
                    if row_price and row_price != "未公布":
                        price = row_price.replace(" 、 ", "、").replace(" , ", "、")
                        ticket_types = extract_ticket_types_from_price(price)
                        break
                elif len(cells) == 2:
                    label = cells[0].strip()
                    value = cells[1].strip()
                    if any(x in label for x in ["售票", "開賣", "啟售"]):
                        sale_time = value or sale_time
                    elif any(x in label for x in ["票種", "座位", "席次", "票券種類"]):
                        if value and value != "未公布":
                            ticket_types = value
                    elif any(x in label for x in ["地址", "Address"]):
                        if value and value != "未公布":
                            address = value
                    elif any(x in label for x in ["票價", "Price"]):
                        if value and value != "未公布":
                            price = value
                            if ticket_types == "未公布":
                                ticket_types = extract_ticket_types_from_price(price)

            if price == "未公布":
                price = extract_price_text(full_text)
            if ticket_types == "未公布":
                ticket_types = extract_ticket_types_from_price(price)
            if ticket_types == "未公布":
                ticket_types = extract_ticket_types(full_text)
            if ticket_types == "未公布" and price != "未公布" and re.search(r"\b\d{3,5}\b", price):
                ticket_types = "全票"

            if not any([title, date != "未公布", venue != "未公布"]):
                return {}
            return build_event_record(
                source=self.site_name,
                event_name=title or "未公布",
                artist=artist or title or "未知藝人",
                sale_time=sale_time,
                event_time=date,
                venue=venue,
                address=address,
                price=price,
                ticket_types=ticket_types,
                url=url,
            )
        except Exception:
            return {}

    def _fetch_event_detail_playwright(self, url: str, state_file: str = "ticket_state.json", force_headful: bool = False) -> Dict:
        try:
            with sync_playwright() as p:
                browser = launch_browser_with_fallback(p, force_headful=force_headful)
                context = browser.new_context(storage_state=load_state_if_exists(state_file))
                page = context.new_page()
                page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle", timeout=self.timeout * 1000)
                except Exception:
                    page.wait_for_timeout(min(3000, self.timeout * 1000))
                html = page.content()
                context.storage_state(path=state_file)
                browser.close()

            soup = BeautifulSoup(html, "lxml")
            full_text = soup.get_text("\n", strip=True)

            title_el = soup.select_one("h1, h2, .title, .event-title, [class*='title']")
            title = title_el.get_text(" ", strip=True) if title_el else ""
            if not title and soup.title:
                title = re.split(r"[-｜|]", soup.title.get_text(strip=True))[0].strip()
            if self._is_invalid_title(title):
                return {}

            date = self._extract_date(full_text)
            venue = self._extract_venue(soup, full_text)
            venue, address = split_venue_and_address(venue, full_text)
            artist = extract_labeled_value(full_text, ["演出者", "演出藝人", "Artist"], 100) or title
            sale_time = extract_sale_time(full_text)
            price = extract_price_text(full_text)
            ticket_types = extract_ticket_types(full_text)
            if ticket_types == "未公布":
                ticket_types = extract_ticket_types_from_price(price)

            if not any([title, date != "未公布", venue != "未公布"]):
                return {}
            return build_event_record(
                source=self.site_name,
                event_name=title or "未公布",
                artist=artist or title or "未知藝人",
                sale_time=sale_time,
                event_time=date,
                venue=venue,
                address=address,
                price=price,
                ticket_types=ticket_types,
                url=url,
            )
        except Exception:
            return {}

    def _fallback_from_tier1_crawler(self) -> List[dict]:
        try:
            from crawlers.tier1_crawlers import TicketComCrawler

            print("  ℹ 啟用進階 TicketComCrawler 補抓...")
            crawler = TicketComCrawler()
            events = crawler.run() or []

            normalized = []
            for event in events:
                title = (event.get("title") or event.get("artist") or "").strip()
                date = (event.get("date") or "未公布").strip()
                venue = (event.get("location") or "未公布").strip()
                url = (event.get("url") or self.base_url).strip()

                if not title or self._is_invalid_title(title):
                    continue
                if any(x in title for x in ["搜尋", "search", "檢核", "錯誤"]):
                    continue
                if "UTK0101_06" in url:
                    continue
                detail = self._fetch_event_detail(url)
                if detail:
                    normalized.append(detail)
                    continue
                if venue in ["講座", "座", "活動", "未取得", "未公布"]:
                    venue = "未公布"
                normalized.append(
                    build_event_record(
                        source=self.site_name,
                        event_name=title,
                        artist=title,
                        event_time=date or "未公布",
                        venue=venue or "未公布",
                        price="未公布",
                        ticket_types="未公布",
                        url=url,
                    )
                )

            return normalized
        except Exception as e:
            print(f"  ⚠ 進階補抓失敗: {e}")
            return []

    def crawl(self) -> List[dict]:
        print(f"\n[等級1] 開始爬取 {self.site_name}...")
        self.concerts = []
        state_file = "ticket_state.json"
        headless_env = os.getenv("PLAYWRIGHT_HEADLESS", "1")
        force_headful = headless_env.strip() == "0"

        list_urls = [
            f"{self.base_url}",
            f"{self.base_url}/Concert",
            f"{self.base_url}/category/Concert",
            f"{self.base_url}/search?type=concert",
            f"{self.base_url}/dm.html",
        ]
        html_pages = []
        for lu in list_urls:
            try:
                resp = requests.get(lu, headers=self.headers, timeout=self.timeout)
                if resp.status_code == 200 and "html" in resp.headers.get("Content-Type", "").lower():
                    html_pages.append(resp.text)
            except Exception:
                continue

        if not html_pages:
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
                    html_pages.append(page.content())
                    context.storage_state(path=state_file)
                    browser.close()
            except Exception as e:
                print(f"✗ 無法取得年代售票列表頁: {e}")
                return self._fallback_placeholder()

        event_urls = set()
        list_events = []
        for html in html_pages:
            event_urls.update(self._extract_links_from_html(html))
            list_events.extend(self._extract_list_events(html))

        url_to_item = {}
        for item in list_events:
            link = item.get("網址", "").strip()
            if not link:
                continue
            url_to_item[link] = item

        if not event_urls:
            if list_events:
                self.concerts = list_events[:80]
                print(f"✓ {self.site_name} 爬取完成，共 {len(self.concerts)} 筆資料")
                return self.concerts
            print("  ⚠ 年代售票列表沒有解析到有效活動連結")
            advanced_events = self._fallback_from_tier1_crawler()
            if advanced_events:
                self.concerts = advanced_events
                print(f"✓ {self.site_name} 爬取完成，共 {len(self.concerts)} 筆資料")
                return self.concerts
            return self._fallback_placeholder()

        seen_keys = set()
        for link in list(event_urls)[:80]:
            item = self._fetch_event_detail(link)
            if (not item) or str(item.get("票種", "未公布")).strip() in ["", "未公布"]:
                item_pw = self._fetch_event_detail_playwright(link, state_file=state_file, force_headful=force_headful)
                if item_pw:
                    item = item_pw
            if not item and link in url_to_item:
                item = url_to_item[link]
            if not item:
                continue
            key = (
                item.get("演出藝人", "").strip(),
                item.get("演出時間", "").strip(),
                item.get("演出地點", "").strip(),
                item.get("網址", "").strip(),
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            self.concerts.append(item)

        if not self.concerts and list_events:
            self.concerts = list_events[:80]

        if not self.concerts:
            advanced_events = self._fallback_from_tier1_crawler()
            if advanced_events:
                self.concerts = advanced_events

        print(f"✓ {self.site_name} 爬取完成，共 {len(self.concerts)} 筆資料")
        if not self.concerts:
            return self._fallback_placeholder()
        return self.concerts

    def _fallback_placeholder(self) -> List[dict]:
        self.concerts.append(
            build_event_record(
                source=self.site_name,
                artist="（待公佈）",
                url=self.base_url + "/Concert",
            )
        )
        return self.concerts


class IndievoxCrawler(ConcertCrawler):
    """iNDIEVOX 爬蟲 (等級1) - 使用 API 或簡化抓取"""

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.base_url = "https://www.indievox.com"
        self.site_name = "iNDIEVOX"

    def _get_list_html(self) -> str:
        list_urls = [
            f"{self.base_url}/activity/list",
            f"{self.base_url}/activity/list?type=card&startDate=2025/01/01&endDate=2026/12/31",
            f"{self.base_url}/activity/list?type=table&startDate=2025/01/01&endDate=2026/12/31",
        ]

        html_parts = []
        for list_url in list_urls:
            try:
                resp = requests.get(list_url, headers=self.headers, timeout=self.timeout)
                if resp.status_code == 200:
                    resp.encoding = resp.apparent_encoding or resp.encoding
                    html_parts.append(resp.text)
            except Exception:
                continue

        if html_parts:
            return "\n".join(html_parts)

        try:
            with sync_playwright() as p:
                browser = launch_browser_with_fallback(p)
                page = browser.new_page()
                page.goto(f"{self.base_url}/activity/list?type=table&startDate=2025/01/01&endDate=2026/12/31", timeout=self.timeout * 1000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                for _ in range(8):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1200)
                html = page.content()
                browser.close()
                return html
        except Exception:
            return ""

    def _extract_date_from_text(self, text: str) -> str:
        if not text:
            return "未公布"
        patterns = [
            r"(20\d{2}[\./-]\d{1,2}[\./-]\d{1,2}(?:\s*\d{1,2}:\d{2})?)",
            r"(20\d{2}年\d{1,2}月\d{1,2}日(?:\s*\d{1,2}:\d{2})?)",
            r"(\d{1,2}/\d{1,2}(?:\s*\d{1,2}:\d{2})?)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                return m.group(1).strip()
        return "未公布"

    def _infer_venue(self, text: str) -> str:
        if not text:
            return "未公布"

        def _clean(raw: str) -> str:
            value = (raw or "").strip()
            for sep in ["演出者", "票價", "※", "注意事項", "\n"]:
                if sep in value:
                    value = value.split(sep)[0].strip()
            return value[:90] if value else "未公布"

        label_match = re.search(r"(?:地點|場地|演出地點|Venue|Location)\s*[:：]\s*([^\n\r]{2,80})", text, re.I)
        if label_match:
            return _clean(label_match.group(1))

        venue_keywords = [
            "Legacy Taipei", "Legacy Taichung", "Legacy", "THE WALL", "Zepp", "SUB", "河岸留言",
            "小地方展演空間", "小巨蛋", "流行音樂中心", "女巫店", "Revolver", "PIPE"
        ]
        lowered = text.lower()
        for v in venue_keywords:
            if v.lower() in lowered:
                return _clean(v)
        return "未公布"

    def crawl(self) -> List[dict]:
        print(f"\n[等級1] 開始爬取 {self.site_name}...")
        self.concerts = []

        try:
            html = self._get_list_html()
            if not html:
                return self._fallback_placeholder()

            soup = BeautifulSoup(html, "lxml")
            links = soup.select('a[href*="/activity/detail/"]')
            if not links:
                links = soup.select('a[href*="/activity/"]')

            regex_links = sorted(set(re.findall(r'/activity/detail/[A-Za-z0-9_]+', html)))
            for href in regex_links:
                class _LinkObj:
                    def __init__(self, h):
                        self._h = h
                    def get(self, key):
                        return self._h if key == "href" else ""
                    def get_text(self, *args, **kwargs):
                        return ""
                    @property
                    def parent(self):
                        return None
                    def find_parent(self, *args, **kwargs):
                        return None
                links.append(_LinkObj(href))

            seen_urls = set()
            seen_keys = set()

            for a in links:
                link = a.get("href") or ""
                if link and not link.startswith("http"):
                    link = self.base_url + link
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)

                title = a.get_text(" ", strip=True)
                date = ""
                venue = ""

                # 嘗試從附近節點取日期/地點
                parent = a.find_parent(["div", "li", "article"]) or a.parent
                if parent:
                    dt = parent.select_one('.date, .time, [class*="date"], [class*="time"]')
                    vn = parent.select_one('.venue, .location, .place, [class*="venue"], [class*="place"]')
                    date = dt.get_text(" ", strip=True) if dt else ""
                    venue = vn.get_text(" ", strip=True) if vn else ""

                detail = self._extract_detail(link)
                merged_title = detail.get('title') or title or "未知藝人"
                merged_artist = clean_artist_text(detail.get('artist') or merged_title)
                merged_date = detail.get('date') or date
                merged_venue = detail.get('venue') or venue
                merged_venue, merged_address = split_venue_and_address(merged_venue, detail.get("raw_text") or "")
                merged_sale_time = detail.get('sale_time') or "未公布"
                merged_price = detail.get('price') or "未公布"
                merged_ticket_types = detail.get('ticket_types') or "未公布"

                if merged_date in ["", "未公布"]:
                    merged_date = self._extract_date_from_text((detail.get("raw_text") or "") + " " + (date or ""))
                if merged_venue in ["", "未公布"]:
                    merged_venue = self._infer_venue((detail.get("raw_text") or "") + " " + (merged_title or "") + " " + (venue or ""))

                item = build_event_record(
                    source=self.site_name,
                    event_name=merged_title,
                    artist=merged_artist,
                    sale_time=merged_sale_time,
                    event_time=merged_date or "未公布",
                    venue=merged_venue or "未公布",
                    address=merged_address,
                    price=merged_price,
                    ticket_types=merged_ticket_types,
                    url=link,
                )

                key = (
                    item.get("演出藝人", "").strip(),
                    item.get("演出時間", "").strip(),
                    item.get("演出地點", "").strip(),
                    item.get("網址", "").strip(),
                )
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                self.concerts.append(item)

                if len(self.concerts) >= 120:
                    break

            # 若清單仍為空，最後再用 AI 嘗試補充
            if not self.concerts:
                concerts_from_ai = parse_html_with_gemini(html, self.site_name)
                for concert in concerts_from_ai:
                    if concert.get('演出藝人'):
                        self.concerts.append(
                            build_event_record(
                                source=self.site_name,
                                artist=concert.get('演出藝人', '未知藝人'),
                                event_time=concert.get('演出時間', '未公布'),
                                venue=concert.get('演出地點', '未公布'),
                                url=concert.get('網址', self.base_url),
                            )
                        )

            print(f"✓ {self.site_name} 爬取完成，共 {len(self.concerts)} 筆資料")
        except Exception as e:
            print(f"✗ {self.site_name} 爬取失敗: {e}")

        if not self.concerts:
            return self._fallback_placeholder()
        return self.concerts

    def _extract_detail(self, detail_url: str) -> dict:
        """從詳細頁面抽取完整資訊（標題、時間、場地、票價、票種）"""
        try:
            resp = requests.get(detail_url, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200:
                return {}
            
            soup = BeautifulSoup(resp.text, "lxml")
            info = {}
            raw_text = soup.get_text("\n", strip=True)
            stop_labels = ['演出日期及時間', '活動日期及時間', '演出時間', '活動時間', '演出地點', '活動地點', '場地', '演出者', '票價', '售票時間', '開賣時間', '啟售時間', '主辦', '備註', '注意事項']

            for script in soup.select('script[type="application/ld+json"]'):
                script_text = (script.string or script.get_text() or "").strip()
                if not script_text:
                    continue
                try:
                    payload = json.loads(script_text)
                except Exception:
                    continue

                nodes = payload if isinstance(payload, list) else [payload]
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    start_date = str(node.get('startDate') or "").strip()
                    if start_date and not info.get('date'):
                        info['date'] = start_date.replace('T', ' ')

                    location = node.get('location')
                    if isinstance(location, dict):
                        location_name = str(location.get('name') or "").strip()
                        address = location.get('address')
                        if isinstance(address, dict):
                            addr = str(address.get('streetAddress') or address.get('addressLocality') or "").strip()
                            if location_name and addr:
                                info['venue'] = f"{location_name}（{addr}）"
                            elif location_name:
                                info['venue'] = location_name
                            elif addr:
                                info['venue'] = addr
                        elif location_name:
                            info['venue'] = location_name

                    offers = node.get('offers')
                    offer_nodes = offers if isinstance(offers, list) else ([offers] if isinstance(offers, dict) else [])
                    offer_texts = []
                    for offer in offer_nodes:
                        if not isinstance(offer, dict):
                            continue
                        price_value = str(offer.get('price') or "").strip()
                        currency = str(offer.get('priceCurrency') or "").strip()
                        category = str(offer.get('category') or "").strip()
                        availability = str(offer.get('availability') or "").strip()
                        text_parts = [x for x in [category, f"{currency}{price_value}" if price_value else "", availability] if x]
                        if text_parts:
                            offer_texts.append(" ".join(text_parts))
                    if offer_texts and not info.get('price'):
                        info['price'] = " / ".join(dict.fromkeys(offer_texts))[:220]
            
            # 抓取標題
            title_el = soup.select_one('h1, .page-title, h2.title')
            if title_el:
                info['title'] = title_el.get_text(strip=True)
            info['artist'] = extract_labeled_block(raw_text, ['演出者'], stop_labels, max_lines=3) or info.get('title', '')
            info['date'] = extract_labeled_block(raw_text, ['演出日期及時間', '活動日期及時間', '演出時間', '活動時間'], stop_labels, max_lines=2) or info.get('date', '')
            info['venue'] = extract_labeled_block(raw_text, ['演出地點', '活動地點', '場地'], stop_labels, max_lines=2) or info.get('venue', '')
            info['price'] = extract_labeled_block(raw_text, ['票價'], stop_labels, max_lines=3) or info.get('price', '')
            info['sale_time'] = extract_labeled_block(raw_text, ['售票時間', '開賣時間', '啟售時間'], stop_labels, max_lines=3) or info.get('sale_time', '')

            if not info.get('sale_time'):
                info['sale_time'] = extract_labeled_value(raw_text, ['售票時間', '開賣時間', '啟售時間', '開始販售'])
            if not info.get('sale_time'):
                sale_match = re.search(r"((?:\d{1,2}[\./]\d{1,2})(?:\s*[（\(][^）\)]*[）\)])?(?:\s*(?:上午|下午|中午|晚上))?\s*\d{1,2}:\d{2}[^\n\r]{0,20}(?:開賣|啟售|售票))", raw_text, re.I)
                if sale_match:
                    info['sale_time'] = sale_match.group(1).strip()
            if not info.get('venue'):
                info['venue'] = extract_labeled_value(raw_text, ['演出地點', '活動地點', '場地', 'Venue', 'Location'])
            if not info.get('venue'):
                venue_match = re.search(r"(?:地點|場地|Venue|Location)\s*[:：｜|]\s*([^\n\r]{2,120})", raw_text, re.I)
                if venue_match:
                    info['venue'] = venue_match.group(1).strip()
            if not info.get('price'):
                info['price'] = extract_labeled_value(raw_text, ['票價', 'Price', '一般預售票', '預購票'])
            if not info.get('price'):
                price_match = re.search(r"(?:票價|Price)\s*[:：｜|]\s*([^\n\r]{2,220})", raw_text, re.I)
                if price_match:
                    info['price'] = price_match.group(1).strip()
            
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
                    elif any(kw in label for kw in ['演出者', 'Artist']):
                        if value and value != '未公布':
                            info['artist'] = value
                    elif any(kw in label for kw in ['啟售', '開賣', '售票']):
                        if value and value != '未公布':
                            info['sale_time'] = value
                    elif any(kw in label for kw in ['地點', 'Venue', '場地', 'Location']):
                        if value and value != '未公布':
                            info['venue'] = value
                    elif any(kw in label for kw in ['票價', 'Price']):
                        if value and value != '未公布':
                            info['price'] = value
                    elif any(kw in label for kw in ['票種', 'Ticket Type']):
                        if value and value != '未公布':
                            info['ticket_types'] = value
            
            # 如果沒找到，用其他方法
            if 'date' not in info:
                date_el = soup.select_one('.date, .event-date, time')
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    if date_text:
                        info['date'] = date_text
                else:
                    info['date'] = self._extract_date_from_text(soup.get_text(" ", strip=True))

            if 'sale_time' not in info:
                info['sale_time'] = extract_sale_time(raw_text)
            
            if 'venue' not in info:
                venue_el = soup.select_one('.venue, .location, .place')
                if venue_el:
                    venue_text = venue_el.get_text(strip=True)
                    if venue_text and venue_text != '未公布':
                        info['venue'] = venue_text
                else:
                    venue_alt = soup.select_one('[class*="venue"], [class*="location"], [class*="place"], [itemprop="location"]')
                    if venue_alt:
                        venue_text = venue_alt.get_text(" ", strip=True)
                        if venue_text and venue_text != '未公布':
                            info['venue'] = venue_text

            if 'price' not in info:
                info['price'] = extract_price_text(raw_text)

            if 'ticket_types' not in info:
                info['ticket_types'] = extract_ticket_types_from_price(info.get('price', ''))
                if info['ticket_types'] == '未公布':
                    info['ticket_types'] = extract_ticket_types(raw_text)

            info['artist'] = clean_artist_text(info.get('artist', ''))

            info['raw_text'] = soup.get_text(" ", strip=True)[:2000]
            
            return info
        except Exception:
            return {}

    def _fallback_placeholder(self) -> List[dict]:
        self.concerts.append(
            build_event_record(
                source=self.site_name,
                artist="（待公佈）",
                url=self.base_url + "/activity/list",
            )
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
        # 目前僅保留：年代售票、iNDIEVOX
        self.level1_crawlers = [TicketCrawler(timeout=per_site_timeout)]
        self.level2_crawlers = [IndievoxCrawler(timeout=per_site_timeout)]
        self.level3_crawlers = []

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
        columns = [
            "來源網站", "活動名稱", "藝人", "搶票時間", "活動時間", "活動地點", "活動地址", "票價", "票種",
            "網址", "爬取時間", "演出藝人", "演出時間", "演出地點"
        ]
        normalized_records = [normalize_record(record) for record in self.all_concerts]
        normalized_records = [record for record in normalized_records if is_valid_concert_record(record)]
        self.all_concerts = normalized_records
        df = pd.DataFrame(normalized_records, columns=columns)
        df = df.drop_duplicates(subset=["來源網站", "網址", "活動名稱", "演出時間", "演出地點"])

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
        help="等級：1=年代售票、2=iNDIEVOX、all=全部"
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