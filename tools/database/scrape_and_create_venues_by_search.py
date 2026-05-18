#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""以網路搜尋（DuckDuckGo）爬取場地地址，並建立/更新 `venues`。

流程：
- 從 `events` 聚合常見 `活動地點` 名稱（或可指定 limit）
- 使用 DuckDuckGo 取得搜尋結果，取第一個結果頁面
- 從結果頁面解析 JSON-LD 或用正則抽取台灣地址
- 若找到合理地址，建立或更新 `venues` 表；若使用 `--preview` 則只列出建議

注意：搜尋與抓取可能遇到反爬或需驗證的頁面，腳本會跳過失敗的案例。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import List, Tuple

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

DDG_SEARCH = 'https://duckduckgo.com/html/'
HEADERS = {'User-Agent': 'jr-venue-scraper/1.0 (+https://example.invalid)'}


def get_candidate_names(cur, limit: int = 100) -> List[Tuple[str, int]]:
	q = "SELECT LOWER(TRIM(e.`活動地點`)) as name, COUNT(*) as c FROM events e GROUP BY LOWER(TRIM(e.`活動地點`)) ORDER BY c DESC"
	if limit:
		q += f" LIMIT {int(limit)}"
	cur.execute(q)
	return [(r[0], int(r[1])) for r in cur.fetchall() if r[0] and r[0].strip()]


def normalize_name(n: str) -> str:
	if not n:
		return ''
	s = str(n)
	s = re.sub(r"\(.*?\)|\[.*?\]|\{.*?\}", '', s)
	s = re.split(r'票價|活動地址|地址|啟售|預售|購票|票務|票價：', s, flags=re.I)[0]
	s = re.sub(r'\s+[-–—:].*$', '', s)
	s = re.sub(r'[^\w\u4e00-\u9fff\s\-]', ' ', s)
	s = re.sub(r'\s+', ' ', s).strip()
	return s


def ddg_search(name: str) -> List[str]:
	try:
		r = requests.post(DDG_SEARCH, data={'q': name}, headers=HEADERS, timeout=12)
		if r.status_code != 200:
			return []
		soup = BeautifulSoup(r.text, 'html.parser')
		links = []
		for a in soup.select('a.result__a'):
			href = a.get('href')
			if href:
				links.append(href)
		# fallback: any result links
		if not links:
			for a in soup.select('a'):
				href = a.get('href')
				if href and href.startswith('http'):
					links.append(href)
		return links
	except Exception:
		return []


def fetch_page(url: str) -> Tuple[str, str]:
	try:
		r = requests.get(url, headers=HEADERS, timeout=12)
		if r.status_code == 200:
			return r.text, r.url
	except Exception:
		return '', url
	return '', url


def extract_address_from_html(html: str) -> str:
	if not html:
		return ''
	soup = BeautifulSoup(html, 'html.parser')
	# try JSON-LD
	for sc in soup.select('script[type="application/ld+json"]'):
		try:
			data = json.loads(sc.string or sc.get_text() or '{}')
		except Exception:
			continue
		nodes = data if isinstance(data, list) else [data]
		for n in nodes:
			if not isinstance(n, dict):
				continue
			loc = n.get('location') or n.get('address') or n.get('addressLocality')
			if isinstance(loc, dict):
				parts = []
				for k in ('streetAddress', 'addressLocality', 'addressRegion', 'postalCode'):
					v = loc.get(k)
					if v:
						parts.append(str(v))
				addr = ' '.join(parts).strip()
				if addr:
					return addr
	text = soup.get_text('\n', strip=True)
	# regex for Taiwan addresses
	m = re.search(r'((?:台|臺)[^\n，。]{0,40}(?:市|縣)[^\n，。]{0,60}(?:路|街|大道|巷|弄|段)[^\n，。]{0,40}號?)', text)
	if m:
		return m.group(1).strip()
	# fallback postal code + city
	m2 = re.search(r'(\d{3,5}\s*(?:台灣|臺灣)?)', text)
	if m2:
		return m2.group(0).strip()
	return ''


def upsert_venue(cur, name: str, address: str) -> int:
	cur.execute('SELECT venue_id, venue_address FROM venues WHERE LOWER(TRIM(venue_name))=%s', (name,))
	r = cur.fetchone()
	if not r:
		cur.execute('INSERT INTO venues (venue_name, venue_address, venue_intro, created_at) VALUES (%s,%s,%s,NOW())', (name, address, ''))
		return cur.lastrowid or 0
	else:
		if not r[1] or not str(r[1]).strip():
			cur.execute('UPDATE venues SET venue_address=%s WHERE venue_id=%s', (address, r[0]))
			return r[0]
	return 0


def main():
	p = argparse.ArgumentParser()
	p.add_argument('--preview', action='store_true')
	p.add_argument('--dry-run', action='store_true')
	p.add_argument('--limit', type=int, default=50)
	p.add_argument('--sleep', type=float, default=1.0)
	args = p.parse_args()

	conn = mysql.connector.connect(**DB_CONFIG)
	cur = conn.cursor()
	try:
		candidates = get_candidate_names(cur, args.limit)
		print('candidates=', len(candidates))
		processed = 0
		created = 0
		updated = 0
		for name, cnt in candidates:
			if not name or name.strip() == '':
				continue
			processed += 1
			raw = name
			qname = normalize_name(raw)
			if not qname:
				print('skip empty after normalize:', raw)
				continue
			print(f'[{processed}] search: "{qname}" (events={cnt})')
			links = ddg_search(qname)
			addr = ''
			for link in links[:4]:
				html, final = fetch_page(link)
				if not html:
					continue
				a = extract_address_from_html(html)
				if a:
					addr = a
					print('  found address from', final)
					break
				time.sleep(0.3)
			if not addr:
				print('  no address found from search results')
				time.sleep(args.sleep)
				continue
			if args.preview or args.dry-run:
				print(f' PREVIEW: "{qname}" -> "{addr}"')
			else:
				vid = upsert_venue(cur, qname, addr)
				if vid:
					if vid and vid > 0:
						if conn.in_transaction:
							pass
						created += 1
						print('  upserted venue id=', vid)
				if processed % 20 == 0:
					conn.commit()
			time.sleep(args.sleep)
		if not (args.preview or args.dry-run):
			conn.commit()
		print('done processed=', processed, 'created/updated=', created)
	finally:
		cur.close()
		conn.close()


if __name__ == '__main__':
	main()
