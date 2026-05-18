import argparse
import glob
import json
import os
from datetime import datetime
from typing import Iterable, List, Optional

import mysql.connector

DEFAULT_GLOBS = ["data/concerts.json"]


def iter_input_files(base_dir: str, patterns: Iterable[str]) -> List[str]:
    files: List[str] = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(base_dir, pattern)))
    return sorted(set(files))


def normalize_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return str(value)


def import_file(conn: mysql.connector.MySQLConnection, file_path: str) -> None:
    with open(file_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    records = payload if isinstance(payload, list) else []
    inserted = 0
    cur = conn.cursor()
    for item in records:
        source = normalize_value(item.get("來源網站"))
        artist = normalize_value(item.get("演出藝人") or item.get("藝人"))
        event_time = normalize_value(item.get("演出時間") or item.get("活動時間"))
        venue = normalize_value(item.get("演出地點") or item.get("活動地點"))
        price = normalize_value(item.get("票價"))
        url = normalize_value(item.get("網址"))
        scraped_at = normalize_value(item.get("爬取時間") or item.get("爬取時間"))
        source_file = os.path.basename(file_path)

        # Insert with columns matching existing schema
        try:
            cur.execute(
                """
                INSERT IGNORE INTO events (
                    `來源網站`, `活動名稱`, `藝人`, `搶票時間`, `活動時間`, `活動地點`, `活動地址`, `票價`, `票種`, `網址`, `爬取時間`, `資料來源檔`
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    source,
                    normalize_value(item.get('活動名稱') or item.get('title') or item.get('title')),
                    artist,
                    None,
                    event_time,
                    venue,
                    None,
                    price,
                    None,
                    url,
                    scraped_at,
                    source_file,
                ),
            )
        except Exception:
            # fallback: try minimal columns
            cur.execute(
                """
                INSERT IGNORE INTO events (`來源網站`,`藝人`,`活動時間`,`活動地點`,`票價`,`網址`,`爬取時間`,`資料來源檔`)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (source, artist, event_time, venue, price, url, scraped_at, source_file),
            )

        if cur.rowcount:
            inserted += 1

    conn.commit()
    cur.close()
    print(f"Inserted {inserted} records from {os.path.basename(file_path)}")


def connect_mysql(host: str, port: int, user: str, password: str, database: Optional[str]) -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        autocommit=False,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import concert JSON data into existing MySQL schema (localized columns).")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--db", required=True)
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

    conn = connect_mysql(args.host, args.port, args.user, args.password, args.db)
    try:
        for file_path in input_files:
            import_file(conn, file_path)
    finally:
        conn.close()

    print(f"已匯入 {len(input_files)} 個檔案至 MySQL 資料庫 {args.db}")


if __name__ == "__main__":
    main()
