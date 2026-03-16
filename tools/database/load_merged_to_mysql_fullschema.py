import json
from pathlib import Path

import mysql.connector


ROOT = Path(__file__).resolve().parents[2]
MERGED_JSON = ROOT / "爬蟲資料" / "整理後" / "concerts_merged.json"


FULL_COLUMNS = [
    "來源網站",
    "活動名稱",
    "藝人",
    "演出藝人",
    "搶票時間",
    "售票時間",
    "啟售日期",
    "啟售時間",
    "活動時間",
    "演出時間",
    "活動日期",
    "活動地點",
    "演出地點",
    "活動地址",
    "地址",
    "票價",
    "ticket_price",
    "票種",
    "ticket_types",
    "網址",
    "活動連結",
    "event_link",
    "場地名稱",
    "場地編號PK",
    "場地編號FK",
    "藝人編號PK",
    "藝人編號FK",
    "活動編號PK",
    "活動編號FK",
    "平台名稱",
    "平台編號PK",
    "爬取時間",
    "資料來源檔",
]


def clean(value, default="未提供"):
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() == "nan" or text == "未公布":
        return default
    return text


def normalize_row(row: dict) -> dict:
    artist = clean(row.get("藝人") or row.get("演出藝人") or row.get("活動名稱"), "未提供")
    event_time = clean(row.get("活動時間") or row.get("演出時間") or row.get("活動日期"), "未提供")
    venue = clean(row.get("活動地點") or row.get("演出地點") or row.get("場地名稱"), "未提供")
    address = clean(row.get("活動地址") or row.get("地址"), "未提供")
    url = clean(row.get("網址") or row.get("活動連結") or row.get("event_link"), "未提供")
    sale_time = clean(row.get("搶票時間") or row.get("售票時間"), "未提供")
    price = clean(row.get("票價") or row.get("ticket_price"), "未提供")
    ticket_types = clean(row.get("票種") or row.get("ticket_types"), "未提供")
# -*- coding: utf-8 -*-
"""
載入 concerts_merged.json 到 MySQL，使用乾淨的正規化欄位結構（去除所有冗餘欄位）。
欄位設計：來源網站、活動名稱、藝人、搶票時間、活動時間、活動地點、活動地址、票價、票種、網址、爬取時間、資料來源檔
"""
import json
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parents[2]
MERGED_JSON = ROOT / "爬蟲資料" / "整理後" / "concerts_merged.json"

# ── 正規欄位（語義不重複） ────────────────────────────────────────────────
CANONICAL_COLUMNS = [
    "來源網站",    # 售票平台名稱
    "活動名稱",    # 演唱會/活動標題
    "藝人",        # 演出者
    "搶票時間",    # 開賣/啟售時間
    "活動時間",    # 演出日期時間
    "活動地點",    # 場館名稱
    "活動地址",    # 場館地址
    "票價",        # 票價資訊
    "票種",        # 票券種類
    "網址",        # 活動頁面連結
    "爬取時間",    # 資料爬取時間
    "資料來源檔",  # 原始檔案名稱
]

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

FAKE_ADDRESSES = ["中清路一段447號", "台中市北區中清路"]


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
    return any(f in addr for f in FAKE_ADDRESSES)


def normalize_row(raw: dict) -> dict:
    source = clean(raw.get("來源網站") or raw.get("平台名稱"), "未提供")

    event_name = clean(
        raw.get("活動名稱") or raw.get("藝人") or raw.get("演出藝人"), "未提供"
    )

    artist = clean(raw.get("藝人") or raw.get("演出藝人"), "未提供")

    # 搶票時間：合併 啟售日期+啟售時間
    sale_date = clean(raw.get("啟售日期"), "")
    sale_clock = clean(raw.get("啟售時間"), "")
    if sale_date and sale_clock:
        sale_combined = f"{sale_date} {sale_clock}"
    else:
        sale_combined = sale_date or sale_clock or ""
    sale_time = clean(
        raw.get("搶票時間") or raw.get("售票時間") or sale_combined, "未提供"
    )
    # 若搶票時間 = 活動名稱（爬蟲 bug），設為未提供
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


def build_table(cur):
    cur.execute("DROP TABLE IF EXISTS events")
    cols_def = "\n".join(f"    `{c}` TEXT," for c in CANONICAL_COLUMNS)
    cur.execute(f"""
        CREATE TABLE events (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
{cols_def}
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    cur.execute("CREATE INDEX idx_source ON events(`來源網站`(64))")
    cur.execute("CREATE INDEX idx_event_time ON events(`活動時間`(64))")
    cur.execute("CREATE INDEX idx_url ON events(`網址`(128))")


def main():
    if not MERGED_JSON.exists():
        print(f"❌ 找不到合併 JSON: {MERGED_JSON}")
        return

    rows = json.loads(MERGED_JSON.read_text(encoding="utf-8"))
    print(f"載入 {len(rows)} 筆資料...")

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    build_table(cur)
    print("✅ events 資料表已重建（12 個正規欄位）")

    normalized = [normalize_row(r) for r in rows]

    placeholders = ", ".join(["%s"] * len(CANONICAL_COLUMNS))
    col_names = ", ".join(f"`{c}`" for c in CANONICAL_COLUMNS)
    insert_sql = f"INSERT INTO events ({col_names}) VALUES ({placeholders})"

    batch = [[r[c] for c in CANONICAL_COLUMNS] for r in normalized]
    cur.executemany(insert_sql, batch)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM events")
    total = cur.fetchone()[0]
    cur.execute("SELECT `來源網站`, COUNT(*) FROM events GROUP BY `來源網站` ORDER BY COUNT(*) DESC")
    stats = cur.fetchall()

    print(f"✅ MySQL events 更新完成，共 {total} 筆")
    print("來源統計:")
    for s, c in stats:
        print(f"  - {s}: {c}")

    # 驗證樣本
    print("\n=== 年代售票樣本（修正後）===")
    cur.execute("""
        SELECT `活動名稱`, `藝人`, `搶票時間`, `活動地址`
        FROM events WHERE `來源網站`='年代售票' LIMIT 3
    """)
    for r in cur.fetchall():
        print(f"  活動名稱: {r[0][:45]}")
        print(f"  搶票時間: {r[2][:45]}")
        print(f"  活動地址: {r[3][:45]}")
        print()

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
