#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""調試 TicketCom HTML 結構"""
import sys
from bs4 import BeautifulSoup
from crawlers.tier1_crawlers import TicketComCrawler

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

crawler = TicketComCrawler()

print("取得 TicketCom 首頁...")
html = crawler.fetch_html('https://ticket.com.tw/dm.html')

print(f"HTML 大小: {len(html)} 字元\n")

# 檢查 HTML 結構
soup = BeautifulSoup(html, 'html.parser')

print("=== 尋找所有連結 ===")
links = soup.find_all('a')
print(f"總共找到 {len(links)} 個連結\n")

# 顯示前 20 個連結
print("前 20 個連結：")
for i, link in enumerate(links[:20]):
    href = link.get('href', '')
    text = link.get_text().strip()[:50]
    if href:
        print(f"  {i+1}. [{text}] → {href[:60]}")

# 尋找特定類型的連結
print("\n\n=== 尋找可能的活動連結 ===")
activity_links = []

for link in links:
    href = link.get('href', '')
    text = link.get_text().strip()
    
    # 尋找包含票券或活動信息的連結
    if any(keyword in href.lower() for keyword in ['event', 'ticket', 'show', 'concert', 'dm']):
        activity_links.append((href, text))
        print(f"  ✓ {text[:40]} → {href[:60]}")

if not activity_links:
    print("  ✗ 未找到活動連結")
    
    # 查看 HTML 的其他結構
    print("\n=== 檢查 JavaScript 或其他動態內容 ===")
    
    # 尋找 script 標籤中的 JSON 數據
    scripts = soup.find_all('script')
    print(f"找到 {len(scripts)} 個 script 標籤")
    
    # 檢查是否有 div 或 section 容器
    divs = soup.find_all('div', class_=['activity', 'event', 'concert', 'item'])
    print(f"找到 {len(divs)} 個分類 div")
    
    # 顯示頁面主要結構
    print("\n=== 頁面主要元素 ===")
    for tag in ['main', 'section', 'article', 'div']:
        elements = soup.find_all(tag, limit=5)
        if elements:
            print(f"{tag}: {len(elements)} 個")
