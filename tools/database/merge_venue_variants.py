#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge venue variants by pattern: pick an existing venue with address as target,
reassign events referencing other variant rows to the target, then delete the old rows.
Usage: python merge_venue_variants.py "台北小巨蛋"
"""
from __future__ import annotations
import sys
import json
import os
import mysql.connector
from datetime import datetime

DB_CONFIG = dict(
    host='ticketdb-ticket63.f.aivencloud.com',
    port=13599,
    user='avnadmin',
    password='AVNS_QqNVFqacdQinAgGmXY9',
    database='defaultdb',
    charset='utf8mb4',
    autocommit=False,
)

PATTERN = sys.argv[1] if len(sys.argv) > 1 else '台北小巨蛋'
BACKUP_DIR = 'backups'

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)
    like = f"%{PATTERN}%"
    cur.execute('SELECT venue_id, venue_name, venue_address FROM venues WHERE LOWER(venue_name) LIKE LOWER(%s)', (like,))
    rows = cur.fetchall()
    if not rows:
        print('no rows')
        return
    print('found', len(rows), 'rows')
    # choose target with non-empty address
    target = None
    for r in rows:
        addr = (r.get('venue_address') or '').strip()
        if addr and addr not in ('未提供','未取得',''):
            target = r
            break
    if not target:
        print('no target with address found for pattern', PATTERN)
        return
    target_id = target['venue_id']
    print('target chosen:', target_id, target['venue_name'], target['venue_address'])
    # identify source rows to merge (missing address and id != target_id)
    sources = [r for r in rows if (not r.get('venue_address') or r.get('venue_address') in ('未提供','未取得','')) and r['venue_id'] != target_id]
    print('sources to merge:', [ (s['venue_id'], s['venue_name']) for s in sources ])
    # backup events referencing source ids and source venues
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    backup = {'pattern': PATTERN, 'target': target, 'sources': sources, 'events': []}
    for s in sources:
        cur.execute('SELECT * FROM events WHERE venue_id=%s', (s['venue_id'],))
        evs = cur.fetchall()
        backup['events'].append({'venue_id': s['venue_id'], 'events': evs})
    bp = os.path.join(BACKUP_DIR, f'venue_merge_backup_{PATTERN}_{ts}.json')
    with open(bp, 'w', encoding='utf-8') as f:
        json.dump(backup, f, ensure_ascii=False, default=str)
    print('backup written to', bp)
    # perform reassignment and delete
    total_reassigned = 0
    total_deleted = 0
    for s in sources:
        try:
            cur.execute('UPDATE events SET venue_id=%s WHERE venue_id=%s', (target_id, s['venue_id']))
            total_reassigned += cur.rowcount
            cur.execute('DELETE FROM venues WHERE venue_id=%s', (s['venue_id'],))
            total_deleted += cur.rowcount
            conn.commit()
            print('merged', s['venue_id'], '->', target_id)
        except Exception as e:
            conn.rollback()
            print('failed to merge', s['venue_id'], e)
    print('total reassigned events:', total_reassigned, 'total deleted venues:', total_deleted)
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
