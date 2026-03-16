# -*- coding: utf-8 -*-
"""
建立 ER 正規化資料表（含 PK/FK）並從 concerts_merged.json 匯入。

新增表：
- er_users
- er_artists
- er_venues
- er_platforms
- er_events

說明：
- 不會刪除既有 events 表，避免影響原流程
- 以 er_* 表提供 ER 關聯格式查詢
"""

import json
import re
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parents[2]
MERGED_JSON = ROOT / "爬蟲資料" / "整理後" / "concerts_merged.json"
USERS_JSON = ROOT / "data" / "users.json"

DB_CONFIG = dict(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="barry0803",
    database="concerts",
    charset="utf8mb4",
    collation="utf8mb4_unicode_ci",
    autocommit=False,
)


def clean(value, default="未提供") -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return default
    if text == "未公布":
        return "未提供"
    return text


def _is_suspicious_artist_name(name: str, event_name: str) -> bool:
    n = clean(name, "")
    e = clean(event_name, "")
    if not n:
        return True
    if n in {"未提供", "未知", "未知藝人", "KKTIX", "LIVE", "Tickets in Japan"}:
        return True
    if re.match(r"^20\d{2}(?:[-./]\d{2})?\b", n):
        return True
    if n == e:
        return True
    suspicious_tokens = ["演唱會", "音樂會", "巡迴", "登記抽選", "VIP PASS", "限量加購", " in Taipei", " IN TAIPEI"]
    if any(token in n for token in suspicious_tokens):
        return True
    if re.search(r"\b(?:TOUR|LIVE|CONCERT)\b", n, re.I):
        return True
    return False


def _sanitize_artist_text(name: str) -> str:
    n = clean(name, "")
    if not n:
        return ""
    n = re.sub(r"^20\d{2}(?:[-./]\d{2})?\s*[·‧・]?\s*", "", n).strip()
    n = re.sub(r"\s*登記抽選$", "", n)
    n = re.sub(r"\s*VIP PASS.*$", "", n, flags=re.I)
    n = re.sub(r"\s*限量加購.*$", "", n)
    n = re.sub(r"\s+(?:TOUR|CONCERT|FAN\s*MEETING|FANMEETING|SHOWCASE)\b.*$", "", n, flags=re.I).strip()
    n = re.sub(r"\s+LIVE\b.*$", "", n, flags=re.I).strip()
    if n in {"KKTIX", "LIVE", "Tickets", "Tickets in Japan", "Unknown", "UNKNOWN", "未知"}:
        return "未提供"
    return n or "未提供"


