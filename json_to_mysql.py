import argparse
import glob
import json
import os
from datetime import datetime
from typing import Iterable, List, Optional

import mysql.connector

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


def ensure_schema(conn: mysql.connector.MySQLConnection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            source TEXT,
            artist TEXT,
            event_time TEXT,
            venue TEXT,
            price TEXT,
            url TEXT,
            scraped_at TEXT,
            source_file TEXT,
            raw_json JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY idx_events_unique (url(191), event_time(191), artist(191)),
            KEY idx_events_source (source(191))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS import_log (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            source_file TEXT NOT NULL,
            imported_at DATETIME NOT NULL,
            record_count INT NOT NULL,
            inserted_count INT NOT NULL,
            skipped_count INT NOT NULL,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    cur.close()


def parse_records(payload: object) -> List[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ["data", "records", "items"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def import_file(conn: mysql.connector.MySQLConnection, file_path: str) -> None:
    with open(file_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    records = parse_records(payload)
    inserted = 0
    cur = conn.cursor()
    for item in records:
        source = normalize_value(item.get("來源網站"))
        artist = normalize_value(item.get("演出藝人"))
        event_time = normalize_value(item.get("演出時間"))
        venue = normalize_value(item.get("演出地點"))
        price = normalize_value(item.get("票價"))
        url = normalize_value(item.get("網址"))
        scraped_at = normalize_value(item.get("爬取時間"))
        raw_json = json.dumps(item, ensure_ascii=False)

        cur.execute(
            """
            INSERT IGNORE INTO events (
                source, artist, event_time, venue, price, url, scraped_at, source_file, raw_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
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
    cur.execute(
        """
        INSERT INTO import_log (source_file, imported_at, record_count, inserted_count, skipped_count)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (
            os.path.basename(file_path),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            len(records),
            inserted,
            skipped,
        ),
    )
    cur.close()


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
    parser = argparse.ArgumentParser(description="Import concert JSON data into MySQL.")
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "root"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD", ""))
    parser.add_argument("--db", default=os.getenv("MYSQL_DB", "concerts"))
    parser.add_argument("--create-db", action="store_true", help="Create database if it does not exist.")
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

    if args.create_db:
        admin_conn = connect_mysql(args.host, args.port, args.user, args.password, None)
        try:
            cur = admin_conn.cursor()
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{args.db}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            admin_conn.commit()
            cur.close()
        finally:
            admin_conn.close()

    conn = connect_mysql(args.host, args.port, args.user, args.password, args.db)
    try:
        ensure_schema(conn)
        for file_path in input_files:
            import_file(conn, file_path)
        conn.commit()
    finally:
        conn.close()

    print(f"已匯入 {len(input_files)} 個檔案至 MySQL 資料庫 {args.db}")


if __name__ == "__main__":
    main()
