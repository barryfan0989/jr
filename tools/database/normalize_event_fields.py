#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize and split event free-text fields into structured components.

This script previews structured parsing for key free-text columns.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple

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


def clean(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or '').strip())


def parse_dates(text: str) -> Dict[str, str]:
    out = {}
    if not text:
        return out
    # YYYY-MM-DD or YYYY/MM/DD with optional time HH:MM
    m = re.search(r'(20\d{2})[\/-](\d{1,2})[\/-](\d{1,2})(?:[ T]*(\d{1,2}:\d{2}))?', text)
    if m:
        y, mo, d, t = m.groups()
        date = f'{int(y):04d}-{int(mo):02d}-{int(d):02d}'
        if t:
            out['start_datetime'] = f'{date} {t}'
        else:
            out['start_date'] = date
        return out
    # fallback: day month year (basic)
    m2 = re.search(r'(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})', text)
    if m2:
        d, mon, y = m2.groups()
        out['start_date'] = f'{y}-{int(1):02d}-{int(d):02d}'
        return out
    return out


def parse_sale_time(text: str) -> Dict[str, str]:
    out = {}
    if not text:
        return out
    m = re.search(r'(20\d{2}[\/-]\d{1,2}[\/-]\d{1,2})(?:[ T]*(\d{1,2}:\d{2}))?', text)
    if m:
        date, t = m.groups()
        if t:
            out['sale_start'] = f'{date} {t}'
        else:
            out['sale_start_date'] = date
    return out


def parse_prices(text: str) -> List[str]:
    if not text:
        return []
    prices = []
    # NT$ patterns
    for m in re.findall(r'NT\$\s*\d{2,5}(?:[-~～]\s*NT\$?\s*\d{2,5})?', text, re.I):
        prices.append(clean(m))
    # simple numeric tiers
    for m in re.findall(r'([A-Za-z\u4e00-\u9fff\s]{1,20})[:：\s]+(\d{2,5})', text):
        name, amt = m
        prices.append(f'{clean(name)} {amt}')
    # dedupe
    seen = []
    for p in prices:
        if p not in seen:
            seen.append(p)
    return seen


def split_venue_address(raw_place: str, raw_address: str) -> Tuple[str, str]:
    if raw_address and raw_address.strip() and raw_address.strip() not in ('未提供', '未取得'):
        return clean(raw_place), clean(raw_address)
    if not raw_place:
        return '', clean(raw_address or '')
    # parenthesis address
    m = re.search(r'\(([^\)]+\d{2,4}[^\)]*)\)', raw_place)
    if m:
        addr = m.group(1).strip()
        name = re.sub(r'\([^\)]*\)', '', raw_place).strip()
        return clean(name), clean(addr)
    # basic taiwan address regex
    m2 = re.search(r'((?:台|臺)[^\n，。]{0,60}(?:市|縣)[^\n，。]{0,80}(?:路|街|大道|巷|弄|段)[^\n，。]{0,60}號?)', raw_place)
    if m2:
        addr = m2.group(1).strip()
        name = raw_place.replace(addr, '').strip(' -:()[]')
        return clean(name), clean(addr)
    return clean(raw_place), clean(raw_address or '')


def split_artists(text: str) -> List[str]:
    if not text:
        return []
    parts = re.split(r'[,/、;；\n\r]| and | & | vs | vs\.|\band\b', text)
    out = []
    for p in parts:
        p = re.sub(r'[-–—:：].*$', '', p)
        p = clean(p)
        if p and p not in ('未提供', '未取得') and p not in out:
            out.append(p)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--preview', action='store_true')
    p.add_argument('--limit', type=int, default=50)
    args = p.parse_args()

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute('SELECT event_id, `來源網站`, `活動名稱`, `藝人`, `搶票時間`, `活動時間`, `活動地點`, `活動地址`, `票價`, `網址` FROM events ORDER BY event_id')
    rows = cur.fetchall()
    processed = 0
    for row in rows:
        event_id, site, title, artist, sale_time, event_time, place, address, price, url = row
        if args.limit and processed >= args.limit:
            break
        processed += 1
        parsed = {
            'event_id': event_id,
            'site': site,
            'title': clean(title),
            'artists': split_artists(artist),
            'sale': parse_sale_time(sale_time or ''),
            'event': parse_dates(event_time or ''),
            'prices': parse_prices(price or ''),
            'url': url,
        }
        vn, va = split_venue_address(place or '', address or '')
        parsed['venue_name'] = vn
        parsed['venue_address'] = va
        if args.preview:
            print(json.dumps(parsed, ensure_ascii=False))
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
