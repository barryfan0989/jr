#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""建立缺少的場地檔並用 OpenStreetMap Nominatim 補地址。

用途：針對 `events.活動地點` 中常見但 `venues` 表不存在或 `venue_address` 缺值的場地，
用 Nominatim 搜尋（加上 Taiwan 範圍提示）取得建議地址，並建立或更新 `venues`。

注意：Nominatim 有流量限制，請在大量執行時小心節流。
"""

from __future__ import annotations

import argparse
import json
import re
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import mysql.connector
import requests

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

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
HTTP_HEADERS = {'User-Agent': 'jr-backfill-agent/1.0 (+https://example.invalid)'}


def find_missing_venue_names(cur, limit: int = 0) -> List[Tuple[str, int]]:
    q = """
    SELECT LOWER(TRIM(e.`活動地點`)) as venue_name, COUNT(*) as c
    FROM events e
    LEFT JOIN venues v ON LOWER(TRIM(v.venue_name)) = LOWER(TRIM(e.`活動地點`))
    WHERE e.`活動地點` IS NOT NULL AND TRIM(e.`活動地點`)<>'') AND (v.venue_id IS NULL OR v.venue_address IS NULL OR TRIM(v.venue_address)='')
    GROUP BY LOWER(TRIM(e.`活動地點`))
    ORDER BY c DESC
    """
    # Some MySQL servers may not accept the above complex WHERE; fallback to simpler query
    try:
        if limit:
            q2 = ("SELECT t.venue_name, t.c FROM (SELECT LOWER(TRIM(e.`活動地點`)) as venue_name, COUNT(*) as c "
                  "FROM events e GROUP BY LOWER(TRIM(e.`活動地點`))) t "
                  "LEFT JOIN venues v ON LOWER(TRIM(v.venue_name))=t.venue_name "
                  "WHERE (v.venue_id IS NULL OR v.venue_address IS NULL OR TRIM(v.venue_address)='') "
                  "ORDER BY t.c DESC LIMIT %s")
            cur.execute(q2, (limit,))
        else:
            q2 = ("SELECT t.venue_name, t.c FROM (SELECT LOWER(TRIM(e.`活動地點`)) as venue_name, COUNT(*) as c "
                  "FROM events e GROUP BY LOWER(TRIM(e.`活動地點`))) t "
                  "LEFT JOIN venues v ON LOWER(TRIM(v.venue_name))=t.venue_name "
                  "WHERE (v.venue_id IS NULL OR v.venue_address IS NULL OR TRIM(v.venue_address)='') "
                  "ORDER BY t.c DESC")
            cur.execute(q2)
        rows = cur.fetchall()
        return [(r[0], int(r[1])) for r in rows if r[0] and r[0].strip()]
    except Exception:
        # fallback simpler: distinct names from events not in venues
        cur.execute("SELECT DISTINCT LOWER(TRIM(e.`活動地點`)) FROM events e")
        names = [r[0] for r in cur.fetchall() if r[0]]
        out = []
        for n in names:
            cur.execute("SELECT venue_id, venue_address FROM venues WHERE LOWER(TRIM(venue_name))=%s", (n,))
            r = cur.fetchone()
            if not r or not r[1] or not r[1].strip():
                out.append((n, 0))
                if limit and len(out) >= limit:
                    break
        return out


def nominatim_search(name: str) -> dict:
    params = {'q': f'{name} Taiwan', 'format': 'json', 'limit': 1, 'addressdetails': 1}
    try:
        r = requests.get(NOMINATIM_URL, params=params, headers=HTTP_HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                return data[0]
    except Exception:
        return {}
    return {}


def create_venue(cur, name: str, address: str) -> int:
    try:
        cur.execute("INSERT INTO venues (venue_name, venue_address, venue_intro, created_at) VALUES (%s, %s, %s, NOW())", (name, address, ''))
        return cur.lastrowid
    except mysql.connector.IntegrityError as e:
        print(f'  skip create duplicate or integrity error: {e}')
        return 0
    except Exception as e:
        print(f'  error creating venue: {e}')
        return 0


def update_venue_address(cur, name: str, address: str) -> int:
    cur.execute("UPDATE venues SET venue_address=%s WHERE LOWER(TRIM(venue_name))=LOWER(TRIM(%s))", (address, name))
    return cur.rowcount


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--preview', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--limit', type=int, default=50)
    p.add_argument('--sleep', type=float, default=1.0, help='seconds between Nominatim requests')
    args = p.parse_args()

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        candidates = find_missing_venue_names(cur, args.limit)
        def normalize_name(n: str) -> str:
            if not n:
                return ''
            s = str(n)
            # remove parenthesis content
            s = re.sub(r"\(.*?\)|\[.*?\]|\{.*?\}", '', s)
            # cut off at common keywords (票價/地址/啟售/預售)
            s = re.split(r'票價|活動地址|地址|啟售|預售|購票|票務|票價：', s, flags=re.I)[0]
            # remove extra punctuation and long numeric tails
            s = re.sub(r'\s+[-–—:].*$', '', s)
            s = re.sub(r'[^\w\u4e00-\u9fff\s\-]', ' ', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return s
        print('candidates=', len(candidates))
        processed = 0
        created = 0
        updated = 0
        for name, cnt in candidates:
            if not name or name.strip() == '':
                continue
            processed += 1
            raw = name
            name = normalize_name(raw)
            if not name:
                print('skip empty after normalize:', raw)
                continue
            print('checking:', name, 'events=', cnt)
            res = nominatim_search(name)
            if not res:
                print('  no nominatim result')
                continue
            display = res.get('display_name', '')
            addr = ''
            ad = res.get('address', {})
            if ad:
                parts = []
                for k in ('road', 'house_number', 'suburb', 'city_district', 'city', 'county', 'state', 'postcode'):
                    v = ad.get(k)
                    if v:
                        parts.append(v)
                if 'country' in ad and ad.get('country') and 'Taiwan' not in ad.get('country'):
                    parts.append(ad.get('country'))
                addr = ' '.join(parts).strip() or display
            else:
                addr = display

            if not addr:
                print('  no address parsed')
                continue

            if args.preview or args.dry_run:
                print(f' PREVIEW create/update: "{name}" -> "{addr}"')
            else:
                # check exists
                cur.execute("SELECT venue_id, venue_address FROM venues WHERE LOWER(TRIM(venue_name))=%s", (name,))
                r = cur.fetchone()
                if not r:
                    vid = create_venue(cur, name, addr)
                    created += 1
                    print('  created venue_id=', vid)
                else:
                    if not r[1] or not str(r[1]).strip():
                        updated += update_venue_address(cur, name, addr)
                        print('  updated existing venue')
                if processed % 20 == 0:
                    conn.commit()
            time.sleep(args.sleep)

        if not (args.preview or args.dry_run):
            conn.commit()
        print('done processed=', processed, 'created=', created, 'updated=', updated)

    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
