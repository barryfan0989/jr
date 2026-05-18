#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan `events`.`藝人` values and propose canonical artist names (preview).

Usage: python tools/database/standardize_artists.py --preview --limit 50
"""

from __future__ import annotations

import argparse
import json
import re
from typing import List

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


def canonicalize_artist(text: str) -> str:
    if not text:
        return ''
    s = text.strip()
    # remove HTML tags
    s = re.sub(r'<[^>]+>', '', s)
    # remove bracketed annotations
    s = re.sub(r'[\(\[（【].*?[\)\]\）】]', '', s)
    # remove common noise words
    s = re.sub(r'個人演唱會|演唱會|購票|售票|票價|購票連結|購票｜|購票：|票｜|啟售|購票資訊|延期|delay|取消', '', s, flags=re.I)
    # split on separators
    parts = re.split(r'[,/、／;；\n\r\|\\-–—]', s)
    parts = [p.strip() for p in parts if p and p.strip()]
    # prefer a Chinese name (2-4 chars)
    chinese_re = re.compile(r'([\u4e00-\u9fff]{2,4})')
    for p in parts:
        m = chinese_re.search(p)
        if m:
            return m.group(1)
    # fallback: if whole string has Chinese substring longer than 1
    m2 = re.search(r'([\u4e00-\u9fff]{2,})', s)
    if m2:
        return m2.group(1)
    # else pick the first reasonable part (prefer length >=2)
    if parts:
        for p in parts:
            p = p.strip()
            if len(p) >= 2:
                return p
        return parts[0].strip()
    # last resort: return cleaned original (trimmed)
    return re.sub(r'\s{2,}', ' ', s).strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--preview', action='store_true')
    p.add_argument('--limit', type=int, default=100)
    p.add_argument('--export', type=str, default='')
    args = p.parse_args()

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    # get distinct artist values ordered by frequency
    cur.execute(
        """
        SELECT `藝人`, COUNT(*) as cnt, GROUP_CONCAT(event_id ORDER BY event_id SEPARATOR ',') as sample_event_ids
        FROM events
        GROUP BY `藝人`
        ORDER BY cnt DESC
        LIMIT %s
        """,
        (args.limit,)
    )
    rows = cur.fetchall()
    export_fh = None
    if args.export:
        export_fh = open(args.export, 'w', encoding='utf-8')
    for artist, cnt, sample_ids in rows:
        suggested = canonicalize_artist(artist or '')
        out = {'original': artist or '', 'count': int(cnt or 0), 'suggested': suggested, 'sample_event_ids': sample_ids}
        line = json.dumps(out, ensure_ascii=False)
        if args.preview:
            print(line)
        if export_fh:
            export_fh.write(line + '\n')
    if export_fh:
        export_fh.close()
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
