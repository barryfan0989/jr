#!/usr/bin/env python3
"""
台灣演唱會爬蟲主程式
整合所有 Tier 1~3 售票網站
"""
import os
import json
import sys
from datetime import datetime
from typing import List, Dict

# 確保環境變數
if 'GEMINI_API_KEY' not in os.environ:
    print("⚠️  請設定環境變數 GEMINI_API_KEY")
    print("   Windows: $env:GEMINI_API_KEY='your-key-here'")
    print("   Linux/Mac: export GEMINI_API_KEY='your-key-here'")
    sys.exit(1)

# 匯入所有爬蟲
from crawlers import (
    TixCraftCrawler,
    TicketComCrawler,
    KKTIXCrawler,
    IndievoxCrawler,
    AccupassCrawler,
    BooksTicketCrawler
)


def main():
    """主執行流程"""
    print("\n" + "="*70)
    print("🎵 台灣演唱會資訊爬蟲系統 v2.0")
    print("="*70)
    
    # 初始化所有爬蟲（按 Tier 順序）
    crawlers = [
        # Tier 1 - 主流核心
        TixCraftCrawler(),
        TicketComCrawler(),
        KKTIXCrawler(),
        
        # Tier 2 - 次主流與獨立
        IndievoxCrawler(),
        AccupassCrawler(),
        
        # Tier 3 - 補充
        BooksTicketCrawler()
    ]
    
    all_events = []
    success_count = 0
    failed_sites = []
    
    # 依序執行所有爬蟲
    for crawler in crawlers:
        try:
            events = crawler.run()
            if events:
                all_events.extend(events)
                success_count += 1
            else:
                failed_sites.append(crawler.site_name)
        except Exception as e:
            print(f"✗ {crawler.site_name}: 發生異常 - {e}")
            failed_sites.append(crawler.site_name)
    
    # 統計結果
    print("\n" + "="*70)
    print("📊 爬取結果統計")
    print("="*70)
    print(f"✓ 成功網站: {success_count}/{len(crawlers)}")
    print(f"✓ 總活動數: {len(all_events)}")
    
    if failed_sites:
        print(f"✗ 失敗網站: {', '.join(failed_sites)}")
    
    # 轉換為標準格式
    formatted_events = []
    for event in all_events:
        formatted_events.append({
            '來源網站': event.get('source', '未知'),
            '演出藝人': event.get('title', '未知'),
            '演出時間': event.get('date', '未公布'),
            '演出地點': '未公布',  # Gemini 沒有提取地點
            '票價': '',
            '網址': event.get('url', ''),
            '爬取時間': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    # 儲存結果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"all_events_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(formatted_events, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 已儲存至: {output_file}")
    
    # 同時更新到 data/concerts.json
    data_file = "data/concerts.json"
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_events, f, ensure_ascii=False, indent=2)
        print(f"💾 已更新至: {data_file}")
    except Exception as e:
        print(f"⚠️  無法更新 {data_file}: {e}")
    
    print("\n" + "="*70)
    print("✓ 爬取完成！")
    print("="*70 + "\n")
    
    return formatted_events


if __name__ == "__main__":
    main()
