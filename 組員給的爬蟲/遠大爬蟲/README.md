# 遠大售票爬蟲 (TicketPlus) - v7

精準解析遠大售票系統（ticketplus.com.tw）的演唱會資訊爬蟲。

## 安裝依賴

確保已安裝所需的 Python 套件：

```bash
pip install playwright requests pandas openpyxl
playwright install chromium
```

## 運行爬蟲

```bash
cd 組員給的爬蟲/遠大爬蟲
python run_scraper.py
```

### 配置選項

編輯 `run_scraper.py` 中的設定區：

- `SHOW_BROWSER`: `True` 顯示瀏覽器視窗，`False` 背景執行（預設）
- `MAX_ITEMS`: 限制爬取數量（0 表示全部）

## 輸出格式

爬蟲遵循統一格式，輸出到 `爬蟲資料/ticketplus_output/`：

### 輸出文件

- `ticketplus_activities.json` - JSON 格式
- `ticketplus_activities.csv` - CSV 格式
- `ticketplus_activities.xlsx` - Excel 格式

### 資料欄位

| 欄位 | 說明 |
|------|------|
| 活動ID | 遠大平台的活動 ID |
| 活動名稱 | 演唱會/活動名稱 |
| 活動日期 | 活動日期 |
| 演出時間 | 各票種的進場/開演時間 |
| 搶票時間 | 開始售票時間 |
| 活動場地 | 場館名稱（含地址） |
| 票價資訊 | 各票種的價格 |
| 活動狀態 | 未開賣/售票中/已售完/已結束 |
| 活動描述 | 簡短活動說明 |
| 圖片URL | 活動海報圖片連結 |
| 活動頁面 | 遠大平台的活動連結 |
| 爬取時間 | 資料爬取的時間戳記 |

## 資料合併

爬蟲輸出會自動整合到統一資料庫流程：

```bash
cd tools/database
python build_unified_database.py
```

此腳本會：
1. 讀取 `ticketplus_activities.json`
2. 與其他平台資料合併（KKTIX、Tixcraft、寬宏等）
3. 去重並輸出到 `爬蟲資料/整理後/concerts_merged.json`
4. 同步到 MySQL 資料庫

## 技術細節

### API 來源

- 活動列表：`https://apis.ticketplus.com.tw/config/api/v1/getS3?path=main/mainEvents.json`
- 活動頁面：`https://ticketplus.com.tw/activity/{活動ID}`

### 解析策略

使用 Playwright 自動化瀏覽器以：
1. 載入完整的動態頁面
2. 攔截 API 回應
3. 提取頁面上的 `<p>` 段落文字
4. 精準匹配格式化的資料（Date | ..., Time | ..., Venue | ...）
5. 內容安全的票價/場地/時間解析

### 反偵測機制

- 隨機延遲（0.8-1.8 秒）
- 禁用自動化標記
- 模擬真實的用戶代理和瀏覽器特性
- 模擬真實的本地化和時區設定

## 注意事項

- 爬蟲會查詢遠大平台的 API 取得所有活動清單，根據列表數量可能耗時 5-30 分鐘
- 建議在背景執行（`SHOW_BROWSER=False`）
- 首次執行可能下載較大的 Chromium 瀏覽器檔案（~300MB）
- 若遭遇網路超時，可降低 `MAX_ITEMS` 限制或調整延遲時間

## 故障排除

### Playwright 安裝失敗

```bash
playwright install chromium
```

### 爬蟲卡住

- 檢查網路連線
- 增加 `rand_sleep()` 中的延遲時間
- 嘗試設定 `MAX_ITEMS` 進行測試

### 資料缺失

- 檢查遠大平台是否有最新資料
- 查看 API 是否有變更（需要自行調整 API 路徑及解析邏輯）

## 更新日誌

### v7 (2026-04)
- 新增精準的 HTML 文字格式解析
- 支援 API 攔截補充資訊
- 優化反偵測機制
- 統一輸出格式整合到資料庫
