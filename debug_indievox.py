#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""調試 Indievox 爬蟲"""
import sys
from bs4 import BeautifulSoup
from crawlers.tier2_crawlers import IndievoxCrawler

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

crawler = IndievoxCrawler()

# 抓取第一個活動頁面進行調試
print("取得 Indievox 首頁...")
html = crawler.fetch_html('https://www.indievox.com/activity/list')

# 提取 URL
event_urls = crawler._extract_event_urls(html)
print(f"找到 {len(event_urls)} 個 URL")

if event_urls:
    # 測試第一個 URL
    test_url = event_urls[0]
    print(f"\n測試 URL: {test_url}")
    
    event_html = crawler.fetch_html(test_url)
    
    # 檢查 HTML 結構
    soup = BeautifulSoup(event_html, 'html.parser')
    
    print("\n=== HTML 結構分析 ===")
    print(f"頁面長度: {len(event_html)} 字元\n")
    
    # 尋找標題
    h1 = soup.find('h1')
    if h1:
        print(f"✓ 找到 H1: {h1.text[:50]}")
    else:
        print("✗ 找不到 H1")
    
    h2 = soup.find('h2')
    if h2:
        print(f"✓ 找到 H2: {h2.text[:50]}")
    else:
        print("✗ 找不到 H2")
    
    # 尋找日期相關信息
    print("\n=== 日期尋找 ===")
    for i, text in enumerate(soup.stripped_strings):
        if '202' in text or '月' in text or '日' in text:
            if i < 50:  # 只顯示前 50 個包含日期的文本
                print(f"  {text[:60]}")
    
    # 檢查特定的日期元素
    print("\n=== 檢查所有 span 和 p 標籤 ===")
    for elem in soup.find_all(['span', 'p'])[:10]:
        text = elem.get_text().strip()
        if text:
            print(f"  [{elem.name}] {text[:50]}")
    
    # 嘗試解析
    print("\n=== 嘗試解析 ===")
    result = crawler._parse_event_detail(event_html, test_url)
    if result:
        print(f"✓ 解析成功: {result}")
    else:
        print("✗ 解析失敗")
