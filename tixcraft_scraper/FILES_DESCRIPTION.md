# 📂 檔案與資料夾說明

## 目錄結構

```
tixcraft_scraper/          # 爬蟲專案主資料夾
│
├── tixcraft_precision_field_scraper.py    # 📌 主要爬蟲程式（推薦使用）
│   └── 功能：精準欄位提取、JS監控、反偵測、即時存檔
│
├── tixcraft_monitor.py                     # 🔄 監控工具
│   └── 功能：持續監控新活動、狀態追蹤、本地資料庫
│
├── run_scraper.py                          # 🚀 統一啟動器
│   └── 功能：命令行介面、版本選擇、幫助資訊
│
├── requirements.txt                        # 📦 Python 依賴清單
│   └── selenium>=4.0.0
│       webdriver-manager>=3.8.0
│
├── README.md                               # 📘 完整使用說明
├── QUICK_START.md                          # ⚡ 快速開始
└── FILES_DESCRIPTION.md                    # 📄 本檔案

```

## 📌 主要檔案詳解

### 1. tixcraft_precision_field_scraper.py（推薦）

**用途**: 主要爬蟲程式，提供精準的欄位提取

**主要方法**:
- `TixcraftPrecisionFieldScraper()` - 初始化爬蟲
- `setup_driver()` - 啟動反偵測瀏覽器
- `scrape_all_events()` - 爬取所有活動
- `process_single_event()` - 處理單一活動
- 各式欄位提取方法（標題、日期、地點、票價等）

**輸出**: `tixcraft_activities.json`

**執行方式**:
```bash
python tixcraft_precision_field_scraper.py
# 或通過啟動器
python run_scraper.py precision-field
# 或預設
python run_scraper.py
```

---

### 2. tixcraft_monitor.py

**用途**: 實時監控爬蟲，適合長期追蹤新活動

**主要方法**:
- `TixcraftMonitor()` - 初始化監控器
- `monitor_loop()` - 持續監控（設定間隔）
- `run_single_scan()` - 單次掃描

**特點**:
- 可設定掃描間隔（預設 10 分鐘）
- 自動偵測新活動
- 追蹤活動狀態變更
- 本地資料庫管理

**執行方式**:
```bash
python tixcraft_monitor.py
# 或通過啟動器
python run_scraper.py monitor
```

---

### 3. run_scraper.py

**用途**: 統一啟動器，管理多個爬蟲版本

**命令**:
```bash
python run_scraper.py                    # 執行預設（精準欄位版）
python run_scraper.py precision-field   # 執行精準欄位版
python run_scraper.py monitor           # 執行監控版
python run_scraper.py --list            # 列出所有可用版本
```

**程式碼註冊新版本**:
```python
SCRIPT_MAP: dict[str, tuple[str, str]] = {
    "precision-field": ("tixcraft_precision_field_scraper", "描述"),
    # 添加新版本...
}
```

---

### 4. requirements.txt

**用途**: Python 環境依賴清單

**內容**:
```
selenium>=4.0.0
webdriver-manager>=3.8.0
```

**安裝**:
```bash
pip install -r requirements.txt
```

---

## 📊 資料流程

```
1. 使用者執行爬蟲
   └─> run_scraper.py (直接執行或通過它)
       │
       ├─> tixcraft_precision_field_scraper.py (精準欄位版)
       │   └─> 抓取所有活動資訊
       │       └─> 生成 tixcraft_activities.json
       │
       └─> tixcraft_monitor.py (監控版)
           └─> 循環掃描
               └─> 更新資料庫
```

## 🔄 資料輸出

所有版本都會生成 `tixcraft_activities.json`:

```json
{
  "scrape_time": "2026-03-03 10:30:00",
  "last_update": "2026-03-03 10:30:00",
  "total_events": 45,
  "success_count": 38,
  "success_rate": "84.4%",
  "extraction_method": "realtime_precision_field_extraction",
  "events": [
    {
      "index": 1,
      "title": "演唱會名稱",
      "event_info": "2026/03/15 19:00 ; 演出資訊",
      "location": "台北小巨蛋",
      "price": "NT$1500 ; NT$1200",
      "sale_time": "2026/02/28 10:00",
      "url": "https://tixcraft.com/activity/detail/..."
    },
    // ... 更多活動
  ]
}
```

## 📚 文檔說明

| 檔案 | 內容 | 適合誰 |
|-----|------|-------|
| README.md | 完整功能介紹、進階使用 | 想深入了解的開發者 |
| QUICK_START.md | 5分鐘快速上手 | 急著開始的使用者 |
| FILES_DESCRIPTION.md | 本檔案，詳細檔案說明 | 想理解專案結構的人 |

## 🔧 整合到其他專案

### 方法 1: 複製整個資料夾
```bash
# 將 tixcraft_scraper 資料夾複製到你的專案
cp -r tixcraft_scraper /path/to/your/project/
```

### 方法 2: 作為模組匯入
```python
# 在你的 Python 檔案中
import sys
sys.path.insert(0, '/path/to/tixcraft_scraper')

from tixcraft_precision_field_scraper import TixcraftPrecisionFieldScraper

scraper = TixcraftPrecisionFieldScraper()
result = scraper.scrape_all_events()
```

### 方法 3: 透過命令列呼叫
```python
import subprocess
import json

result = subprocess.run(
    ['python', 'tixcraft_scraper/run_scraper.py'],
    capture_output=True,
    text=True
)

# 讀取生成的 JSON
with open('tixcraft_activities.json', 'r') as f:
    data = json.load(f)
```

## 📝 日誌檔案

執行後會生成:

**tixcraft_precision_field.log**
```
2026-03-03 10:30:00 - INFO - 成功載入現有資料：2 個活動
2026-03-03 10:30:01 - INFO - 找到 43 個活動，開始即時處理...
2026-03-03 10:30:02 - INFO - 處理活動 1：https://tixcraft.com/...
...
```

檢查此日誌可了解程式執行詳情與錯誤。

## 🎯 常見修改

### 修改輸出路徑
在爬蟲程式中找到：
```python
output_file = 'tixcraft_activities.json'
# 改為
output_file = '/path/to/your/output.json'
```

### 修改等待時間
```python
time.sleep(random.uniform(2, 4))  # 修改此數字
```

### 修改監控間隔
```python
monitor = TixcraftMonitor(check_interval=600)  # 單位：秒
```

## 🔐 安全注意事項

1. 爬蟲會下載 Chrome 驅動 (~200MB)
2. 建議在虛擬環境中執行
3. 第一次運行較慢（下載驅動 + 首次爬取）
4. 後續運行會快得多（驅動已下載）

## 📌 版本相容性

- Python: 3.7+
- Selenium: 4.0+
- webdriver-manager: 3.8+
- 系統：Windows, macOS, Linux

---

**更新日期**: 2026年3月3日
**版本**: 2.0
