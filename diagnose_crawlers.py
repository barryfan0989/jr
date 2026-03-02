#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬蟲系統診斷工具
檢查各爬蟲的失敗原因
"""
import sys
import os

# 設定 UTF-8 編碼
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

print("\n" + "="*70)
print("爬蟲系統診斷工具")
print("="*70)

# 1. 檢查依賴
print("\n[1] 檢查必要依賴...")
print("-" * 70)

deps = {
    'seleniumbase': 'KKTIX 爬蟲',
    'requests': '通用爬蟲',
    'beautifulsoup4': 'HTML 解析',
    'google.generativeai': 'Gemini API',
}

failed_deps = []
for pkg, usage in deps.items():
    try:
        __import__(pkg)
        print(f"[成功] {pkg:25} | {usage}")
    except:
        print(f"[失敗] {pkg:25} | {usage}")
        failed_deps.append(pkg)

# 2. 檢查爬蟲導入
print("\n[2] 檢查爬蟲導入...")
print("-" * 70)

try:
    from crawlers import TicketComCrawler, KKTIXCrawler, TixCraftCrawler
    from crawlers.tier2_crawlers import IndievoxCrawler
    
    crawlers = [
        ('TicketComCrawler', TicketComCrawler, '年代售票'),
        ('KKTIXCrawler', KKTIXCrawler, 'KKTIX 票務'),
        ('TixCraftCrawler', TixCraftCrawler, '拓元售票'),
        ('IndievoxCrawler', IndievoxCrawler, 'iNDIEVOX'),
    ]
    
    print(f"[成功] 導入 {len(crawlers)} 個爬蟲")
    for name, cls, desc in crawlers:
        print(f"  - {name:20} | {desc}")
        
except Exception as e:
    print(f"[失敗] 爬蟲導入失敗: {e}")

# 3. 檢查環境變數
print("\n[3] 檢查環境變數...")
print("-" * 70)

env_vars = {
    'GEMINI_API_KEY': 'Gemini API (可選)',
}

for var, desc in env_vars.items():
    if var in os.environ:
        value = os.environ[var]
        masked = value[:5] + '***' + value[-2:] if len(value) > 7 else '***'
        print(f"[已設定] {var:20} = {masked} | {desc}")
    else:
        print(f"[未設定] {var:20} = N/A   | {desc}")

# 4. 總結
print("\n" + "="*70)
print("診斷結果")
print("="*70)

if 'seleniumbase' in failed_deps:
    print("\n[警告] KKTIX 爬蟲已禁用（seleniumbase 缺失）")

if 'google.generativeai' in failed_deps:
    print("\n[警告] Gemini API 無法使用（未安裝或未設定）")
    print("  解決方案：")
    print("    1. 安裝: pip install google-generativeai")
    print("    2. 設定: 在 .env 或環境變數中設定 GEMINI_API_KEY")

print("\n[建議] 系統以降級模式運行（無 Gemini 解析）")
print("="*70 + "\n")
