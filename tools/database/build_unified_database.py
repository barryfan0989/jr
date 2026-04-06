import json
import re
import sqlite3
from glob import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "爬蟲資料"
OUT_DIR = DATA_DIR / "整理後"
OUT_JSON = OUT_DIR / "concerts_merged.json"
OUT_DB = OUT_DIR / "concerts_merged.db"
TEAM_CRAWLERS_DIR = ROOT / "組員給的爬蟲"


ARTIST_WHITELIST_PATTERNS = [
    (r"但願人長久.*鄧麗君", "鄧麗君"),
    (r"鄧麗君.*(?:演唱會|音樂會|公演|專場)", "鄧麗君"),
    (r"^MISIA\b|MISIA星空現場", "MISIA"),
]


def get_latest_crawler_json() -> Path | None:
    candidates = sorted(glob(str(ROOT / "演唱會資訊彙整_*.json")), key=lambda p: Path(p).stat().st_mtime)
    return Path(candidates[-1]) if candidates else None


def clean(value, default="未提供") -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return default
    if text == "未公布":
        return "未提供"
    return text


def is_fake_address(value: str) -> bool:
    text = clean(value, "")
    if not text:
        return False
    fake_tokens = ["中清路一段447號", "台中市北區中清路"]
    return any(token in text for token in fake_tokens)


def infer_artist(source_site: str, event_name: str, artist_raw: str) -> str:
    source = clean(source_site, "")
    event = clean(event_name, "未提供")
    artist = clean(artist_raw, "未提供")

    for pattern, mapped_artist in ARTIST_WHITELIST_PATTERNS:
        if re.search(pattern, event, re.I):
            return mapped_artist

    # 非重點來源且已有藝人時直接保留
    if source not in ["年代售票", "iNDIEVOX"] and artist not in ["未提供", "未知藝人"]:
        return artist

    # 只在 artist 缺失或與活動名稱相同時嘗試推斷
    should_infer = artist in ["未提供", "未知藝人"] or artist == event
    if not should_infer:
        return artist

    text = event
    text = re.sub(r"^[\d\s\./\-]+(?:\([^\)]*\)|（[^）]*）)?\s*", "", text)

    def _is_valid_candidate(name: str) -> bool:
        n = clean(name, "")
        if not n:
            return False
        blocked = [
            "高流系", "產業工作大解密", "舞蹈營", "Masterclass", "Session", "大會", "台中站", "台北站",
            "演唱會", "音樂會", "專場", "巡迴", "公演", "活動", "課", "分享夜",
        ]
        if any(token in n for token in blocked):
            return False
        if len(n) < 2 or len(n) > 40:
            return False
        return True

    def _postprocess_candidate(name: str) -> str:
        n = clean(name, "")
        if not n:
            return n
        n = re.sub(r"\s+ALL\s+THE\s+BEST$", "", n, flags=re.I).strip()
        n = re.sub(r"\s+ASIA$", "", n, flags=re.I).strip()
        if n.startswith("巧虎"):
            return "巧虎"
        return n

    # 1) 冒號前主詞（例如：安眠巫師 WiFi aka 守夜人旭章 ： ...）
    if re.search(r"[:：]", text):
        head = re.split(r"[:：]", text, maxsplit=1)[0].strip()
        if _is_valid_candidate(head):
            return _postprocess_candidate(head)

    # 2) 日期後英文團名（例如：3.18 ... BIG CITY GERMS『...』）
    m = re.search(r"(?:^|\s)([A-Z][A-Z0-9&'\.\-\s]{2,30})\s*[『「《\"“]", text)
    if m:
        cand = m.group(1).strip()
        if _is_valid_candidate(cand):
            return _postprocess_candidate(cand)

    # 3) 中文名 + 括號/書名號（例如：龍千玉【...】）
    m = re.search(r"^([\u4e00-\u9fffA-Za-z0-9·・\-\s]{2,20})\s*[【《「『]", text)
    if m:
        cand = m.group(1).strip()
        if _is_valid_candidate(cand):
            return _postprocess_candidate(cand)

    # 4) XX演唱會/巡迴... 前綴（例如：周杰倫巡迴演唱會）
    m = re.search(r"^([\u4e00-\u9fffA-Za-z0-9·・\-\s]{2,24}?)(?:演唱會|音樂會|專場|公演|巡迴|演出)", text)
    if m:
        cand = m.group(1).strip()
        if _is_valid_candidate(cand):
            return _postprocess_candidate(cand)

    # 5) 國際XX日
    m = re.search(r"國際([\u4e00-\u9fffA-Za-z0-9·・\-\s]{2,12})日", text)
    if m:
        cand = m.group(1).strip()
        if _is_valid_candidate(cand):
            return _postprocess_candidate(cand)

    # 6) 英文藝人 + LIVE/CONCERT/TOUR
    m = re.search(r"^([A-Za-z][A-Za-z0-9&'\.\-\s]{1,40}?)\s+(?:LIVE|CONCERT|TOUR)\b", text, re.I)
    if m:
        cand = re.sub(r"\s+(?:ASIA|WORLD|LIVE|CONCERT|TOUR|IN)$", "", m.group(1), flags=re.I).strip()
        if _is_valid_candidate(cand):
            return _postprocess_candidate(cand)

    # 推斷失敗，避免錯值繼續污染
    return "未提供"


