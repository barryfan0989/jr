#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import venue addresses from a deduplicated CSV and upsert into `venues`.

Usage examples:
  python tools/database/import_venues_from_csv.py exports/venue_dedup_20260519_033410.csv --preview
  python tools/database/import_venues_from_csv.py exports/venue_dedup_20260519_033410.csv --backup --dry-run
  python tools/database/import_venues_from_csv.py exports/venue_dedup_20260519_033410.csv --backup --apply --batch 50
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from typing import Dict, List, Any

import mysql.connector

DB_CONFIG = dict(
    host='ticketdb-ticket63.f.aivencloud.com',
    port=13599,
    user='avnadmin',
    password='AVNS_QqNVFqacdQinAgGmXY9',
    database='defaultdb',
    charset='utf8mb4',
    autocommit=False,
)


def load_csv(path: str) -> List[Dict[str, str]]:
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append(r)
    return rows


def backup_rows(conn, rows_to_backup: List[Dict[str, Any]], outpath: str) -> None:
    def _safe(obj):
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if hasattr(v, 'isoformat'):
                    out[k] = v.isoformat()
                else:
                    try:
                        json.dumps(v)
                        out[k] = v
                    except Exception:
                        out[k] = str(v)
            return out
        return obj

    serializable = [_safe(r) for r in rows_to_backup]
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)


def fetch_existing_by_id(cur, vid: str):
    cur.execute('SELECT * FROM venues WHERE venue_id=%s', (vid,))
    return cur.fetchone()


def fetch_existing_by_name(cur, name: str):
    cur.execute('SELECT * FROM venues WHERE venue_name=%s', (name,))
    return cur.fetchone()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('csv', help='Path to dedup CSV')
    p.add_argument('--preview', action='store_true')
    p.add_argument('--backup', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--apply', action='store_true')
    p.add_argument('--batch', type=int, default=50)
    args = p.parse_args()

    rows = load_csv(args.csv)
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)

    updates = []
    backups = []
    ts = time.strftime('%Y%m%d_%H%M%S')

    for r in rows:
        canonical = (r.get('canonical_name') or '').strip()
        venue_id = (r.get('venue_id') or '').strip()
        addr = (r.get('venue_address') or '').strip()
        sample_url = (r.get('sample_url') or '').strip()
        if not addr:
            continue
        target = None
        existing = None
        if venue_id.isdigit():
            existing = fetch_existing_by_id(cur, venue_id)
            target = ('id', venue_id)
        if existing is None and canonical:
            existing = fetch_existing_by_name(cur, canonical)
            target = ('name', canonical)

        update_item = {
            'target': target,
            'venue_id_csv': venue_id,
            'canonical_name': canonical,
            'venue_address_csv': addr,
            'sample_url': sample_url,
            'existing_row': existing,
        }
        updates.append(update_item)
        if existing and args.backup:
            backups.append(existing)

    if args.backup and backups:
        bak_path = os.path.join('backups', f'venues_backup_{ts}.json')
        os.makedirs('backups', exist_ok=True)
        backup_rows(conn, backups, bak_path)
        print(f'備份 {len(backups)} 筆 venues 到 {bak_path}')

    # Preview output
    preview_path = os.path.join('exports', f'venue_upsert_preview_{ts}.jsonl')
    os.makedirs('exports', exist_ok=True)
    def safe_serialize(obj):
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if hasattr(v, 'isoformat'):
                    out[k] = v.isoformat()
                else:
                    try:
                        json.dumps(v)
                        out[k] = v
                    except Exception:
                        out[k] = str(v)
            return out
        return str(obj)

    with open(preview_path, 'w', encoding='utf-8') as fo:
        for u in updates:
            u_serial = dict(u)
            if u_serial.get('existing_row'):
                u_serial['existing_row'] = safe_serialize(u_serial['existing_row'])
            fo.write(json.dumps(u_serial, ensure_ascii=False) + '\n')

    print(f'準備對 {len(updates)} 筆候選進行 upsert（預覽已寫入 {preview_path}）')

    # show first 40 preview items
    for i, u in enumerate(updates[:40], start=1):
        tgt = u['target']
        tgt_desc = f'{tgt[0]}={tgt[1]}' if tgt else 'NO_TARGET'
        existing_addr = u['existing_row']['venue_address'] if u['existing_row'] and 'venue_address' in u['existing_row'] else None
        print(f'{i}. target={tgt_desc} | csv_addr={u["venue_address_csv"]!s} | existing_addr={existing_addr!s} | name={u["canonical_name"]!s}')

    if args.preview and not args.apply:
        cur.close()
        conn.close()
        return

    if not args.apply:
        print('未啟用 --apply，作業停止於 preview/dry-run。')
        cur.close()
        conn.close()
        return

    # Apply updates in batches
    applied = 0
    for i in range(0, len(updates), args.batch):
        batch = updates[i:i + args.batch]
        for u in batch:
            tgt = u['target']
            addr = u['venue_address_csv']
            name = u['canonical_name'] or None
            if tgt is None:
                # insert new venue
                cur.execute('INSERT INTO venues (venue_name, venue_address) VALUES (%s, %s)', (name, addr))
                applied += 1
            else:
                if tgt[0] == 'id':
                    cur.execute('UPDATE venues SET venue_address=%s, venue_name=COALESCE(%s, venue_name) WHERE venue_id=%s', (addr, name, tgt[1]))
                    applied += cur.rowcount
                else:
                    cur.execute('UPDATE venues SET venue_address=%s, venue_name=COALESCE(%s, venue_name) WHERE venue_name=%s', (addr, name, tgt[1]))
                    applied += cur.rowcount
        conn.commit()
        print(f'已套用 batch {i//args.batch + 1}, 總計套用: {applied}')

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
