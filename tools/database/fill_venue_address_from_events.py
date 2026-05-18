#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""從 events 的 `活動地址` 補回 venues 的 `venue_address`（整理版）

工作流程：
- 找出 `venues` 中 address 缺值或為空的場地（依 venue_name）
- 從 `events` 中以 `活動地點` 對應 `venue_name`，挑出最常見的 `活動地址` 作為填值來源
- 先備份這些 `venues` 行到 JSON，支援 --preview / --dry-run
- 支援 --limit 控制最多更新幾個場地，並每 50 筆 commit

注意：本腳本使用 `venues.venue_name` 與 `events.活動地點` 做文字比對，若你的資料使用 id 關聯（venue_id），應改為以 id 更新。
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import mysql.connector

ROOT = Path(__file__).resolve().parents[2]

DB_CONFIG = dict(
    host=os.getenv('DB_HOST', 'ticketdb-ticket63.f.aivencloud.com'),
    port=int(os.getenv('DB_PORT', '13599')),
    user=os.getenv('DB_USER', 'avnadmin'),
    password=os.getenv('DB_PASSWORD', 'AVNS_QqNVFqacdQinAgGmXY9'),
    database=os.getenv('DB_NAME', 'defaultdb'),
    charset='utf8mb4',
    autocommit=False,
)


def quote(s: str) -> str:
    return (s or '').strip()


def find_candidate_venues(cur, limit: int = 0) -> List[Tuple[str, int, str]]:
    # Find venues with missing address and at least one event that has 活動地址
    q = """
    SELECT v.venue_name, COUNT(*) as event_count
    FROM venues v
    JOIN events e ON LOWER(TRIM(e.`活動地點`)) = LOWER(TRIM(v.venue_name))
    WHERE (v.venue_address IS NULL OR TRIM(v.venue_address) = '' OR v.venue_address IN ('未提供','未取得'))
      AND e.`活動地址` IS NOT NULL AND TRIM(e.`活動地址`)<>''
    GROUP BY v.venue_name
    ORDER BY event_count DESC
    """
    if limit:
        q += f" LIMIT {int(limit)}"
    cur.execute(q)
    return [(r[0], int(r[1])) for r in cur.fetchall()]


def pick_most_common_address_for_venue(cur, venue_name: str) -> str:
    cur.execute(
        """
        SELECT e.`活動地址`, COUNT(*) as c
        FROM events e
        WHERE LOWER(TRIM(e.`活動地點`)) = LOWER(TRIM(%s)) AND e.`活動地址` IS NOT NULL AND TRIM(e.`活動地址`)<>''
        GROUP BY e.`活動地址`
        ORDER BY c DESC
        LIMIT 1
        """,
        (venue_name,),
    )
    r = cur.fetchone()
    if not r:
        return ''
    addr = (r[0] or '').strip()
    if addr in ('未提供', '未取得', '未公布', ''):
        return ''
    return addr


def backup_venues(cur, venue_names: List[str], out_dir: Path) -> Path:
    if not venue_names:
        return None
    placeholder = ','.join(['%s'] * len(venue_names))
    q = f"SELECT * FROM venues WHERE venue_name IN ({placeholder})"
    cur.execute(q, tuple(venue_names))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    data = []
    for r in rows:
        rec = {}
        for k, v in zip(cols, r):
            if v is None:
                rec[k] = None
            else:
                try:
                    # Attempt JSON-friendly conversion
                    if hasattr(v, 'isoformat'):
                        rec[k] = v.isoformat()
                    else:
                        rec[k] = str(v)
                except Exception:
                    rec[k] = str(v)
        data.append(rec)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f'venues_address_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with path.open('w', encoding='utf8') as f:
        json.dump({'cols': cols, 'rows': data}, f, ensure_ascii=False, indent=2)
    return path


def update_venue_address(cur, venue_name: str, address: str) -> int:
    try:
        cur.execute("UPDATE venues SET venue_address=%s WHERE LOWER(TRIM(venue_name))=LOWER(TRIM(%s))", (address, venue_name))
        return cur.rowcount
    except mysql.connector.IntegrityError as e:
        print(f'SKIP duplicate venue/address for "{venue_name}" -> "{address}" : {e}')
        return 0
    except Exception as e:
        print(f'ERROR updating venue "{venue_name}": {e}')
        return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--preview', action='store_true', help='print proposed updates')
    p.add_argument('--dry-run', action='store_true', help='no changes')
    p.add_argument('--limit', type=int, default=0)
    p.add_argument('--commit-batch', type=int, default=50)
    args = p.parse_args()

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        candidates = find_candidate_venues(cur, args.limit)
        print('candidate_venues=', len(candidates))
        if not candidates:
            return

        venue_names = [v for v, _ in candidates]
        backup_path = backup_venues(cur, venue_names, Path('.'))
        if backup_path:
            print('backup saved to', backup_path)

        proposed = []
        for venue_name, cnt in candidates:
            addr = pick_most_common_address_for_venue(cur, venue_name)
            if addr:
                proposed.append((venue_name, addr, cnt))

        if args.preview or args.dry_run:
            for v, a, c in proposed:
                print(f'PREVIEW venue="{v}" events={c} propose_address="{a}"')
            return

        updated = 0
        batch = 0
        for v, a, c in proposed:
            updated += update_venue_address(cur, v, a)
            batch += 1
            if batch >= args.commit_batch:
                conn.commit()
                batch = 0
        conn.commit()
        print('updated count=', updated)

    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
