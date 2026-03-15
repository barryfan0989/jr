#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速爬蟲測試 - 只爬取前幾個活動"""
import os
import sys
import json
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from crawlers.tier1_crawlers import TicketComCrawler, TixCraftCrawler
from crawlers.tier2_crawlers import IndievoxCrawler

def quick_test_crawler(crawler_class, limit_events=3):
    """快速測試爬蟲"""
    crawler = crawler_class()
    crawler_name = crawler.site_name
    
    print(f"\n{'='*60}")
    print(f"測試 {crawler_name}")
    print(f"{'='*60}")
    
    try:
        events = crawler.run()
        
        if events:
            # 只保留前 limit_events 個
            limited_events = events[:limit_events]
            print(f"\n✓ 成功爬取 {len(events)} 個活動（顯示前 {len(limited_events)} 個）")
            
            for i, event in enumerate(limited_events, 1):
                print(f"\n[{i}] {event.get('title', '未知')}")
                print(f"    日期: {event.get('date', '未公布')}")
                print(f"    地點: {event.get('location', '未公布')}")
                if 'url' in event:
                    print(f"    URL: {event['url'][:60]}...")
            
            return limited_events
        else:
            print(f"未找到任何活動")
            return []
            
    except Exception as e:
        print(f"✗ 爬蟲出錯: {e}")
        import traceback
        traceback.print_exc()
        return []

# 測試三個爬蟲
print("\n" + "="*70)
print("快速爬蟲測試 - HTML 直接解析")
print("="*70)

all_results = []

crawlers_to_test = [
    ("TicketCom", TicketComCrawler),
    ("Indievox", IndievoxCrawler),
    ("TixCraft", TixCraftCrawler),
]

for name, crawler_class in crawlers_to_test:
    results = quick_test_crawler(crawler_class, limit_events=3)
    all_results.extend(results)

# 保存結果到文件
if all_results:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"quick_test_results_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n\n{'='*70}")
    print(f"測試完成！共爬取 {len(all_results)} 個活動")
    print(f"結果已保存至: {output_file}")
    print(f"{'='*70}\n")
else:
    print("\n[警告] 未爬取到任何活動")

