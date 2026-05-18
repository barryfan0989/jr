# -*- coding: utf-8 -*-
"""
載入 concerts_merged.json 到 MySQL，建立正規化資料表：
- venues: 場地主檔（含場地簡介）
- artists: 藝人主檔（含藝人介紹）
- events: 活動主檔（保留原先 12 欄）
- event_artists: 活動-藝人多對多
- artist_news: 藝人新聞
"""

import json
import re
import os
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parents[2]
MERGED_JSON = ROOT / "爬蟲資料" / "整理後" / "concerts_merged.json"

CANONICAL_COLUMNS = [
    "來源網站",
    "活動名稱",
    "藝人",
    "搶票時間",
    "活動時間",
    "活動地點",
    "活動地址",
    "票價",
    "票種",
    "網址",
    "爬取時間",
    "資料來源檔",
]

DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "barry0803"),
    database=os.getenv("DB_NAME", "concerts"),
    charset="utf8mb4",
    collation="utf8mb4_unicode_ci",
    autocommit=False,
    ssl_verify_cert=False,
    ssl_verify_identity=False,
)

FAKE_ADDRESSES = ["中清路一段447號", "台中市北區中清路"]
ARTIST_SPLIT_REGEX = r"\s*(?:、|，|,|/|\||＆|&|\band\b|\bfeat\.?\b|\bft\.?\b|\bx\b)\s*"


def clean(value, default="未提供") -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none", ""):
        return default
    if text in ("未公布", "未知", "null"):
        return default
    return text


def is_fake_address(addr: str) -> bool:
    return any(token in addr for token in FAKE_ADDRESSES)


def normalize_row(raw: dict) -> dict:
    source = clean(raw.get("來源網站") or raw.get("平台名稱"), "未提供")

    event_name = clean(
        raw.get("活動名稱") or raw.get("藝人") or raw.get("演出藝人"), "未提供"
    )

    artist = clean(raw.get("藝人") or raw.get("演出藝人"), "未提供")

    sale_date = clean(raw.get("啟售日期"), "")
    sale_clock = clean(raw.get("啟售時間"), "")
    if sale_date and sale_clock:
        sale_combined = f"{sale_date} {sale_clock}"
    else:
        sale_combined = sale_date or sale_clock or ""

    sale_time = clean(
        raw.get("搶票時間") or raw.get("售票時間") or sale_combined, "未提供"
    )
    if sale_time == event_name or sale_time == artist:
        sale_time = "未提供"

    event_time = clean(
        raw.get("活動時間") or raw.get("演出時間") or raw.get("活動日期"), "未提供"
    )

    venue = clean(
        raw.get("活動地點") or raw.get("演出地點") or raw.get("場地名稱"), "未提供"
    )

    raw_addr = clean(raw.get("活動地址") or raw.get("地址"), "")
    address = "未提供" if (not raw_addr or is_fake_address(raw_addr)) else raw_addr

    price = clean(raw.get("票價") or raw.get("ticket_price"), "未提供")
    ticket_types = clean(raw.get("票種") or raw.get("ticket_types"), "未提供")
    url = clean(raw.get("網址") or raw.get("活動連結") or raw.get("event_link"), "未提供")
    crawl_time = clean(raw.get("爬取時間"), "未提供")
    source_file = clean(raw.get("資料來源檔"), MERGED_JSON.name)

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
        "資料來源檔": source_file,
    }


def split_artists(artist_text: str, event_name: str) -> list[str]:
    artist_text = clean(artist_text, "未提供")
    event_name = clean(event_name, "")

    if artist_text in ("未提供", "未知藝人"):
        return []

    # 無常見分隔符時，直接視為單一藝人，避免過度切分。
    split_hints = ["、", "，", ",", "/", "|", "＆", "&", " and ", " feat", " ft", " x "]
    if not any(hint in artist_text for hint in split_hints):
        return [artist_text] if artist_text != event_name else []

    parts = re.split(ARTIST_SPLIT_REGEX, artist_text)
    result = []
    for part in parts:
        name = clean(part, "")
        if not name:
            continue
        if name == event_name:
            continue
        if name in ("未提供", "未知藝人"):
            continue
        if len(name) == 1:
            continue
        if name not in result:
            result.append(name)

    if not result and artist_text not in (event_name, "未提供", "未知藝人"):
        result = [artist_text]

    return result


