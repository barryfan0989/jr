#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速測試 TicketCom 爬蟲"""
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from crawlers.tier1_crawlers import TicketComCrawler

print("\n測試 TicketCom 爬蟲...\n")

crawler = TicketComCrawler()
events = crawler.run()

print(f'\n最終結果: {len(events)} 場活動')
if events:
    for e in events[:5]:
        print(f'  ✓ {e.get("title")[:40]} ({e.get("date")})')
