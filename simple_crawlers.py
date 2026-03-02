#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡化版爬蟲系統（無 Gemini API 和 SeleniumBase）
直接使用 requests + beautifulsoup 提取資訊
"""
import json
import sys
from datetime import datetime
from typing import List, Dict

# 設定 UTF-8 編碼
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from bs4 import BeautifulSoup

def scrape_tixcraft() -> List[Dict]:
    """爬取拓元售票活動"""
    print("\n" +"="*70)
    print("TixCraft 爬蟲啟動")
    print("="*70)
    
    try:
        url = "https://tixcraft.com/activity"
        print(f"[正在] 訪問 {url}...")
        
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"[失敗] HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        events = []
        
        # 簡單的活動卡片解析
        for card in soup.find_all('div', class_=['activity-card', 'product-item']):
            title_elem = card.find(['h2', 'h3', 'a'])
            if not title_elem:
                continue
                
            title = title_elem.get_text(strip=True)
            if not title:
                continue
            
            # 嘗試找到連結
            link = card.find('a', href=True)
            url = link['href'] if link else ""
            
            events.append({
                'title': title,
                'date': '未公布',
                'url': url,
                'artist': title.split()[0] if title else '未知',
                'location': '未公布',
                'source': 'TixCraft'
            })
        
        if events:
            print(f"[成功] 找到 {len(events)} 場活動")
        else:
            print(f"[訊息] 未找到任何活動")
        
        return events
        
    except Exception as e:
        print(f"[失敗] {e}")
        return []


def scrape_ticketcom() -> List[Dict]:
    """爬取年代售票活動"""
    print("\n" + "="*70)
    print("年代售票爬蟲啟動")
    print("="*70)
    
    try:
        url = "https://ticket.com.tw/dm.html"
        print(f"[正在] 訪問 {url}...")
        
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"[失敗] HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        events = []
        
        # 簡單的活動卡片解析
        for card in soup.find_all(['div', 'li'], class_=['concert', 'show', 'event']):
            title_elem = card.find(['h2', 'h3', 'a', 'span'])
            if not title_elem:
                continue
                
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            
            events.append({
                'title': title,
                'date': '未公布',
                'url': '',
                'artist': title.split()[0] if title else '未知',
                'location': '未公布',
                'source': 'TicketCom'
            })
        
        if events:
            print(f"[成功] 找到 {len(events)} 場活動")
        else:
            print(f"[訊息] 未找到任何活動（結構複雜需要 JavaScript 解析）")
        
        return events
        
    except Exception as e:
        print(f"[失敗] {e}")
        return []


def scrape_indievox() -> List[Dict]:
    """爬取 iNDIEVOX 活動"""
    print("\n" + "="*70)
    print("iNDIEVOX 爬蟲啟動")
    print("="*70)
    
    try:
        url = "https://www.indievox.com/activity/list"
        print(f"[正在] 訪問 {url}...")
        
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"[失敗] HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        events = []
        
        # 簡單的活動卡片解析
        for card in soup.find_all(['div', 'li'], class_=['activity', 'event', 'item']):
            title_elem = card.find(['h2', 'h3', 'a', 'span'])
            if not title_elem:
                continue
                
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            
            events.append({
                'title': title,
                'date': '未公布',
                'url': '',
                'artist': title,
                'location': '未公布',
                'source': 'Indievox'
            })
        
        if events:
            print(f"[成功] 找到 {len(events)} 場活動")
        else:
            print(f"[訊息] 未找到任何活動（結構複雜需要 JavaScript 解析）")
        
        return events
        
    except Exception as e:
        print(f"[失敗] {e}")
        return []


def main():
    print("\n" + "="*70)
    print("簡化版爬蟲系統 (無 Gemini API)")
    print("="*70)
    
    all_events = []
    
    # 運行所有爬蟲
    results = [
        ('拓元售票', scrape_tixcraft()),
        ('年代售票', scrape_ticketcom()),
        ('iNDIEVOX', scrape_indievox()),
    ]
    
    success = 0
    for name, events in results:
        if events:
            all_events.extend(events)
            success += 1
        else:
            print(f"[無數據] {name}")
    
    # 統計
    print("\n" + "="*70)
    print("爬取結果統計")
    print("="*70)
    print(f"[成功] 網站: {success}/3")
    print(f"[成功] 活動數: {len(all_events)}")
    
    # 保存結果
    if all_events:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"simple_events_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_events, f, ensure_ascii=False, indent=2)
        
        print(f"[保存] 已儲存至: {output_file}")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
