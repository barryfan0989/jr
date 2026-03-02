# KKTIX 爬蟲整合指南

## 整合概述

KKTIX 爬蟲已成功整合到主要爬蟲系統中。以下說明整合內容和使用方式。

## 整合變更

### 1. **新增爬蟲實現** 
- **文件**: [crawlers/tier1_crawlers.py](crawlers/tier1_crawlers.py)
- **類別**: `KKTIXCrawler`
- **功能**: 自動爬取 KKTIX 音樂類活動（標籤 ID 1, 7）

### 2. **更新依賴**
- **文件**: [requirements.txt](requirements.txt)
- **新增**: 
  - `seleniumbase>=4.0.0` - 用於瀏覽器自動化和反爬蟲繞過
  - `google-generativeai>=0.3.0` - 用於 Gemini API（可選）

### 3. **更新爬蟲註冊**
- **文件**: [crawlers/__init__.py](crawlers/__init__.py)
- **新增**: `KKTIXCrawler` 導出

### 4. **更新主程式**
- **文件**: [run_all_crawlers.py](run_all_crawlers.py)
- **變更**: 
  - 移除 Gemini API 環境變數檢查（可選）
  - 添加 `KKTIXCrawler` 到爬蟲列表

## 爬蟲特性

### KKTIXCrawler
```python
crawler = KKTIXCrawler()
events = crawler.run()
```

**功能**:
- 自動翻頁遍歷 KKTIX 音樂類活動（15 頁上限）
- 提取活動基本資訊：
  - 活動名稱 (`title`)
  - 活動日期 (`event_date`, `date`)
  - 演出藝人 (`artist`)
  - 活動地點 (`location`)
  - 啟售日期 (`sale_date`)
  - 原始網址 (`url`)

**技術棧**:
- SeleniumBase - 與 UndetectedChromeDriver 整合的反爬蟲
- BeautifulSoup4 - HTML 解析
- 正則表達式 - 信息提取

## 數據格式標準化

所有爬蟲輸出統一格式：
```json
{
  "title": "活動名稱",
  "date": "2026-01-15",
  "url": "https://...",
  "artist": "藝人名稱",
  "location": "活動地點",
  "source": "KKTIX"
}
```

最終儲存格式（標準字段）：
```json
{
  "來源網站": "KKTIX",
  "演出藝人": "藝人名稱",
  "演出時間": "2026-01-15",
  "演出地點": "場地名稱",
  "票價": "",
  "網址": "https://...",
  "爬取時間": "2026-01-15 12:00:00"
}
```

## 使用方式

### 方式 1: 運行所有爬蟲（推薦）
```bash
python run_all_crawlers.py
```
輸出:
- 標準格式 JSON: `all_events_YYYYMMdd_HHmmss.json`
- 備份: `data/concerts.json`

### 方式 2: 單獨運行 KKTIX 爬蟲
```python
from crawlers import KKTIXCrawler
import json

crawler = KKTIXCrawler()
events = crawler.run()

# 儲存為 JSON
with open('kktix_events.json', 'w', encoding='utf-8') as f:
    json.dump(events, f, ensure_ascii=False, indent=2)
```

## 數據庫整合

爬取的數據自動整合到數據庫：

### SQLite
```bash
python json_to_sqlite.py
```
- 自動掃描並導入 JSON 文件
- 自動去重 (按 url, event_time, artist)
- 生成導入日誌

### MySQL
```bash
python json_to_mysql.py
```
- 需要設定環境變數或配置文件
- 支持增量導入

## 性能注意事項

### SeleniumBase 特運:
- 首次運行會下載瀏覽器驅動 (~100MB)
- 單頁加載時間約 5 秒（網絡延遲）
- 15 頁爬取時間約 2-3 分鐘
- 推薦在後台或定時任務運行

### 優化建議:
1. 在晚間或非高峰時段運行
2. 使用 `headless=True` 隱藏瀏覽器窗口
3. 可調整 `max_pages` 限制爬取頁數

## 故障排除

### 問題 1: SeleniumBase 未安裝
```powershell
pip install seleniumbase>=4.0.0
```

### 問題 2: 瀏覽器驅動下載失敗
```powershell
python -m seleniumbase install chromedriver
```

### 問題 3: 超時或連接錯誤
- 檢查網絡連接
- 增加 `time.sleep()` 延遲
- 降低 `max_pages` 值

## 舊版本遷移

如果有舊的獨立 `kktix-crawler/` 資料夾：

1. **備份舊數據**:
   ```bash
   cp -r kktix-crawler kktix-crawler.backup
   ```

2. **移除舊資料夾** (可選):
   ```bash
   rm -rf kktix-crawler
   ```

3. **使用新的整合爬蟲**:
   ```bash
   python run_all_crawlers.py
   ```

## 相關文件

- [爬蟲基礎類別](crawlers/base_crawler.py)
- [Tier 1 爬蟲實現](crawlers/tier1_crawlers.py)
- [主程式](run_all_crawlers.py)
- [SQLite 導入工具](json_to_sqlite.py)
- [MySQL 導入工具](json_to_mysql.py)

## 更新日誌

### v2.0 (2026-03-03)
- ✅ 整合 KKTIX 爬蟲到主系統
- ✅ 標準化數據格式
- ✅ 添加 SeleniumBase 依賴
- ✅ 更新爬蟲註冊和主程式

---

**最後更新**: 2026-03-03  
**版本**: 2.0
