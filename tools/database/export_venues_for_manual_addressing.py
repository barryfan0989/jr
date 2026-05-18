#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""匯出去重後的場館清單供人工補地址。

輸出欄位：canonical_name, events_count, venue_id, venue_address, sample_url

用法：python tools/database/export_venues_for_manual_addressing.py
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path

import mysql.connector

DB_CONFIG = dict(
    host=os.getenv('DB_HOST', 'ticketdb-ticket63.f.aivencloud.com'),
    port=int(os.getenv('DB_PORT', '13599')),
    user=os.getenv('DB_USER', 'avnadmin'),
    password=os.getenv('DB_PASSWORD', 'AVNS_QqNVFqacdQinAgGmXY9'),
    database=os.getenv('DB_NAME', 'defaultdb'),
    charset='utf8mb4',
    autocommit=False,
)

OUT_DIR = Path('exports')


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    q = '''
    SELECT name, events_count,
      (SELECT venue_id FROM venues v WHERE LOWER(TRIM(v.venue_name))=name LIMIT 1) AS venue_id,
      (SELECT venue_address FROM venues v WHERE LOWER(TRIM(v.venue_name))=name LIMIT 1) AS venue_address,
      (SELECT MIN(e2.`網址`) FROM events e2 WHERE LOWER(TRIM(e2.`活動地點`))=name) AS sample_url
    FROM (
      SELECT LOWER(TRIM(`活動地點`)) AS name, COUNT(*) AS events_count
      FROM events
      WHERE `活動地點` IS NOT NULL AND TRIM(`活動地點`)<>''
      GROUP BY LOWER(TRIM(`活動地點`))
    ) t
    ORDER BY events_count DESC
    '''
    cur.execute(q)
    rows = cur.fetchall()
    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / f'venue_dedup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    with out_path.open('w', encoding='utf8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['canonical_name', 'events_count', 'venue_id', 'venue_address', 'sample_url'])
        for name, cnt, vid, vaddr, url in rows:
            w.writerow([name or '', cnt or 0, vid or '', vaddr or '', url or ''])
    cur.close()
    conn.close()
    print('exported', len(rows), 'rows to', out_path)


if __name__ == '__main__':
    main()
