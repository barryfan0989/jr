# 演唱會爬蟲系統整合指南

## 整合概述

本系統已成功整合 **KKTIX** 和 **TixCraft** 爬蟲到主要爬蟲系統中。

## 已整合的爬蟲

### Tier 1 - 主流售票平台

1. **TicketComCrawler** - 年代售票
   - 技術: Gemini API
   - 網址: https://ticket.com.tw/dm.html

2. **KKTIXCrawler** - KKTIX 票務平台
   - 技術: SeleniumBase + UndetectedChromeDriver
   - 網址: https://kktix.com/events
   - 特性: 自動翻頁、反爬蟲繞過

3. **TixCraftCrawler** - 拓元售票 ⭐
   - 技術: Playwright + Playwright Stealth
   - 網址: https://tixcraft.com/activity
   - 特性: 異步爬取、Pydantic 資料驗證

### Tier 2 - 獨立音樂平台

4. **IndievoxCrawler** - iNDIEVOX 獨立音樂
   - 技術: Gemini API
   - 網址: https://www.indievox.com/activity/list

## 整合變更記錄

### 文件更新

1. **crawlers/tier1_crawlers.py**
   - ✓ 添加 `KKTIXCrawler` 類
   - ✓ 添加 `TixCraftCrawler` 類

2. **crawlers/__init__.py**
   - ✓ 導出 `KKTIXCrawler`
   - ✓ 導出 `TixCraftCrawler`

3. **requirements.txt**
   - ✓ `seleniumbase>=4.0.0` - KKTIX 瀏覽器自動化
   - ✓ `playwright>=1.45.0` - TixCraft 瀏覽器自動化
   - ✓ `playwright-stealth>=1.0.6` - TixCraft 反爬蟲
   - ✓ `pydantic>=2.6.0` - TixCraft 資料驗證
   - ✓ `html2text>=2024.2.26` - HTML 轉換
   - ✓ `google-generativeai>=0.3.0` - Gemini API

4. **run_all_crawlers.py**
   - ✓ 添加 `KKTIXCrawler()` 實例
   - ✓ 添加 `TixCraftCrawler()` 實例

### 刪除的檔案

- ✓ `kktix-crawler/` - 舊 KKTIX 爬蟲資料夾
- ✓ `tixcraft_scraper/` - 舊 TixCraft 爬蟲資料夾
- ✓ 所有臨時驗證腳本

## 安裝依賴

```bash
# 安裝 Python 依賴
pip install -r requirements.txt

# 安裝 Playwright 瀏覽器（TixCraft 需要）
python -m playwright install chromium
```

## 使用方式

### 運行所有爬蟲

```bash
python run_all_crawlers.py
```

輸出文件：
- `all_events_YYYYMMdd_HHmmss.json` - 完整爬取結果
- `data/concerts.json` - 備份數據

### 單獨使用某個爬蟲

```python
from crawlers import KKTIXCrawler, TixCraftCrawler

# KKTIX 爬蟲
kktix = KKTIXCrawler()
events = kktix.run()

# TixCraft 爬蟲
tixcraft = TixCraftCrawler()
events = tixcraft.run()
```

## 數據格式

### 爬蟲輸出格式

```json
{
  "title": "活動名稱",
  "date": "2026-03-03",
  "url": "https://...",
  "artist": "藝人名稱",
  "location": "活動地點",
  "source": "KKTIX/TixCraft"
}
```

### 標準化格式（儲存到 JSON）

```json
{
  "來源網站": "KKTIX",
  "演出藝人": "藝人名稱",
  "演出時間": "2026-03-03",
  "演出地點": "場地名稱",
  "票價": "",
  "網址": "https://...",
  "爬取時間": "2026-03-03 12:00:00"
}
```

## 數據庫整合

### SQLite

```bash
python json_to_sqlite.py
```

- 自動掃描 JSON 文件
- 自動去重（按 url, event_time, artist）
- 生成導入日誌

### MySQL

```bash
python json_to_mysql.py
```

- 支持增量導入
- 需要設定數據庫連接

## 爬蟲特性對比

| 爬蟲 | 技術棧 | 優點 | 適用場景 |
|------|--------|------|----------|
| **KKTIX** | SeleniumBase | 穩定、可見瀏覽器操作 | 需要互動的頁面 |
| **TixCraft** | Playwright | 快速、異步、精確 | 大量數據爬取 |
| **年代/iNDIEVOX** | Gemini API | 智能解析、靈活 | HTML 結構複雜 |

## 性能建議

### KKTIX 爬蟲
- 單頁加載時間: ~5 秒
- 15 頁爬取時間: ~2-3 分鐘
- 建議: headless=True 提升速度

### TixCraft 爬蟲
- 異步並發爬取
- 動態延遲避免封鎖
- 自動錯誤恢復

## 故障排除

### 問題 1: 依賴安裝失敗

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 問題 2: Playwright 瀏覽器未安裝

```bash
python -m playwright install chromium
```

### 問題 3: 爬蟲超時

- 檢查網絡連接
- 增加延遲時間
- 使用 headless=False 觀察瀏覽器

## 相關文件

- [crawlers/tier1_crawlers.py](crawlers/tier1_crawlers.py) - 主流爬蟲實現
- [crawlers/base_crawler.py](crawlers/base_crawler.py) - 爬蟲基礎類  
- [run_all_crawlers.py](run_all_crawlers.py) - 主執行程式
- [json_to_sqlite.py](json_to_sqlite.py) - SQLite 導入
- [json_to_mysql.py](json_to_mysql.py) - MySQL 導入

## 更新日誌

### v2.1 (2026-03-03)
- ✅ 整合 TixCraft 爬蟲到主系統
- ✅ 添加 Playwright 異步爬取支持
- ✅ 添加 Pydantic 資料驗證
- ✅ 刪除舊的獨立爬蟲資料夾

### v2.0 (2026-03-03)
- ✅ 整合 KKTIX 爬蟲到主系統
- ✅ 標準化數據格式
- ✅ 添加 SeleniumBase 支持

---

**最後更新**: 2026-03-03  
**版本**: 2.1  
**整合爬蟲數**: 4