def _infer_artist_from_event_name(event_name: str) -> str:
    text = clean(event_name, "")
    if not text:
        return "未提供"

    # 移除前綴促銷標籤
    text = re.sub(r"^\[(?:身心障礙優惠票購票頁面)\]\s*", "", text)
    text = re.sub(r"^【(?:Mastercard專區|預購商品)】\s*", "", text)

    # 移除尾端非藝人資訊
    text = re.sub(r"\s*登記抽選$", "", text)
    text = re.sub(r"\s*VIP PASS.*$", "", text, flags=re.I)
    text = re.sub(r"\s*限量加購.*$", "", text)
    text = re.sub(r"^20\d{2}(?:[-./]\d{2})?\s*", "", text)

    # 先處理常見分隔："A - B Tour..." / "A – B Live..."
    split_dash = re.split(r"\s[-–—]\s", text, maxsplit=1)
    if split_dash:
        left = clean(split_dash[0], "")
        if 2 <= len(left) <= 60 and left.upper() not in {"KKTIX", "LIVE"}:
            if re.search(r"[A-Za-z\u4e00-\u9fff]", left):
                text = left

    patterns = [
        r"^([A-Za-z][A-Za-z0-9&'\.\-\s]{1,40}?)(?=\s+(?:TOUR|LIVE|CONCERT|FAN\s*MEETING|ONEMAN|WORLD|SHOWCASE)\b)",
        r"^([A-Za-z][A-Za-z0-9&'\.\-\s]{1,40}?)(?=\s+(?:ASIA\s+)?(?:TOUR|LIVE|CONCERT|FAN\s*MEETING|ONEMAN|WORLD)|\s+(?:in|IN)\s+[A-Z])",
        r"^([\u4e00-\u9fffA-Za-z0-9·・\-\s]{2,24}?)(?=《|【|「|『|演唱會|音樂會|巡迴|公演|專場)",
        r"^([\u4e00-\u9fffA-Za-z0-9&'\.\-\s]{2,50}?)(?=\s+(?:in|IN)\s+(?:TAIPEI|KAOHSIUNG|TAICHUNG|TAINAN))",
        r"^([\u4e00-\u9fffA-Za-z0-9&'\.\-\sxX]+?)(?=\s+[—–-]\s+Live)",
        r"^([A-Za-z][A-Za-z0-9&'\.\-\s]{1,40}?)(?=\s+(?:TOUR|LIVE|CONCERT))",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            candidate = clean(m.group(1), "")
            candidate = re.sub(r"\s+ASIA$", "", candidate, flags=re.I).strip()
            candidate = re.sub(r"\s+WORLD$", "", candidate, flags=re.I).strip()
            candidate = re.sub(r"^20\d{2}(?:[-./]\d{2})?\s*", "", candidate).strip()
            if 2 <= len(candidate) <= 60 and candidate.upper() not in {"KKTIX", "LIVE"}:
                return candidate

    # 若名稱像「Xxx Tour / Xxx Live ...」，取第一段
    m = re.search(r"^([A-Za-z\u4e00-\u9fff0-9&'\.\-\s]{2,50})", text)
    if m:
        candidate = clean(m.group(1), "")
        candidate = re.sub(r"^20\d{2}(?:[-./]\d{2})?\s*", "", candidate).strip()
        candidate = re.sub(r"\s+(?:TOUR|LIVE|CONCERT).*$", "", candidate, flags=re.I).strip()
        if 2 <= len(candidate) <= 60 and candidate.upper() not in {"KKTIX", "LIVE"}:
            return candidate

    return "未提供"


def normalize_artist_name(raw_artist: str, event_name: str, source_site: str = "") -> str:
    artist = _sanitize_artist_text(raw_artist)
    event = clean(event_name)

    if artist in {"未知", "未知藝人", "Unknown", "UNKNOWN", "未提供"}:
        artist = "未提供"

    source = clean(source_site, "")
    if source == "Tixcraft":
        sports_tokens = ["例行賽", "主場賽事", "入場券", "門票"]
        if any(token in event for token in sports_tokens):
            return "未提供"

    if not _is_suspicious_artist_name(artist, event):
        return artist

    inferred = _infer_artist_from_event_name(event)
    inferred = _sanitize_artist_text(inferred)
    if inferred and inferred not in {"未提供", "未知藝人", "KKTIX", "LIVE"}:
        return inferred

    return "未提供"


def create_schema(cur):
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("DROP VIEW IF EXISTS er_events_view")
    cur.execute("DROP TABLE IF EXISTS er_events")
    cur.execute("DROP TABLE IF EXISTS er_users")
    cur.execute("DROP TABLE IF EXISTS er_artists")
    cur.execute("DROP TABLE IF EXISTS er_venues")
    cur.execute("DROP TABLE IF EXISTS er_platforms")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")

    cur.execute(
        """
        CREATE TABLE er_users (
            user_id_pk BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            app_user_uuid VARCHAR(64) NOT NULL,
            username VARCHAR(120) NOT NULL,
            email VARCHAR(255) NOT NULL,
            password_hash TEXT NOT NULL,
            created_at_text VARCHAR(64) NOT NULL,
            PRIMARY KEY (user_id_pk),
            UNIQUE KEY uk_app_user_uuid (app_user_uuid),
            UNIQUE KEY uk_username (username)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute(
        """
        CREATE TABLE er_artists (
            artist_id_pk BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            artist_name VARCHAR(255) NOT NULL,
            PRIMARY KEY (artist_id_pk),
            UNIQUE KEY uk_artist_name (artist_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE er_venues (
            venue_id_pk BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            venue_name VARCHAR(255) NOT NULL,
            address VARCHAR(255) NOT NULL,
            PRIMARY KEY (venue_id_pk),
            UNIQUE KEY uk_venue_name_addr (venue_name, address)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute(
        """
        CREATE TABLE er_platforms (
            platform_id_pk BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            platform_name VARCHAR(255) NOT NULL,
            PRIMARY KEY (platform_id_pk),
            UNIQUE KEY uk_platform_name (platform_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute(
        """
        CREATE TABLE er_events (
            event_id_pk BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            event_name VARCHAR(500) NOT NULL,
            artist_id_fk BIGINT UNSIGNED NULL,
            venue_id_fk BIGINT UNSIGNED NULL,
            platform_id_fk BIGINT UNSIGNED NULL,
            event_time TEXT NOT NULL,
            sale_time TEXT NOT NULL,
            price TEXT NOT NULL,
            ticket_type TEXT NOT NULL,
            event_link TEXT NOT NULL,
            crawl_time TEXT NOT NULL,
            source_file VARCHAR(255) NOT NULL,
            PRIMARY KEY (event_id_pk),
            CONSTRAINT fk_events_artist FOREIGN KEY (artist_id_fk)
                REFERENCES er_artists (artist_id_pk)
                ON UPDATE CASCADE ON DELETE SET NULL,
            CONSTRAINT fk_events_venue FOREIGN KEY (venue_id_fk)
                REFERENCES er_venues (venue_id_pk)
                ON UPDATE CASCADE ON DELETE SET NULL,
            CONSTRAINT fk_events_platform FOREIGN KEY (platform_id_fk)
                REFERENCES er_platforms (platform_id_pk)
                ON UPDATE CASCADE ON DELETE SET NULL,
            UNIQUE KEY uk_event_dedupe (event_name(255), event_time(120), venue_id_fk, platform_id_fk, event_link(255))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def create_views(cur):
    cur.execute(
        """
        CREATE VIEW er_events_view AS
        SELECT
            e.event_id_pk,
            e.event_name AS 活動名稱,
            a.artist_name AS 藝人,
            e.sale_time AS 售票時間,
            e.event_time AS 活動時間,
            v.venue_name AS 活動地點,
            v.address AS 地址,
            e.price AS 票價,
            e.ticket_type AS 票種,
            p.platform_name AS 售票平台,
            e.event_link AS 活動連結,
            e.crawl_time AS 爬取時間,
            e.source_file AS 資料來源檔
        FROM er_events e
        LEFT JOIN er_artists a ON e.artist_id_fk = a.artist_id_pk
        LEFT JOIN er_venues v ON e.venue_id_fk = v.venue_id_pk
        LEFT JOIN er_platforms p ON e.platform_id_fk = p.platform_id_pk
        """
    )

def get_or_create_artist(cur, cache: dict, artist_name: str) -> int:
    key = clean(artist_name)
    if key in cache:
        return cache[key]
    cur.execute("INSERT IGNORE INTO er_artists (artist_name) VALUES (%s)", (key,))
    cur.execute("SELECT artist_id_pk FROM er_artists WHERE artist_name=%s", (key,))
    artist_id = cur.fetchone()[0]
    cache[key] = artist_id
    return artist_id


def get_or_create_venue(cur, cache: dict, venue_name: str, address: str) -> int:
    venue = clean(venue_name)
    addr = clean(address)
    key = (venue, addr)
    if key in cache:
        return cache[key]
    cur.execute(
        "INSERT IGNORE INTO er_venues (venue_name, address) VALUES (%s, %s)",
        (venue, addr),
    )
    cur.execute(
        "SELECT venue_id_pk FROM er_venues WHERE venue_name=%s AND address=%s",
        (venue, addr),
    )
    venue_id = cur.fetchone()[0]
    cache[key] = venue_id
    return venue_id


def get_or_create_platform(cur, cache: dict, platform_name: str) -> int:
    key = clean(platform_name)
    if key in cache:
        return cache[key]
    cur.execute("INSERT IGNORE INTO er_platforms (platform_name) VALUES (%s)", (key,))
    cur.execute("SELECT platform_id_pk FROM er_platforms WHERE platform_name=%s", (key,))
    platform_id = cur.fetchone()[0]
    cache[key] = platform_id
    return platform_id


def import_users(cur) -> int:
    if not USERS_JSON.exists():
        return 0

    raw = json.loads(USERS_JSON.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return 0

    inserted = 0
    for _, user in raw.items():
        user_id = clean(user.get("user_id"), "")
        username = clean(user.get("username"), "")
        email = clean(user.get("email"), "")
        password_hash = clean(user.get("password"), "")
        created_at = clean(user.get("created_at"), "")

        if not user_id or not username:
            continue

        cur.execute(
            """
            INSERT IGNORE INTO er_users (
                app_user_uuid, username, email, password_hash, created_at_text
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, username, email, password_hash, created_at),
        )
        inserted += cur.rowcount

    return inserted


def import_events(cur) -> int:
    if not MERGED_JSON.exists():
        raise SystemExit(f"找不到檔案: {MERGED_JSON}")

    rows = json.loads(MERGED_JSON.read_text(encoding="utf-8"))

    artist_cache = {}
    venue_cache = {}
    platform_cache = {}

    inserted = 0
    for row in rows:
        normalized_artist = normalize_artist_name(row.get("藝人"), row.get("活動名稱"), row.get("來源網站"))
        artist_id = get_or_create_artist(cur, artist_cache, normalized_artist)
        venue_id = get_or_create_venue(cur, venue_cache, row.get("活動地點"), row.get("活動地址"))
        platform_id = get_or_create_platform(cur, platform_cache, row.get("來源網站"))

        cur.execute(
            """
            INSERT IGNORE INTO er_events (
                event_name, artist_id_fk, venue_id_fk, platform_id_fk,
                event_time, sale_time, price, ticket_type,
                event_link, crawl_time, source_file
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                clean(row.get("活動名稱")),
                artist_id,
                venue_id,
                platform_id,
                clean(row.get("活動時間")),
                clean(row.get("搶票時間")),
                clean(row.get("票價")),
                clean(row.get("票種")),
                clean(row.get("網址"), ""),
                clean(row.get("爬取時間")),
                clean(row.get("資料來源檔"), MERGED_JSON.name),
            ),
        )
        inserted += cur.rowcount

    return inserted


def print_stats(cur):
    table_list = ["er_users", "er_artists", "er_venues", "er_platforms", "er_events"]
    print("\n=== ER 資料表筆數 ===")
    for table in table_list:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"{table}: {cur.fetchone()[0]}")

    print("\n=== 範例關聯查詢（活動 + 藝人 + 場地 + 平台）===")
    cur.execute(
        """
        SELECT
            e.event_name,
            a.artist_name,
            v.venue_name,
            p.platform_name,
            e.event_time
        FROM er_events e
        LEFT JOIN er_artists a ON e.artist_id_fk = a.artist_id_pk
        LEFT JOIN er_venues v ON e.venue_id_fk = v.venue_id_pk
        LEFT JOIN er_platforms p ON e.platform_id_fk = p.platform_id_pk
        ORDER BY e.event_id_pk DESC
        LIMIT 5
        """
    )
    for row in cur.fetchall():
        print(row)


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    create_schema(cur)
    users_count = import_users(cur)
    events_count = import_events(cur)
    create_views(cur)

    conn.commit()

    print("✅ ER schema 建立完成（含 PK / FK）")
    print(f"匯入 users: {users_count}")
    print(f"匯入 events: {events_count}")
    print("已建立 view: er_events_view")

    print_stats(cur)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