def make_record(
    source_site: str,
    event_name: str,
    artist: str,
    sale_time: str,
    event_time: str,
    venue: str,
    price: str,
    ticket_types: str,
    url: str,
    crawl_time: str,
    source_file: str,
    address: str = "未提供",
) -> Dict:
    return {
        "來源網站": clean(source_site, "未知來源"),
        "活動名稱": clean(event_name),
        "藝人": clean(artist, "未知藝人"),
        "搶票時間": clean(sale_time),
        "活動時間": clean(event_time),
        "活動地點": clean(venue),
        "活動地址": clean(address),
        "票價": clean(price),
        "票種": clean(ticket_types),
        "網址": clean(url, ""),
        "爬取時間": clean(crawl_time, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "資料來源檔": source_file,
    }


def pick_existing_path(*paths: Path) -> Path | None:
    for path in paths:
        if path and path.exists():
            return path
    return None


def load_crawler_json(path: Path) -> List[Dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for row in rows:
        source_site = row.get("來源網站", "未知來源")
        event_name = row.get("活動名稱") or row.get("藝人") or row.get("演出藝人", "未公布")
        artist_raw = row.get("藝人") or row.get("演出藝人", "未知藝人")
        artist = infer_artist(source_site, event_name, artist_raw)
        sale_time = row.get("搶票時間", "未公布")
        sale_time_clean = clean(sale_time)
        if sale_time_clean in [clean(event_name), clean(artist)]:
            sale_time_clean = "未提供"

        address = row.get("活動地址", "未提供")
        address_clean = clean(address)
        if is_fake_address(address_clean):
            address_clean = "未提供"

        out.append(
            make_record(
                source_site=source_site,
                event_name=event_name,
                artist=artist,
                sale_time=sale_time_clean,
                event_time=row.get("活動時間") or row.get("演出時間", "未公布"),
                venue=row.get("活動地點") or row.get("演出地點", "未公布"),
                address=address_clean,
                price=row.get("票價", "未公布"),
                ticket_types=row.get("票種", "未公布"),
                url=row.get("網址", ""),
                crawl_time=row.get("爬取時間", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                source_file=path.name,
            )
        )
    return out


def load_tixcraft_json(path: Path) -> List[Dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    scrape_time = clean(data.get("scrape_time"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    events = data.get("events", [])
    out = []
    for row in events:
        out.append(
            make_record(
                source_site="Tixcraft",
                event_name=row.get("event_name", "未公布"),
                artist=row.get("artist_name") or row.get("event_name", "未知藝人"),
                sale_time=row.get("sale_time", "未公布"),
                event_time=row.get("event_time", "未公布"),
                venue=row.get("venue_name", "未公布"),
                address=row.get("address", "未提供"),
                price=row.get("ticket_price", "未公布"),
                ticket_types=row.get("ticket_types", "未公布"),
                url=row.get("event_link", ""),
                crawl_time=scrape_time,
                source_file=path.name,
            )
        )
    return out


def load_kktix_excel(path: Path) -> List[Dict]:
    df = pd.read_excel(path, sheet_name=0)
    out = []
    for _, row in df.iterrows():
        sale_date = clean(row.get("啟售日期"), "")
        sale_clock = clean(row.get("啟售時間"), "")
        if sale_date and sale_clock:
            sale_time = f"{sale_date} {sale_clock}"
        else:
            sale_time = sale_date or sale_clock or "未公布"

        venue = clean(row.get("活動地點"), "未公布")
        address = clean(row.get("活動地址"), "")

        out.append(
            make_record(
                source_site="KKTIX",
                event_name=row.get("活動名稱", "未公布"),
                artist=row.get("演出藝人") or row.get("活動名稱", "未知藝人"),
                sale_time=sale_time,
                event_time=row.get("活動日期", "未公布"),
                venue=venue,
                address=address or "未提供",
                price=row.get("票價", "未公布"),
                ticket_types=row.get("票種", "未公布"),
                url=row.get("活動連結", ""),
                crawl_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source_file=path.name,
            )
        )
    return out


def _extract_yuanda_sale_time(raw: str) -> str:
    """從遠大售票的冗長搶票說明文字中抽取開賣時間。"""
    import re
    if not raw or raw.strip().lower() == "nan":
        return "未提供"
    # 嘗試「開賣時間｜2026.03.20（FRI）12:00 PM」
    m = re.search(r"開賣時間[｜|：:]\s*([^\n/（(]+)", raw)
    if m:
        return m.group(1).strip()
    # 取第一個分段 (以 " / " 切)
    first = raw.split(" / ")[0].strip()
    if re.search(r"\d{4}[./年]\d{1,2}", first):
        return first
    # fallback: 找任何 YYYY.MM.DD HH:MM 型式
    m = re.search(r"(\d{4}[./年]\d{1,2}[./月]\d{1,2}[^\s]*\s*\d{1,2}:\d{2})", raw)
    if m:
        return m.group(1).strip()
    return first if first else "未提供"


def _split_yuanda_venue_address(venue_text: str):
    """分離『場館名稱（地址）』中的場館與地址。"""
    import re
    if not venue_text:
        return "未提供", "未提供"
    m = re.search(r"[（(]([^）)]+)[）)]", venue_text)
    if m:
        addr = re.sub(r"\s+演出時間.*$", "", m.group(1)).strip()
        venue = venue_text[: m.start()].strip()
        return (venue or "未提供"), addr
    return venue_text.strip(), "未提供"


def _extract_yuanda_ticket_types(price_info: str) -> str:
    """從「VIP：NT$2400 ｜ ADV：NT$1200」格式提取票種名稱。"""
    import re
    if not price_info or price_info.strip().lower() == "nan":
        return "未提供"
    types = re.findall(r"([A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s]*)[：:][^\|｜]+", price_info)
    cleaned = [t.strip() for t in types if t.strip()]
    return " ｜ ".join(cleaned) if cleaned else "未提供"


def load_yuanda_excel(path: Path) -> List[Dict]:
    df = pd.read_excel(path, sheet_name=0)
    out = []
    for _, row in df.iterrows():
        event_name = clean(row.get("活動名稱"), "未提供")

        # 活動時間：合併活動日期 + 演出時間
        event_date = clean(row.get("活動日期"), "")
        perf_time = clean(row.get("演出時間"), "")
        if event_date and perf_time:
            event_time = f"{event_date} {perf_time}"
        else:
            event_time = event_date or perf_time or "未提供"

        # 搶票時間：從冗長文字中抽取
        sale_time_raw = str(row.get("搶票時間", "")) if pd.notna(row.get("搶票時間")) else ""
        sale_time = _extract_yuanda_sale_time(sale_time_raw)

        # 場地 + 地址
        venue_raw = clean(row.get("活動場地"), "")
        venue, address = _split_yuanda_venue_address(venue_raw)

        # 票價
        price = clean(row.get("票價資訊"), "未提供")

        # 票種：從票價欄位提取
        ticket_types = _extract_yuanda_ticket_types(price)

        url = clean(row.get("活動頁面"), "")
        crawl_time = clean(str(row.get("爬取時間", "")), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        out.append(
            make_record(
                source_site="遠大售票 TicketPlus",
                event_name=event_name,
                artist=event_name,  # 遠大資料無獨立藝人欄位，以活動名稱代替
                sale_time=sale_time,
                event_time=event_time,
                venue=venue,
                address=address,
                price=price,
                ticket_types=ticket_types,
                url=url,
                crawl_time=crawl_time,
                source_file=path.name,
            )
        )
    return out


def load_kham_excel(path: Path) -> List[Dict]:
    activities = pd.read_excel(path, sheet_name="活動")
    locations = pd.read_excel(path, sheet_name="活動地點")
    artists = pd.read_excel(path, sheet_name="藝人")
    platforms = pd.read_excel(path, sheet_name="售票平台")

    loc_map = {
        clean(row.get("場地編號PK"), ""): {
            "場地名稱": clean(row.get("場地名稱"), "未公布"),
            "地址": clean(row.get("地址"), ""),
        }
        for _, row in locations.iterrows()
    }
    artist_map = {
        clean(row.get("藝人編號PK"), ""): clean(row.get("藝人名稱"), "未知藝人")
        for _, row in artists.iterrows()
    }
    platform_map = {
        clean(row.get("活動編號FK"), ""): clean(row.get("平台名稱"), "寬宏售票")
        for _, row in platforms.iterrows()
    }

    out = []
    for _, row in activities.iterrows():
        act_id = clean(row.get("活動編號PK"), "")
        loc_fk = clean(row.get("場地編號FK"), "")
        artist_fk = clean(row.get("藝人編號FK"), "")

        loc = loc_map.get(loc_fk, {"場地名稱": "未公布", "地址": ""})
        venue = loc.get("場地名稱", "未公布")
        address = clean(loc.get("地址"), "未提供")

        artist = artist_map.get(artist_fk, "未知藝人")
        if artist in ["未知藝人", "未提供", "未提供藝人"]:
            artist = clean(row.get("活動名稱"), "未知藝人")

        out.append(
            make_record(
                source_site=platform_map.get(act_id, "寬宏售票"),
                event_name=row.get("活動名稱", "未公布"),
                artist=artist,
                sale_time=row.get("售票時間", "未公布"),
                event_time=row.get("活動時間", "未公布"),
                venue=venue,
                address=address,
                price=row.get("票價", "未公布"),
                ticket_types=row.get("票種", "未公布"),
                url=row.get("活動連結", ""),
                crawl_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source_file=path.name,
            )
        )
    return out


def load_kham_csv_folder(folder: Path) -> List[Dict]:
    activities = pd.read_csv(folder / "活動.csv")
    locations = pd.read_csv(folder / "活動地點.csv")
    artists = pd.read_csv(folder / "藝人.csv")
    platforms = pd.read_csv(folder / "售票平台.csv")

    loc_map = {
        clean(row.get("場地編號PK"), ""): {
            "場地名稱": clean(row.get("場地名稱"), "未公布"),
            "地址": clean(row.get("地址"), ""),
        }
        for _, row in locations.iterrows()
    }
    artist_map = {
        clean(row.get("藝人編號PK"), ""): clean(row.get("藝人名稱"), "未知藝人")
        for _, row in artists.iterrows()
    }
    platform_map = {
        clean(row.get("活動編號FK"), ""): clean(row.get("平台名稱"), "寬宏售票")
        for _, row in platforms.iterrows()
    }

    out = []
    for _, row in activities.iterrows():
        act_id = clean(row.get("活動編號PK"), "")
        loc_fk = clean(row.get("場地編號FK"), "")
        artist_fk = clean(row.get("藝人編號FK"), "")

        loc = loc_map.get(loc_fk, {"場地名稱": "未公布", "地址": ""})
        venue = loc.get("場地名稱", "未公布")
        address = clean(loc.get("地址"), "未提供")

        artist = artist_map.get(artist_fk, "未知藝人")
        if artist in ["未知藝人", "未提供", "未提供藝人"]:
            artist = clean(row.get("活動名稱"), "未知藝人")

        out.append(
            make_record(
                source_site=platform_map.get(act_id, "寬宏售票"),
                event_name=row.get("活動名稱", "未公布"),
                artist=artist,
                sale_time=row.get("售票時間", "未公布"),
                event_time=row.get("活動時間", "未公布"),
                venue=venue,
                address=address,
                price=row.get("票價", "未公布"),
                ticket_types=row.get("票種", "未公布"),
                url=row.get("活動連結", ""),
                crawl_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source_file=f"{folder.name}/活動.csv",
            )
        )
    return out


def load_ibon_json(path: Path) -> List[Dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    out = []
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for row in rows:
        out.append(
            make_record(
                source_site="ibon售票",
                event_name=row.get("活動名稱", "未公布"),
                artist=row.get("藝人") or row.get("活動名稱", "未知藝人"),
                sale_time=row.get("搶票時間", "未公布"),
                event_time=row.get("活動時間", "未公布"),
                venue=row.get("地點", "未公布"),
                address=row.get("地址", "未提供"),
                price=row.get("票價", "未公布"),
                ticket_types=row.get("票種", "未公布"),
                url=row.get("活動連結", ""),
                crawl_time=now_text,
                source_file=path.name,
            )
        )
    return out


def load_ticketplus_json(path: Path) -> List[Dict]:
    """載入新的遠大售票爬蟲輸出 (ticketplus_activities.json)"""
    rows = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for row in rows:
        # 從活動場地中分離場館名和地址
        venue_raw = clean(row.get("活動場地"), "")
        import re
        venue_match = re.search(r"^([^（(]+)", venue_raw)
        venue = venue_match.group(1).strip() if venue_match else venue_raw
        addr_match = re.search(r"[（(]([^）)]+)[）)]", venue_raw)
        address = addr_match.group(1).strip() if addr_match else "未提供"
        
        out.append(
            make_record(
                source_site="遠大售票 TicketPlus",
                event_name=row.get("活動名稱", "未公布"),
                artist=row.get("活動名稱", "未知藝人"),  # 無獨立藝人欄位，使用活動名稱
                sale_time=row.get("搶票時間", "未公布"),
                event_time=row.get("活動日期", "未公布"),
                venue=clean(venue, "未公布"),
                address=clean(address, "未提供"),
                price=clean(row.get("票價資訊"), "未公布"),
                ticket_types=row.get("票種", "未公布"),
                url=row.get("活動頁面", ""),
                crawl_time=clean(row.get("爬取時間"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                source_file=path.name,
            )
        )
    return out


def dedupe(records: List[Dict]) -> List[Dict]:
    result = []
    seen = set()
    for row in records:
        url = clean(row.get("網址"), "")
        if url:
            key = (url,)
        else:
            key = (
                clean(row.get("來源網站")),
                clean(row.get("活動名稱")),
                clean(row.get("活動時間")),
                clean(row.get("活動地點")),
            )
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def write_sqlite(records: List[Dict], db_path: Path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS concerts")
    cur.execute(
        """
        CREATE TABLE concerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            來源網站 TEXT,
            活動名稱 TEXT,
            藝人 TEXT,
            搶票時間 TEXT,
            活動時間 TEXT,
            活動地點 TEXT,
            活動地址 TEXT,
            票價 TEXT,
            票種 TEXT,
            網址 TEXT,
            爬取時間 TEXT,
            資料來源檔 TEXT
        )
        """
    )
    cur.executemany(
        """
        INSERT INTO concerts (
            來源網站, 活動名稱, 藝人, 搶票時間, 活動時間,
            活動地點, 活動地址, 票價, 票種, 網址, 爬取時間, 資料來源檔
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["來源網站"],
                row["活動名稱"],
                row["藝人"],
                row["搶票時間"],
                row["活動時間"],
                row["活動地點"],
                row["活動地址"],
                row["票價"],
                row["票種"],
                row["網址"],
                row["爬取時間"],
                row["資料來源檔"],
            )
            for row in records
        ],
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_concerts_site ON concerts(來源網站)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_concerts_time ON concerts(活動時間)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_concerts_url ON concerts(網址)")
    conn.commit()
    conn.close()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records: List[Dict] = []
    source_stats = {}

    crawler_json = get_latest_crawler_json()
    if crawler_json and crawler_json.exists():
        part = load_crawler_json(crawler_json)
        records.extend(part)
        source_stats[crawler_json.name] = len(part)

    # 優先使用「組員給的爬蟲」新資料；舊路徑作為備援
    tix_path = pick_existing_path(
        DATA_DIR / "tixcraft_activities_new.json",
        TEAM_CRAWLERS_DIR / "Tixcraft 爬蟲" / "tixcraft_activities.json",
        DATA_DIR / "tixcraft_activities.json",
    )
    if tix_path:
        part = load_tixcraft_json(tix_path)
        records.extend(part)
        source_stats[tix_path.name] = len(part)

    kktix_path = pick_existing_path(
        TEAM_CRAWLERS_DIR / "kktix爬蟲" / "kktix_events_report.xlsx",
        DATA_DIR / "kktix_events_report.xlsx",
    )
    if kktix_path:
        part = load_kktix_excel(kktix_path)
        records.extend(part)
        source_stats[kktix_path.name] = len(part)

    kham_excel_path = pick_existing_path(
        TEAM_CRAWLERS_DIR / "寬宏爬蟲" / "kham_data.xlsx",
        DATA_DIR / "寬宏.xlsx",
    )
    if kham_excel_path:
        part = load_kham_excel(kham_excel_path)
        records.extend(part)
        source_stats[kham_excel_path.name] = len(part)
    else:
        kham_csv_folder = TEAM_CRAWLERS_DIR / "寬宏爬蟲"
        required_csv = [
            kham_csv_folder / "活動.csv",
            kham_csv_folder / "活動地點.csv",
            kham_csv_folder / "藝人.csv",
            kham_csv_folder / "售票平台.csv",
        ]
        if all(p.exists() for p in required_csv):
            part = load_kham_csv_folder(kham_csv_folder)
            records.extend(part)
            source_stats[f"{kham_csv_folder.name}/*.csv"] = len(part)

    ibon_path = pick_existing_path(
        TEAM_CRAWLERS_DIR / "ibon爬蟲" / "ibon_all_data.json",
        DATA_DIR / "ibon_all_data.json",
    )
    if ibon_path:
        part = load_ibon_json(ibon_path)
        records.extend(part)
        source_stats[ibon_path.name] = len(part)

    yuanda_path = DATA_DIR / "遠大.xlsx"
    if yuanda_path.exists():
        part = load_yuanda_excel(yuanda_path)
        records.extend(part)
        source_stats[yuanda_path.name] = len(part)

    # 新的遠大爬蟲輸出 (ticketplus)
    ticketplus_json = pick_existing_path(
        TEAM_CRAWLERS_DIR / "遠大爬蟲" / "爬蟲資料" / "ticketplus_output" / "ticketplus_activities.json",
        DATA_DIR / "ticketplus_output" / "ticketplus_activities.json",
    )
    if ticketplus_json:
        part = load_ticketplus_json(ticketplus_json)
        records.extend(part)
        source_stats[ticketplus_json.name] = len(part)

    deduped = dedupe(records)

    OUT_JSON.write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8")
    write_sqlite(deduped, OUT_DB)

    print("=== 整理完成 ===")
    print(f"輸出 JSON: {OUT_JSON}")
    print(f"輸出 DB  : {OUT_DB}")
    print(f"原始總筆數: {len(records)}")
    print(f"去重後筆數: {len(deduped)}")
    print("來源統計:")
    for name, count in source_stats.items():
        print(f"  - {name}: {count}")


if __name__ == "__main__":
    main()
