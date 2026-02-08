import argparse
import glob
import json
import os
import sqlite3
from datetime import datetime
from typing import Iterable, List, Optional

DEFAULT_GLOBS = ["all_events_*.json", "演唱會資訊彙整_*.json"]


def normalize_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return str(value)


def iter_input_files(base_dir: str, patterns: Iterable[str]) -> List[str]:
    files: List[str] = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(base_dir, pattern)))
    return sorted(set(files))


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            artist TEXT,
            event_time TEXT,
            venue TEXT,
            price TEXT,
            url TEXT,
            scraped_at TEXT,
            source_file TEXT,
            raw_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_events_unique
        ON events (url, event_time, artist);
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_events_source
        ON events (source);
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            record_count INTEGER NOT NULL,
            inserted_count INTEGER NOT NULL,
            skipped_count INTEGER NOT NULL
        );
        """
    )


def parse_records(payload: object) -> List[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ["data", "records", "items"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def import_file(conn: sqlite3.Connection, file_path: str) -> None:
    with open(file_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    records = parse_records(payload)
    inserted = 0
    for item in records:
        source = normalize_value(item.get("來源網站"))
        artist = normalize_value(item.get("演出藝人"))
        event_time = normalize_value(item.get("演出時間"))
        venue = normalize_value(item.get("演出地點"))
        price = normalize_value(item.get("票價"))
        url = normalize_value(item.get("網址"))
        scraped_at = normalize_value(item.get("爬取時間"))
        raw_json = json.dumps(item, ensure_ascii=False)

        cur = conn.execute(
            """
            INSERT OR IGNORE INTO events (
                source, artist, event_time, venue, price, url, scraped_at, source_file, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                source,
                artist,
                event_time,
                venue,
                price,
                url,
                scraped_at,
                os.path.basename(file_path),
                raw_json,
            ),
        )
        if cur.rowcount:
            inserted += 1

    skipped = len(records) - inserted
    conn.execute(
        """
        INSERT INTO import_log (source_file, imported_at, record_count, inserted_count, skipped_count)
        VALUES (?, ?, ?, ?, ?);
        """,
        (
            os.path.basename(file_path),
            datetime.now().isoformat(timespec="seconds"),
            len(records),
            inserted,
            skipped,
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import concert JSON data into SQLite.")
    parser.add_argument(
        "--db",
        default=os.path.join("data", "concerts.db"),
        help="SQLite database path (default: data/concerts.db)",
    )
    parser.add_argument(
        "--input-glob",
        action="append",
        dest="input_globs",
        help="Input glob pattern (can be used multiple times)",
    )
    args = parser.parse_args()

    input_globs = args.input_globs or DEFAULT_GLOBS
    base_dir = os.getcwd()
    input_files = iter_input_files(base_dir, input_globs)

    if not input_files:
        raise SystemExit("找不到符合的 JSON 檔案。請確認輸入檔名或使用 --input-glob。")

    os.makedirs(os.path.dirname(args.db), exist_ok=True)

    conn = sqlite3.connect(args.db)
    try:
        ensure_schema(conn)
        for file_path in input_files:
            import_file(conn, file_path)
        conn.commit()
    finally:
        conn.close()

    print(f"已匯入 {len(input_files)} 個檔案至 {args.db}")


if __name__ == "__main__":
    main()