def recreate_tables(cur):
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("DROP TABLE IF EXISTS event_artists")
    cur.execute("DROP TABLE IF EXISTS artist_news")
    cur.execute("DROP TABLE IF EXISTS event_schedules")
    cur.execute("DROP TABLE IF EXISTS ticket_pricing")
    cur.execute("DROP TABLE IF EXISTS sales_channels")
    cur.execute("DROP TABLE IF EXISTS event_segments")
    cur.execute("DROP TABLE IF EXISTS artist_segments")
    cur.execute("DROP TABLE IF EXISTS events")
    cur.execute("DROP TABLE IF EXISTS artists")
    cur.execute("DROP TABLE IF EXISTS venues")

    cur.execute(
        """
        CREATE TABLE venues (
            venue_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            venue_name VARCHAR(255) NOT NULL,
            venue_address VARCHAR(255) NOT NULL,
            venue_intro TEXT NOT NULL,
            intro_source_url VARCHAR(500) DEFAULT NULL,
            intro_updated_at DATETIME DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_venue_name_addr (venue_name, venue_address)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute(
        """
        CREATE TABLE artists (
            artist_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            artist_name VARCHAR(255) NOT NULL,
            artist_intro TEXT NOT NULL,
            intro_source_url VARCHAR(500) DEFAULT NULL,
            intro_updated_at DATETIME DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_artist_name (artist_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute(
        """
        CREATE TABLE events (
            event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            venue_id BIGINT UNSIGNED DEFAULT NULL,
            `來源網站` TEXT,
            `活動名稱` TEXT,
            `藝人` TEXT,
            `搶票時間` TEXT,
            `活動時間` TEXT,
            `活動地點` TEXT,
            `活動地址` TEXT,
            `票價` TEXT,
            `票種` TEXT,
            `網址` TEXT,
            `爬取時間` TEXT,
            `資料來源檔` TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_events_venue
                FOREIGN KEY (venue_id) REFERENCES venues(venue_id)
                ON UPDATE CASCADE ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute("CREATE INDEX idx_events_source ON events(`來源網站`(64))")
    cur.execute("CREATE INDEX idx_events_time ON events(`活動時間`(64))")
    cur.execute("CREATE INDEX idx_events_url ON events(`網址`(128))")
    cur.execute("CREATE INDEX idx_events_venue_id ON events(venue_id)")

    cur.execute(
        """
        CREATE TABLE event_artists (
            event_id BIGINT UNSIGNED NOT NULL,
            artist_id BIGINT UNSIGNED NOT NULL,
            role_name VARCHAR(100) NOT NULL DEFAULT 'main',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (event_id, artist_id),
            CONSTRAINT fk_event_artists_event
                FOREIGN KEY (event_id) REFERENCES events(event_id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            CONSTRAINT fk_event_artists_artist
                FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
                ON UPDATE CASCADE ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute(
        """
        CREATE TABLE artist_news (
            news_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            artist_id BIGINT UNSIGNED NOT NULL,
            title VARCHAR(500) NOT NULL,
            summary TEXT,
            source_name VARCHAR(255),
            source_url VARCHAR(500) NOT NULL,
            published_at DATETIME DEFAULT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sentiment ENUM('positive', 'neutral', 'negative') DEFAULT 'neutral',
            CONSTRAINT fk_artist_news_artist
                FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            UNIQUE KEY uq_artist_news_source_url (source_url),
            INDEX idx_artist_news_artist_time (artist_id, published_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute("SET FOREIGN_KEY_CHECKS=1")


def get_or_create_venue(cur, venue_name: str, venue_address: str) -> int | None:
    if venue_name == "未提供" and venue_address == "未提供":
        return None

    cur.execute(
        """
        INSERT INTO venues (venue_name, venue_address, venue_intro)
        VALUES (%s, %s, '待補充')
        ON DUPLICATE KEY UPDATE venue_id = LAST_INSERT_ID(venue_id)
        """,
        (venue_name, venue_address),
    )
    cur.execute("SELECT LAST_INSERT_ID()")
    return cur.fetchone()[0]


def get_or_create_artist(cur, artist_name: str) -> int | None:
    artist_name = clean(artist_name, "未提供")
    if artist_name in ("未提供", "未知藝人"):
        return None

    cur.execute(
        """
        INSERT INTO artists (artist_name, artist_intro)
        VALUES (%s, '待補充')
        ON DUPLICATE KEY UPDATE artist_id = LAST_INSERT_ID(artist_id)
        """,
        (artist_name,),
    )
    cur.execute("SELECT LAST_INSERT_ID()")
    return cur.fetchone()[0]


def insert_event(cur, row: dict, venue_id: int | None) -> int:
    placeholders = ", ".join(["%s"] * (len(CANONICAL_COLUMNS) + 1))
    col_names = "venue_id, " + ", ".join(f"`{c}`" for c in CANONICAL_COLUMNS)
    insert_sql = f"INSERT INTO events ({col_names}) VALUES ({placeholders})"

    values = [venue_id] + [row[c] for c in CANONICAL_COLUMNS]
    cur.execute(insert_sql, values)
    return cur.lastrowid


def main():
    if not MERGED_JSON.exists():
        print(f"❌ 找不到合併 JSON: {MERGED_JSON}")
        return

    rows = json.loads(MERGED_JSON.read_text(encoding="utf-8"))
    normalized = [normalize_row(r) for r in rows]

    print(f"載入 {len(normalized)} 筆活動資料...")

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        recreate_tables(cur)

        event_count = 0
        event_artist_count = 0

        for row in normalized:
            venue_name = row["活動地點"]
            venue_addr = row["活動地址"]
            venue_id = get_or_create_venue(cur, venue_name, venue_addr)

            event_id = insert_event(cur, row, venue_id)
            event_count += 1

            artists = split_artists(row["藝人"], row["活動名稱"])
            for artist_name in artists:
                artist_id = get_or_create_artist(cur, artist_name)
                if not artist_id:
                    continue
                cur.execute(
                    """
                    INSERT IGNORE INTO event_artists (event_id, artist_id, role_name)
                    VALUES (%s, %s, 'main')
                    """,
                    (event_id, artist_id),
                )
                event_artist_count += 1

        conn.commit()

        cur.execute("SELECT COUNT(*) FROM events")
        total_events = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM venues")
        total_venues = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM artists")
        total_artists = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM event_artists")
        total_event_artists = cur.fetchone()[0]

        cur.execute(
            "SELECT `來源網站`, COUNT(*) FROM events GROUP BY `來源網站` ORDER BY COUNT(*) DESC"
        )
        source_stats = cur.fetchall()

        print("✅ 正規化資料表重建完成")
        print(f"  - events: {total_events} 筆")
        print(f"  - venues: {total_venues} 筆")
        print(f"  - artists: {total_artists} 筆")
        print(f"  - event_artists: {total_event_artists} 筆")
        print("  - artist_news: 0 筆（預留待新聞爬蟲寫入）")

        print("來源統計:")
        for source, count in source_stats:
            print(f"  - {source}: {count}")

        print("\n場地主檔樣本:")
        cur.execute(
            """
            SELECT venue_name, venue_address, venue_intro
            FROM venues
            ORDER BY venue_id
            LIMIT 3
            """
        )
        for name, address, intro in cur.fetchall():
            print(f"  - {name} | {address} | {intro[:20]}")

        print("\n藝人主檔樣本:")
        cur.execute(
            """
            SELECT artist_name, artist_intro
            FROM artists
            ORDER BY artist_id
            LIMIT 3
            """
        )
        for name, intro in cur.fetchall():
            print(f"  - {name} | {intro[:20]}")

        if event_count != total_events:
            print(f"⚠️ 寫入事件計數不一致：loop={event_count}, db={total_events}")
        if event_artist_count < total_event_artists:
            print(
                f"⚠️ 關聯計數異常：loop={event_artist_count}, db={total_event_artists}"
            )

    except Exception as exc:
        conn.rollback()
        print(f"❌ 匯入失敗：{exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
