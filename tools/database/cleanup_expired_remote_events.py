#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理遠端資料庫中已過期的活動資料。

判斷方式：以 events.活動時間 的日期為準，只要活動日期早於今天就視為過期。
會先備份遠端資料庫，再刪除 events 與其相關子表資料。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

import mysql.connector


ROOT = Path(__file__).resolve().parents[2]
REMOTE_DUMP_SCRIPT = ROOT / 'tools' / 'database' / 'remote_dump.py'

DB_CONFIG = dict(
    host=os.getenv('DB_HOST', 'ticketdb-ticket63.f.aivencloud.com'),
    port=int(os.getenv('DB_PORT', '13599')),
    user=os.getenv('DB_USER', 'avnadmin'),
    password=os.getenv('DB_PASSWORD', 'AVNS_QqNVFqacdQinAgGmXY9'),
    database=os.getenv('DB_NAME', 'defaultdb'),
    charset='utf8mb4',
    autocommit=False,
)


def backup_remote() -> Path:
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = Path.cwd() / f'remote_expired_cleanup_backup_{ts}.sql'
    print('Backing up remote to', out)
    subprocess.run(
        [
            os.sys.executable,
            str(REMOTE_DUMP_SCRIPT),
            '--host', DB_CONFIG['host'],
            '--port', str(DB_CONFIG['port']),
            '--user', DB_CONFIG['user'],
            '--password', DB_CONFIG['password'],
            '--database', DB_CONFIG['database'],
            '--out', str(out),
        ],
        check=True,
    )
    return out


def parse_activity_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    if not text or text == '未提供':
        return None

    match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', text)
    if not match:
        return None

    year, month, day = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def fetch_expired_event_ids(cur) -> list[int]:
    cur.execute('SELECT event_id, `活動時間` FROM events')
    today = date.today()
    expired_ids: list[int] = []
    for event_id, raw_time in cur.fetchall():
        activity_date = parse_activity_date(raw_time)
        if activity_date and activity_date < today:
            expired_ids.append(int(event_id))
    return expired_ids


def delete_expired_events(conn, event_ids: list[int]) -> int:
    if not event_ids:
        return 0

    cur = conn.cursor()
    try:
        child_tables = ['sales_channels', 'event_schedules', 'ticket_pricing', 'event_artists', 'event_segments']
        for table_name in child_tables:
            for start in range(0, len(event_ids), 200):
                chunk = event_ids[start:start + 200]
                placeholders = ','.join(['%s'] * len(chunk))
                cur.execute(f'DELETE FROM `{table_name}` WHERE event_id IN ({placeholders})', tuple(chunk))

        deleted = 0
        for start in range(0, len(event_ids), 200):
            chunk = event_ids[start:start + 200]
            placeholders = ','.join(['%s'] * len(chunk))
            cur.execute(f'DELETE FROM events WHERE event_id IN ({placeholders})', tuple(chunk))
            deleted += cur.rowcount

        conn.commit()
        return deleted
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='只顯示將被刪除的筆數，不實際刪除')
    args = parser.parse_args()

    print('Step 1: backup remote')
    backup_remote()

    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        try:
            expired_ids = fetch_expired_event_ids(cur)
        finally:
            cur.close()

        print('Expired events found:', len(expired_ids))
        if expired_ids:
            print('Sample expired event_ids:', expired_ids[:10])

        if args.dry_run:
            print('Dry run only; no rows deleted.')
            return

        deleted = delete_expired_events(conn, expired_ids)
        print('Deleted expired events:', deleted)
    finally:
        conn.close()


if __name__ == '__main__':
    main()