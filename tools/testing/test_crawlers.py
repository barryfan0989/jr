#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速測試爬蟲"""
import os
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from crawlers.tier1_crawlers import TicketComCrawler, TixCraftCrawler
from crawlers.tier2_crawlers import IndievoxCrawler

print("\n" + "="*70)
print("爬蟲快速測試 - 測試改進後的 Prompt")
print("="*70)

crawlers_to_test = [
    ("TicketCom", TicketComCrawler()),
    ("TixCraft", TixCraftCrawler()),
    ("Indievox", IndievoxCrawler()),
]

for name, crawler in crawlers_to_test:
    print(f"\n\n測試 {name}...")
    try:
        events = crawler.run()
        print(f"\n結果: {len(events)} 個活動")
        if events:
            for e in events[:2]:
                title = e.get('title', '未知')
                date = e.get('date', '未公布')
                url = e.get('url', '')
                print(f"  ✓ {title[:40]} ({date})")
                if url:
                    print(f"    → {url[:60]}")
    except Exception as e:
        print(f"[錯誤] {e}")

print("\n" + "="*70)
print("測試完成")
print("="*70 + "\n")
