#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回填遠端 events 表缺值欄位（整理版）

策略：
- 讀取 events 中仍缺值的列（有網址的），先用資料庫內的參考表（venues / event_schedules / sales_channels / ticket_pricing）回填地址/時間/票價等。
- 若仍缺，則抓活動詳頁做正則解析。
- 最後若仍缺，使用 Gemini 作為 fallback（需設定 GEMINI_API_KEY）。

使用方式：
  python tools/database/backfill_missing_remote_event_fields.py [--dry-run] [--limit N]

注意：此腳本會更新遠端資料庫，建議先用 --dry-run 或 --limit 小量測試。
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import mysql.connector
import requests
from bs4 import BeautifulSoup


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

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
}

MISSING_VALUES = {'', '未取得', '未提供', '未公布', None}
_GEMINI = None


def is_missing(v) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() in MISSING_VALUES
    return False


def clean_text(v) -> str:
    return re.sub(r'\s+', ' ', str(v or '').replace('\u3000', ' ')).strip()


def fetch_page(url: str) -> Tuple[str, str]:
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=18)
        if r.status_code == 200 and 'html' in r.headers.get('Content-Type', '').lower():
            return r.text, r.url
    except Exception:
        pass
    return '', url


def extract_labeled_value(text: str, labels, max_len=160) -> str:
    if not text:
        return ''
    for lab in labels:
        m = re.search(rf'(?:{re.escape(lab)})\s*[:：｜|]\s*([^\n\r]{{1,{max_len}}})', text, re.I)
        if m:
            return clean_text(m.group(1))
    return ''


def extract_event_time(text: str) -> str:
    v = extract_labeled_value(text, ['活動時間', '演出時間', '日期', '時間'])
    if v:
        return v
    m = re.search(r'(20\d{2}[/\.-]\d{1,2}[/\.-]\d{1,2}(?:\s*\d{1,2}:\d{2})?)', text)
    return clean_text(m.group(1)) if m else ''


def extract_sale_time(text: str) -> str:
    v = extract_labeled_value(text, ['啟售時間', '售票時間', '開賣時間', '開賣'])
    if v:
        return v
    m = re.search(r'(?:啟售|開賣|售票)[^0-9\n\r]{0,6}(20\d{2}[/\.-]\d{1,2}[/\.-]\d{1,2})', text)
    return clean_text(m.group(1)) if m else ''


def extract_price_text(text: str) -> str:
    v = extract_labeled_value(text, ['票價', 'Price'])
    if v:
        return v
    matches = re.findall(r'(NT\$\s*\d{2,5}(?:[-~～]\s*NT\$?\s*\d{2,5})?)|免費', text, re.I)
    uniq = []
    for m in matches:
        if isinstance(m, tuple):
            s = next((x for x in m if x), '')
        else:
            s = m
        s = clean_text(s)
        if s and s not in uniq:
            uniq.append(s)
    return '、'.join(uniq[:4])


def extract_venue_and_address(text: str, soup: BeautifulSoup) -> Tuple[str, str]:
    venue = extract_labeled_value(text, ['場地', '地點', '活動地點', 'Venue'])
    address = extract_labeled_value(text, ['地址', 'Address'])
    # try json-ld
    for sc in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(sc.string or sc.get_text() or '{}')
        except Exception:
            continue
        nodes = payload if isinstance(payload, list) else [payload]
        for n in nodes:
            if not isinstance(n, dict):
                continue
            if not venue:
                loc = n.get('location') or n.get('location', '')
                if isinstance(loc, dict):
                    venue = clean_text(loc.get('name') or '')
                    addr = loc.get('address')
                    if isinstance(addr, dict):
                        address = clean_text(addr.get('streetAddress') or addr.get('addressLocality') or '')
                elif isinstance(loc, str) and loc:
                    venue = clean_text(loc)
            if venue and address:
                break
        if venue and address:
            break
    # fallback regex
    if not address:
        m = re.search(r'((?:台|臺)[^\s，。]{0,20}(?:市|縣)[^\s，。]{0,40}(?:路|街|大道|段|巷|弄)[^\s，。]{0,20}號?)', text)
        if m:
            address = clean_text(m.group(1))
    return venue or '', address or ''


