#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export venues that still lack addresses to CSV for manual filling.
Outputs: exports/venues_missing_address_YYYYMMDD_HHMMSS.csv
Columns: venue_id, venue_name, current_address, events_count, sample_url
"""
from __future__ import annotations
import csv
import os
import time
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

OUT_DIR = 'exports'

QUERY = '''
SELECT v.venue_id, v.venue_name, v.venue_address,
  COUNT(e.event_id) AS events_count,
  (SELECT e2.`網址` FROM events e2 WHERE e2.venue_id=v.venue_id LIMIT 1) AS sample_url
FROM venues v
LEFT JOIN events e ON e.venue_id=v.venue_id
WHERE v.venue_address IS NULL OR TRIM(v.venue_address)='' OR v.venue_address IN ('未提供','未取得')
GROUP BY v.venue_id, v.venue_name, v.venue_address
ORDER BY events_count DESC
'''


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(QUERY)
    rows = cur.fetchall()
    ts = time.strftime('%Y%m%d_%H%M%S')
    os.makedirs(OUT_DIR, exist_ok=True)
    outpath = os.path.join(OUT_DIR, f'venues_missing_address_{ts}.csv')
    with open(outpath, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['venue_id','venue_name','venue_address','events_count','sample_url'])
        for r in rows:
            w.writerow([r[0], r[1], r[2] or '', r[3], r[4] or ''])
    cur.close()
    conn.close()
    print('Wrote', outpath)

if __name__ == '__main__':
    main()
