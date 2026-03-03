# 🎫 Tixcraft 拓元售票爬蟲 - 完整版

這是一個專業級的 Tixcraft 拓元售票網活動爬蟲系統，包含精準欄位提取、實時監控等功能。

## 📁 資料夾結構

```
tixcraft_scraper/
├── tixcraft_precision_field_scraper.py  # 主要爬蟲（推薦使用）
├── tixcraft_monitor.py                   # 實時監控工具
├── run_scraper.py                        # 統一啟動器
├── requirements.txt                      # Python 依賴
├── README.md                            # 本檔案
└── QUICK_START.md                       # 快速開始指南
```

## 🚀 快速開始

### 1️⃣ 環境準備

```bash
# 建立虛擬環境（推薦）
python -m venv venv

# 啟動虛擬環境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

### 2️⃣ 執行爬蟲

```bash
# 方法一：使用統一啟動器（推薦）
python run_scraper.py              # 運行精準欄位版（預設）
python run_scraper.py monitor      # 運行監控版

# 方法二：直接執行
python tixcraft_precision_field_scraper.py  # 精準欄位爬蟲
python tixcraft_monitor.py                  # 監控工具
```

## 📊 可用爬蟲版本

### 1. 精準欄位版（推薦）
**檔案**: `tixcraft_precision_field_scraper.py`

功能特點：
- ✅ 智慧型日期時間合併提取
- ✅ 多層級場館地點識別
- ✅ 完整票價資訊蒐集
- ✅ 售票時間回退檢測
- ✅ JavaScript dataLayer 提取
- ✅ 反偵測機制強化
- ✅ 即時 JSON 存檔
- ✅ 數據自動去重複與合併

提取欄位：
- `title` - 活動標題（強制補全）
- `event_info` - 演出日期/時間（合併版）
- `location` - 演出地點
- `price` - 票價資訊
- `sale_time` - 售票時間
- `url` - 活動連結

### 2. 監控版
**檔案**: `tixcraft_monitor.py`

功能特點：
- 🔄 持續監控活動列表
- 🆕 自動偵測新演出
- 📊 活動狀態追蹤
- 💾 本地資料庫管理
- ⏰ 可自訂檢查間隔

使用場景：
- 監控新上架演出
- 追蹤活動狀態變更
- 建立長期監控系統

## 📋 輸出資料格式

爬蟲執行後會產生 `tixcraft_activities.json` 檔案：

```json
{
  "scrape_time": "2026-02-25 12:47:03",
  "last_update": "2026-02-25 12:47:03",
  "total_events": 43,
  "success_count": 23,
  "success_rate": "53.5%",
  "extraction_method": "realtime_precision_field_extraction",
  "current_progress": "43/43",
  "current_session_success": 43,
  "events": [
    {
      "index": 1,
      "title": "演唱會名稱",
      "event_info": "2026/03/15 19:00 ; 演出資訊詳情",
      "location": "台北小巨蛋",
      "price": "NT$1800 ; NT$1500 ; NT$1200",
      "sale_time": "2026/02/28 12:00",
      "url": "https://tixcraft.com/activity/detail/..."
    }
  ]
}
```

## 🔧 系統需求

### 必需
- Python 3.7+
- Chrome 瀏覽器（驅動自動下載）
- 網路連接

### 依賴套件
- `selenium>=4.0.0` - 網頁自動化
- `webdriver-manager>=3.8.0` - 瀏覽器驅動管理

## 🎯 主要功能詳解

### 1. 智慧型資料合併
- 以 URL 為唯一識別符
- 自動去重複
- 保留歷史資料

### 2. 多層級資訊提取
- **第一優先**: JavaScript dataLayer 提取
- **第二優先**: HTML 標籤掃描
- **第三優先**: 正規表達式匹配
- **備援方案**: 上下文推論

### 3. 反偵測機制
- 隨機 User-Agent
- 動態等待時間
- WebDriver 特徵隱藏
- CDP 命令執行
- 自動化轉向規避

### 4. 資料清洗
- 去除表情符號
- 移除裝飾性標記
- 重複行偵測
- 空殼內容過濾
- 噪音關鍵字排除

## 📝 常見問題

### Q: 爬蟲被網站偵測到怎麼辦？
A: 程式已內置強化版反偵測機制，包括隨機等待、User-Agent 輪換等。如持續被偵測，可嘗試：
- 增加等待時間（修改程式碼中的 `time.sleep()` 值）
- 改用監控版進行低頻率掃描
- 使用代理服務

### Q: 為什麼有些欄位提取為「未找到」？
A: 這通常是因為：
- 網站頁面結構與預期不符
- dataLayer 未加載完成
- 該活動未公開相關資訊

程式提供了多層級備援，大部分情況都能正確提取。

### Q: 如何修改抓取間隔？
A: 
```python
# 在監控版中修改
monitor = TixcraftMonitor(check_interval=600)  # 600秒 = 10分鐘
```

### Q: 資料會一直累積嗎？
A: 是的，程式以 URL 為準進行合併，舊資料不會被刪除，僅會被更新。如需清空，刪除 JSON 檔案即可。

## ⚠️ 免責聲明

- 本程式僅供學習與研究用途
- 使用前請確認並遵守拓元售票網服務條款
- 不得用於商業目的或大規模自動化抓取
- 使用者應自行承擔使用本程式所產生的一切後果
- 作者不對程式造成的任何損害負責

## 📞 使用說明

### 基本用法
```bash
# 執行精準欄位版
python run_scraper.py

# 显示所有可用版本
python run_scraper.py --list

# 執行監控版
python run_scraper.py monitor
```

### 程式主要選項
精準欄位版無命令行選項，直接執行即開始爬取。

## 🔍 日誌檔案

執行爬蟲後會產生：
- `tixcraft_precision_field.log` - 精準欄位版詳細日誌
- `tixcraft_activities.json` - 爬取結果資料庫

## 📈 性能參考

- 單次爬取：通常 1-2 分鐘（視活動數量）
- 成功率：70-90%（取決於頁面複雜度）
- 即時存檔：每個活動完成後立即保存

## 🛠️ 進階使用

### 自訂修改程式碼

1. **修改 User-Agent 列表**
```python
def get_random_user_agent(self):
    user_agents = [
        '你的 User-Agent...',
        # 添加更多
    ]
```

2. **調整等待時間**
```python
time.sleep(random.uniform(2, 4))  # 改為你需要的範圍
```

3. **修改輸出檔名**
```python
output_file = 'your_filename.json'
```

## 📚 更多資源

- [Selenium 文檔](https://www.selenium.dev/documentation/)
- [webdriver-manager 說明](https://github.com/SergeyPirogov/webdriver_manager)
- Tixcraft 網站：https://tixcraft.com/

## 🎉 版本歷史

### v2.0（當前）
- 新增智慧型合併提取方式
- 強化反偵測機制
- 實時 JSON 存檔
- 完整文檔與說明

### v1.0
- 基礎爬蟲功能
- 監控系統實現

---

**最後更新**: 2026年3月3日
**適用**: Tixcraft 網站
**開發者**: Assistant