def load_reference_maps(cur) -> Tuple[Dict[str, str], Dict[int, str], Dict[int, str], Dict[int, str]]:
    venue_map: Dict[str, str] = {}
    cur.execute("SELECT venue_name, venue_address FROM venues WHERE venue_name IS NOT NULL AND venue_name<>''")
    for name, addr in cur.fetchall():
        if name:
            venue_map[clean_text(name).lower()] = clean_text(addr)

    schedule_map: Dict[int, str] = {}
    cur.execute('SELECT event_id, MIN(performance_date), MIN(start_time) FROM event_schedules GROUP BY event_id')
    for eid, pd, st in cur.fetchall():
        if pd:
            schedule_map[int(eid)] = f'{pd} {str(st)[:8]}' if st else str(pd)

    sale_map: Dict[int, str] = {}
    cur.execute('SELECT event_id, MIN(start_date), MIN(start_time), MIN(sales_status) FROM sales_channels GROUP BY event_id')
    for eid, sd, st, ss in cur.fetchall():
        parts = []
        if sd:
            parts.append(str(sd))
        if st:
            parts.append(str(st)[:8])
        if ss:
            parts.append(clean_text(ss))
        if parts:
            sale_map[int(eid)] = ' '.join(parts)

    price_map: Dict[int, str] = {}
    cur.execute("SELECT event_id, GROUP_CONCAT(CONCAT(COALESCE(tier_name,'票種'),':',COALESCE(price_amount,'')) SEPARATOR '、') FROM ticket_pricing GROUP BY event_id")
    for eid, p in cur.fetchall():
        if p:
            price_map[int(eid)] = clean_text(p)

    return venue_map, schedule_map, sale_map, price_map


def get_gemini():
    global _GEMINI
    if _GEMINI is not None:
        return _GEMINI
    key = os.getenv('GEMINI_API_KEY', '').strip()
    if not key:
        _GEMINI = False
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=key)
        _GEMINI = genai.GenerativeModel('gemini-2.5-flash')
        return _GEMINI
    except Exception:
        _GEMINI = False
        return None


def gemini_extract(title: str, text: str, url: str, site: str) -> Dict[str, str]:
    model = get_gemini()
    if not model:
        return {}
    prompt = f"請從下列頁面內容提取藝人、活動時間、搶票時間、活動地點、活動地址、票價，回傳 JSON。\n網址：{url}\n站點：{site}\n標題：{title}\n內容前 4000 字：\n{text[:4000]}"
    try:
        r = model.generate_content(prompt)
        txt = r.text.strip()
        if txt.startswith('```'):
            txt = txt.split('```')[1]
            if txt.startswith('json'):
                txt = txt[4:]
            txt = txt.split('```')[0].strip()
        return json.loads(txt)
    except Exception:
        return {}


