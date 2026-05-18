#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上傳最近兩天爬到的資料到遠端 DB：
- 先備份遠端 DB
- 刪除遠端 events 中「爬取時間」在最近兩天內的舊資料（並刪除相關子表資料）
- 從 `爬蟲資料/整理後/concerts_merged.json` 選出最近兩天的紀錄（以 `網址` 去重）並插入 `events`
- 執行 `remote_cleanup_and_fill.py` 補齊 sales_channels / venue_locations

小心：此步會刪除遠端在最近兩天內已存在的事件資料，請確認。
"""
import os
import json
import argparse
from datetime import datetime, timedelta
import subprocess
import mysql.connector
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JSON_PATH = ROOT / '爬蟲資料' / '整理後' / 'concerts_merged.json'
REMOTE_DUMP_SCRIPT = ROOT / 'tools' / 'database' / 'remote_dump.py'
REMOTE_CLEANUP_SCRIPT = ROOT / 'tools' / 'database' / 'remote_cleanup_and_fill.py'

DB_CONFIG = dict(
    host=os.getenv('DB_HOST', 'ticketdb-ticket63.f.aivencloud.com'),
    port=int(os.getenv('DB_PORT', '13599')),
    user=os.getenv('DB_USER', 'avnadmin'),
    password=os.getenv('DB_PASSWORD', 'AVNS_QqNVFqacdQinAgGmXY9'),
    database=os.getenv('DB_NAME', 'defaultdb'),
    charset='utf8mb4',
    autocommit=False,
)


def backup_remote():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = Path.cwd() / f'remote_preupload_backup_{ts}.sql'
    print('Backing up remote to', out)
    subprocess.run([os.sys.executable, str(REMOTE_DUMP_SCRIPT),
                    '--host', DB_CONFIG['host'], '--port', str(DB_CONFIG['port']),
                    '--user', DB_CONFIG['user'], '--password', DB_CONFIG['password'],
                    '--database', DB_CONFIG['database'], '--out', str(out)], check=True)
    return out


def load_recent_local(mode='yesterday'):
    if not JSON_PATH.exists():
        raise SystemExit(f'Local merged JSON not found: {JSON_PATH}')
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        records = json.load(f)

    today = datetime.now().date()
    if mode == 'today':
        target_date = today
    else:
        target_date = today - timedelta(days=1)

    recent = []
    for r in records:
        t = r.get('爬取時間')
        if not t:
            continue
        dt = None
        try:
            dt = datetime.fromisoformat(t)
        except Exception:
            try:
                dt = datetime.strptime(t, '%Y-%m-%d %H:%M:%S')
            except Exception:
                # skip unparsable
                continue
        if dt.date() == target_date:
            recent.append(r)

    # dedupe by URL
    seen = set()
    uniques = []
    for r in recent:
        url = r.get('網址') or ''
        if url in seen:
            continue
        seen.add(url)
        uniques.append(r)
    return uniques


def delete_existing(conn, urls=None):
    cur = conn.cursor()
    # find events whose last performance date < today
    # use event_schedules.performance_date aggregation
    cur.execute("""
    SELECT sch.event_id FROM (
      SELECT event_id, MAX(performance_date) AS lastp FROM event_schedules GROUP BY event_id
    ) sch WHERE sch.lastp < CURDATE()
    """)
    ids = [r[0] for r in cur.fetchall()]

    # also include by URL if provided
    if urls:
        q_urls = ','.join(['%s'] * len(urls))
        cur.execute(f"SELECT event_id FROM events WHERE 網址 IN ({q_urls})", tuple(urls))
        ids += [r[0] for r in cur.fetchall()]

    # unique
    ids = list(dict.fromkeys(ids))
    print('Found existing event_ids to remove (by last performance < today or url):', len(ids))
    if not ids:
        cur.close()
        return 0

    # delete child tables first
    child_tables = ['sales_channels', 'event_schedules', 'ticket_pricing', 'event_artists', 'event_segments']
    for t in child_tables:
        cur.execute(f"DELETE FROM `{t}` WHERE event_id IN ({','.join(['%s']*len(ids))})", tuple(ids))
    cur.execute(f"DELETE FROM events WHERE event_id IN ({','.join(['%s']*len(ids))})", tuple(ids))
    conn.commit()
    cur.close()
    return len(ids)


def drop_chinese_triggers(conn):
    cur = conn.cursor()
    mappings = {
        'events': '活動',
        'venue_locations': '活動地點',
        'sales_channels': '售票平台',
        'artists': '藝人',
        'users': '使用者',
    }
    for eng, chi in mappings.items():
        ins_name = f'tr_{eng}_ins_to_{chi}'
        upd_name = f'tr_{eng}_upd_to_{chi}'
        del_name = f'tr_{eng}_del_from_{chi}'
        for t in (ins_name, upd_name, del_name):
            try:
                cur.execute(f"DROP TRIGGER IF EXISTS `{t}`")
            except Exception:
                pass
    conn.commit()
    cur.close()


def insert_events(conn, records):
    cur = conn.cursor()
    inserted = 0
    for r in records:
        vals = (
            r.get('來源網站'), r.get('活動名稱'), r.get('藝人'), r.get('搶票時間'), r.get('活動時間'),
            r.get('活動地點'), r.get('活動地址'), r.get('票價'), r.get('票種'), r.get('網址'),
            r.get('爬取時間'), r.get('資料來源檔')
        )
        cur.execute(
            "INSERT INTO events (`來源網站`,`活動名稱`,`藝人`,`搶票時間`,`活動時間`,`活動地點`,`活動地址`,`票價`,`票種`,`網址`,`爬取時間`,`資料來源檔`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            vals,
        )
        inserted += cur.rowcount
    conn.commit()
    cur.close()
    return inserted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['today', 'yesterday'], default='yesterday', help='匯入 today 或 yesterday 的爬取資料')
    args = parser.parse_args()

    print('Step 1: backup remote')
    backup_remote()

    print(f'Step 2: load local records ({args.mode})')
    records = load_recent_local(mode=args.mode)
    print('Records to upload (deduped by URL):', len(records))
    urls = [r.get('網址') for r in records if r.get('網址')]

    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        # temporarily drop Chinese-sync triggers to avoid failures if target tables missing
        drop_chinese_triggers(conn)
        removed = delete_existing(conn, urls=None)
        print('Removed existing events matching last_performance < today:', removed)
        inserted = insert_events(conn, records)
        print('Inserted new events:', inserted)
    finally:
        conn.close()

    # run cleanup/fill to populate sales_channels/venue_locations; continue on failure
    print('Running remote cleanup and fill (best-effort)')
    try:
        subprocess.run([os.sys.executable, str(REMOTE_CLEANUP_SCRIPT)], check=True)
    except subprocess.CalledProcessError as e:
        print('remote_cleanup_and_fill.py failed:', e)

    # attempt to recreate Chinese triggers
    try:
        subprocess.run([os.sys.executable, str(ROOT / 'tools' / 'database' / 'create_chinese_triggers_remote.py')], check=True)
    except subprocess.CalledProcessError as e:
        print('create_chinese_triggers_remote.py failed:', e)


if __name__ == '__main__':
    main()
