#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Propagate canonical addresses from exports CSV to other venue rows that lack addresses.
Backs up affected rows before updating.
"""
from __future__ import annotations
import csv
import json
import datetime
import mysql.connector
import os

DB_CONFIG = dict(
    host='ticketdb-ticket63.f.aivencloud.com',
    port=13599,
    user='avnadmin',
    password='AVNS_QqNVFqacdQinAgGmXY9',
    database='defaultdb',
    charset='utf8mb4',
    autocommit=False,
)

CSV_PATH = 'exports/venue_dedup_20260519_033410.csv'
BACKUP_DIR = 'backups'

def load_csv(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def main():
    rows = load_csv(CSV_PATH)
    # map canonical_name -> address (if provided and not '未提供')
    canon_addr = {}
    for r in rows:
        cname = (r.get('canonical_name') or '').strip()
        addr = (r.get('venue_address') or r.get('venue_address_csv') or '').strip()
        if cname and addr and addr not in ('', '未提供', '未取得'):
            canon_addr[cname.lower()] = addr

    if not canon_addr:
        print('No canonical addresses found in CSV to apply.')
        return

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)

    timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'venues_canonical_addr_backup_{timestamp}.json')
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_rows = []

    total_updates = 0
    for cname, addr in canon_addr.items():
        like_pattern = f'%{cname}%'
        cur.execute("SELECT venue_id, venue_name, venue_address FROM venues WHERE LOWER(venue_name) LIKE %s AND (venue_address IS NULL OR venue_address='' OR venue_address='未提供' OR venue_address='未取得')", (like_pattern,))
        targets = cur.fetchall()
        if not targets:
            continue
        # backup
        for t in targets:
            backup_rows.append(t)
        # attempt update each; on uniqueness conflict, try merge
        for t in targets:
            try:
                cur.execute('UPDATE venues SET venue_address=%s, updated_at=NOW() WHERE venue_id=%s', (addr, t['venue_id']))
                total_updates += cur.rowcount
            except mysql.connector.IntegrityError:
                # find existing row that already has the desired name+addr
                cur.execute('SELECT venue_id FROM venues WHERE LOWER(venue_name)=LOWER(%s) AND venue_address=%s LIMIT 1', (t['venue_name'], addr))
                existing = cur.fetchone()
                existing_id = None
                if existing:
                    # cursor may return dict or tuple
                    if isinstance(existing, dict):
                        existing_id = existing.get('venue_id')
                    else:
                        existing_id = existing[0]
                if existing_id and existing_id != t['venue_id']:
                    # reassign events referencing old id to existing_id
                    try:
                        cur.execute('UPDATE events SET venue_id=%s WHERE venue_id=%s', (existing_id, t['venue_id']))
                        reassigned = cur.rowcount
                        # delete the old empty venue row
                        cur.execute('DELETE FROM venues WHERE venue_id=%s', (t['venue_id'],))
                        deleted = cur.rowcount
                        total_updates += (reassigned or 0) + (deleted or 0)
                    except Exception as e:
                        print('Failed to merge venue_id', t['venue_id'], 'into', existing_id, ':', e)
                else:
                    print('IntegrityError but no existing target found for', t['venue_id'])
        conn.commit()
        print(f'Applied canonical address for "{cname}" to {len(targets)} rows.')

    # write backup
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(backup_rows, f, ensure_ascii=False, indent=2, default=str)

    cur.close()
    conn.close()

    print('Total updates:', total_updates)
    print('Backup written to', backup_path)

if __name__ == '__main__':
    main()