def update_event(cur, eid: int, patch: Dict[str, str]) -> int:
    sets = []
    params = []
    for k, v in patch.items():
        if v and not is_missing(v):
            sets.append(f'`{k}`=%s')
            params.append(v)
    if not sets:
        return 0
    params.append(eid)
    cur.execute(f'UPDATE events SET {", ".join(sets)} WHERE event_id=%s', tuple(params))
    return cur.rowcount


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--preview', action='store_true', help='process and print suggested patches but do not commit')
    p.add_argument('--limit', type=int, default=0)
    args = p.parse_args()

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        cur.execute("""
        SELECT event_id, `來源網站`, `活動名稱`, `藝人`, `搶票時間`, `活動時間`, `活動地點`, `活動地址`, `票價`, `網址`
        FROM events
        WHERE `網址` IS NOT NULL AND `網址`<>'' AND (
          `藝人` IS NULL OR `藝人` IN ('未取得','未提供','未公布','') OR
          `搶票時間` IS NULL OR `搶票時間` IN ('未取得','未提供','未公布','') OR
          `活動時間` IS NULL OR `活動時間` IN ('未取得','未提供','未公布','') OR
          `活動地點` IS NULL OR `活動地點` IN ('未取得','未提供','未公布','') OR
          `活動地址` IS NULL OR `活動地址` IN ('未取得','未提供','未公布','') OR
          `票價` IS NULL OR `票價` IN ('未取得','未提供','未公布','')
        ) ORDER BY event_id
        """)
        rows = cur.fetchall()
        print('candidates=', len(rows))

        # stats
        src = Counter()
        fld = Counter()
        for _, site, _, a, s, e, v, ad, pr, _ in rows:
            src[clean_text(site) or 'unknown'] += 1
            if is_missing(a):
                fld['藝人'] += 1
            if is_missing(s):
                fld['搶票時間'] += 1
            if is_missing(e):
                fld['活動時間'] += 1
            if is_missing(v):
                fld['活動地點'] += 1
            if is_missing(ad):
                fld['活動地址'] += 1
            if is_missing(pr):
                fld['票價'] += 1

        print('top_sources:')
        for k, c in src.most_common(10):
            print(' ', k, c)
        print('missing_fields:')
        for k, c in fld.most_common():
            print(' ', k, c)

        if args.dry_run and not args.preview:
            return

        venue_map, schedule_map, sale_map, price_map = load_reference_maps(cur)

        limit = args.limit or 0
        processed = 0
        updated = 0

        for eid, site, title, artist, sale_time, event_time, venue, address, price, url in rows:
            if limit and processed >= limit:
                break
            processed += 1

            patch: Dict[str, str] = {}
            if is_missing(address):
                ref = ''
                if venue:
                    ref = venue_map.get(clean_text(venue).lower(), '')
                if ref:
                    patch['活動地址'] = ref
            if is_missing(event_time):
                if int(eid) in schedule_map:
                    patch['活動時間'] = schedule_map[int(eid)]
            if is_missing(sale_time):
                if int(eid) in sale_map:
                    patch['搶票時間'] = sale_map[int(eid)]
            if is_missing(price):
                if int(eid) in price_map:
                    patch['票價'] = price_map[int(eid)]

            # if still missing some, fetch page and use rules/structured data
            need_fetch = any(is_missing(x) for x in [artist, sale_time, event_time, venue, address, price])
            html = ''
            final_url = url
            if need_fetch:
                html, final_url = fetch_page(url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    text = clean_text(soup.get_text('\n', strip=True))
                    title_text = clean_text(soup.title.get_text(' ', strip=True) if soup.title else title)
                    if is_missing(artist):
                        a = extract_labeled_value(text, ['藝人', '演出者', 'Artist'], 120) or ''
                        if not a:
                            a = re.match(r'^([^－\-—：:\s（]{2,30})', clean_text(title_text))
                            a = a.group(1).strip() if a else ''
                        if a:
                            patch['藝人'] = a
                    if is_missing(event_time) and '活動時間' not in patch:
                        ev = extract_event_time(text)
                        if ev:
                            patch['活動時間'] = ev
                    if is_missing(sale_time) and '搶票時間' not in patch:
                        st = extract_sale_time(text)
                        if st:
                            patch['搶票時間'] = st
                    if is_missing(price) and '票價' not in patch:
                        pr = extract_price_text(text)
                        if pr:
                            patch['票價'] = pr
                    if (is_missing(venue) or is_missing(address)) and ('活動地點' not in patch or '活動地址' not in patch):
                        v, ad = extract_venue_and_address(text, soup)
                        if is_missing(venue) and v:
                            patch['活動地點'] = v
                        if is_missing(address) and ad:
                            patch['活動地址'] = ad

            # if still missing, try Gemini
            still_missing = [f for f in ['藝人', '活動時間', '搶票時間', '活動地點', '活動地址', '票價'] if f not in patch]
            if still_missing:
                ai = gemini_extract(title or '', (text if html else ''), final_url, site or '')
                if isinstance(ai, dict):
                    for k in still_missing:
                        v = clean_text(ai.get(k, ''))
                        if v and not is_missing(v):
                            patch[k] = v

            if patch:
                patch['資料來源檔'] = f'backfill:{site or "unknown"}:{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                if args.preview or args.dry_run:
                    print(f'PREVIEW event_id={eid} site={site} url={url} patch={patch}')
                else:
                    updated += update_event(cur, int(eid), patch)
                    if updated % 25 == 0:
                        conn.commit()

        conn.commit()
        print('processed=', processed, 'updated=', updated)

    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
