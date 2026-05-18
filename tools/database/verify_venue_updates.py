#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify venue updates by comparing a backup JSON to current DB rows.

Usage:
  python tools/database/verify_venue_updates.py backups/venues_backup_20260519_042303.json
"""

from __future__ import annotations

import json
import sys
from typing import Dict

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


def clean(s):
    if s is None:
        return ''
    return str(s).strip()


def main():
    if len(sys.argv) < 2:
        print('Usage: verify_venue_updates.py <backup.json>')
        sys.exit(1)
    backup_path = sys.argv[1]
    with open(backup_path, 'r', encoding='utf-8') as f:
        bak = json.load(f)

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)

    total = 0
    unchanged = 0
    changed = 0
    missing = 0
    samples = []

    for row in bak:
        total += 1
        vid = row.get('venue_id')
        old_addr = clean(row.get('venue_address'))
        cur.execute('SELECT venue_id, venue_name, venue_address FROM venues WHERE venue_id=%s', (vid,))
        currow = cur.fetchone()
        if not currow:
            missing += 1
            samples.append((vid, 'MISSING', old_addr, None))
            continue
        new_addr = clean(currow.get('venue_address'))
        if old_addr == new_addr:
            unchanged += 1
        else:
            changed += 1
            samples.append((vid, currow.get('venue_name'), old_addr, new_addr))

    cur.close()
    conn.close()

    print(f'驗證結果：總共備份筆數={total}, 未變更={unchanged}, 已變更={changed}, DB缺失={missing}')
    if samples:
        print('\n變更或樣本差異 (前 40):')
        for s in samples[:40]:
            vid, name, old, new = s
            print(f'venue_id={vid} name={name} -- old="{old}" --> new="{new}"')


if __name__ == "__main__":
    main()
