# 台灣演唱會資訊爬蟲系統

## 專案說明

本專案用於爬取台灣各大售票網站的演唱會資訊，包括：
- **演出藝人**
- **演出時間**
- **演出地點**
- **活動網址**

## 檔案說明

- `ticket_sites_list.py` - 售票網站清單與優先等級定義
- `concert_crawler.py` - 主要爬蟲程式
- `requirements.txt` - Python 套件需求

## 網站爬取等級

### 等級 1（最高優先，每小時爬取）
- 拓元售票系統 (TixCraft)
- KKTIX
- 年代售票
- KLOOK 客路

### 等級 2（次要優先，每 2-3 小時爬取）
- ibon 售票系統
- 寬宏售票
- FamiTicket 全家售票
- Accupass 活動通

### 等級 3（補充資料，每日爬取）
- Opentix 兩廳院售票
- Indievox
- 博客來售票
- Citytalk 城市通

## 安裝步驟

1. 安裝 Python 3.8 或以上版本

2. 安裝必要套件：
```bash
pip install -r requirements.txt
```

## 使用方式

### 執行爬蟲程式

```bash
python concert_crawler.py
```

執行後會提示選擇：
1. 只爬取等級 1 網站（最高優先）
2. 爬取等級 1 + 2 網站
3. 爬取全部等級網站

然後選擇儲存格式：
1. Excel
2. JSON
3. 兩者都要

### 生成網站清單

```bash
python ticket_sites_list.py
```

會生成包含所有售票網站資訊的 Excel 檔案。

## 輸出格式

### Excel 檔案
- 包含所有演唱會資訊
- 按來源網站分 sheet
- 自動去除重複資料

### JSON 檔案
- 結構化的 JSON 格式
- 便於後續程式處理

## 資料欄位

| 欄位名稱 | 說明 |
|---------|------|
| 來源網站 | 資料來源的售票網站名稱 |
| 演出藝人 | 演唱會藝人或團體名稱 |
| 演出時間 | 演出日期與時間 |
| 演出地點 | 演出場地名稱 |
| 網址 | 活動詳細頁面連結 |
| 爬取時間 | 資料爬取的時間戳記 |

## 注意事項

1. **反爬蟲機制**：部分網站（如拓元）有反爬蟲機制，需要：
   - 適當的延遲時間（已內建）
   - 可能需要處理驗證碼
   - 建議不要過度頻繁爬取

2. **網頁結構變動**：
   - 售票網站可能會更新網頁結構
   - 需要定期檢查並更新選擇器（selector）
   - 目前程式中的 class 名稱需根據實際網站調整

3. **法律與道德**：
   - 遵守網站的 robots.txt
   - 不要對網站造成過大負擔
   - 僅供個人學習研究使用

## 進階客製化

### 調整爬取延遲

在 `concert_crawler.py` 中修改 `delay` 參數：

```python
manager.crawl_all(delay=3)  # 改為 3 秒延遲
```

### 新增其他網站爬蟲

1. 繼承 `ConcertCrawler` 類別
2. 實作 `crawl()` 方法
3. 加入到 `ConcertCrawlerManager` 對應等級

```python
class NewSiteCrawler(ConcertCrawler):
    def __init__(self):
        super().__init__()
        self.base_url = "https://example.com"
        self.site_name = "新網站名稱"
    
    def crawl(self):
        # 實作爬取邏輯
        pass
```

## 疑難排解

### 套件安裝問題
```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### 編碼問題
程式已設定 UTF-8 編碼，若仍有問題可檢查系統預設編碼。

### 連線逾時
可在程式中調整 `timeout` 參數：
```python
response = requests.get(url, headers=self.headers, timeout=15)
```

## 更新日誌

- 2025-12-05：初始版本
  - 建立基礎爬蟲架構
  - 支援多個售票網站
  - 三級優先等級系統

## 授權

本專案僅供學習研究使用。
