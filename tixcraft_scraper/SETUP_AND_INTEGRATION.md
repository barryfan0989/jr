# 🔧 安裝與整合指南

本文檔說明如何將 Tixcraft 爬蟲資料夾複製到你的專案中使用。

## 📦 複製資料夾到你的專案

### 第一步：確認資料夾內容

確保 `tixcraft_scraper` 資料夾包含以下檔案：

```
✓ tixcraft_precision_field_scraper.py
✓ tixcraft_monitor.py
✓ run_scraper.py
✓ requirements.txt
✓ README.md
✓ QUICK_START.md
✓ FILES_DESCRIPTION.md
```

### 第二步：複製資料夾

#### Window 用戶（資源管理器）
1. 右鍵點擊 `tixcraft_scraper` 資料夾
2. 選擇「複製」
3. 進入你的專案資料夾
4. 右鍵點擊，選擇「貼上」

#### Windows 用戶（PowerShell）
```powershell
# 假設原位置是 C:\Users\USER\Documents\GitHub\VVV\tixcraft_scraper
# 要複製到 D:\MyProject

Copy-Item -Path "C:\Users\USER\Documents\GitHub\VVV\tixcraft_scraper" -Destination "D:\MyProject\" -Recurse
```

#### macOS/Linux 用戶
```bash
# 複製資料夾
cp -r /path/to/tixcraft_scraper /path/to/your/project/

# 或使用完整專案複製
rsync -av /path/to/tixcraft_scraper/ /path/to/your/project/tixcraft_scraper/
```

## 🚀 在你的專案中執行

### 方法 1: 直接執行（最簡單）

```bash
# 進入爬蟲資料夾
cd your_project/tixcraft_scraper

# 建立虛擬環境（首次）
python -m venv venv

# 啟動虛擬環境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 執行爬蟲
python run_scraper.py
```

### 方法 2: 在 Python 中呼叫

如果你想在自己的 Python 程式中使用爬蟲：

```python
# your_project/main.py
import sys
import json
from pathlib import Path

# 添加爬蟲資料夾到 Python 路徑
scraper_path = Path(__file__).parent / 'tixcraft_scraper'
sys.path.insert(0, str(scraper_path))

from tixcraft_precision_field_scraper import TixcraftPrecisionFieldScraper

# 執行爬蟲
scraper = TixcraftPrecisionFieldScraper()
result = scraper.scrape_all_events()

# 讀取結果
if result:
    print(f"成功爬取 {result['total_events']} 個活動")
    
    # 使用爬取的資料
    for event in result['events'][:5]:  # 前5個
        print(f"{event['title']} - {event['location']}")
```

### 方法 3: 作為子程序執行

```python
# your_project/main.py
import subprocess
import json
import os

# 執行爬蟲程式
os.chdir('tixcraft_scraper')
subprocess.run(['python', 'run_scraper.py'])

# 讀取生成的 JSON
with open('tixcraft_activities.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"總共爬取: {data['total_events']} 個活動")
```

## 📁 建議的專案結構

```
your_project/
├── main.py                    # 你的主程式
├── config.py                  # 配置檔案
├── requirements.txt           # 你的依賴
│
├── tixcraft_scraper/          # 複製過來的爬蟲資料夾
│   ├── tixcraft_precision_field_scraper.py
│   ├── tixcraft_monitor.py
│   ├── run_scraper.py
│   ├── requirements.txt
│   └── README.md
│
├── utils/                     # 你的工具函式
│   ├── data_processor.py
│   └── api_handler.py
│
└── output/                    # 爬蟲輸出資料夾
    └── tixcraft_activities.json
```

## 🔗 統一依賴管理

如果你的專案已有 `requirements.txt`，可以這樣合併：

```bash
# your_project/requirements.txt 應該包含
selenium>=4.0.0
webdriver-manager>=3.8.0

# 加上你自己的依賴
requests>=2.25.0
pandas>=1.3.0
```

然後一次性安裝所有：
```bash
pip install -r requirements.txt
```

## 🎯 常見整合場景

### 場景 1: 網頁應用中整合

```python
# Flask 應用
from flask import Flask, jsonify
import subprocess

app = Flask(__name__)

@app.route('/api/scrape', methods=['POST'])
def trigger_scrape():
    """觸發爬蟲"""
    result = subprocess.run(
        ['python', 'tixcraft_scraper/run_scraper.py'],
        capture_output=True,
        cwd='/path/to/project'
    )
    
    # 讀取結果
    import json
    with open('tixcraft_scraper/tixcraft_activities.json') as f:
        data = json.load(f)
    
    return jsonify(data)

@app.route('/api/activities', methods=['GET'])
def get_activities():
    """獲取爬取結果"""
    import json
    with open('tixcraft_scraper/tixcraft_activities.json') as f:
        data = json.load(f)
    return jsonify(data['events'])
```

### 場景 2: 定期排程任務

```python
# 使用 APScheduler 或 Celery
from apscheduler.schedulers.background import BackgroundScheduler
import subprocess

def scheduled_scrape():
    """定期執行爬蟲"""
    subprocess.run(['python', 'tixcraft_scraper/run_scraper.py'])

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_scrape, 'cron', hour=2)  # 每天凌晨2點
scheduler.start()
```

### 場景 3: 資料處理管道

```python
# 爬蟲 -> 處理 -> 存儲 -> API
import json
from tixcraft_scraper.tixcraft_precision_field_scraper import TixcraftPrecisionFieldScraper

# 1. 執行爬蟲
scraper = TixcraftPrecisionFieldScraper()
raw_data = scraper.scrape_all_events()

# 2. 資料處理
processed_events = []
for event in raw_data['events']:
    processed_event = {
        'id': event['url'].split('/')[-1],
        'title': event['title'].strip(),
        'date': parse_date(event['event_info']),
        'location': event['location'],
        'prices': parse_prices(event['price']),
    }
    processed_events.append(processed_event)

# 3. 由你的程式儲存到資料庫或 API
save_to_database(processed_events)
```

## ⚠️ 注意事項

### 1. 檔案位置
爬蟲會在執行目錄生成 `tixcraft_activities.json`，確保有寫入權限。

### 2. Chrome 驅動
首次執行會自動下載 Chrome 驅動 (~200MB)，請確保：
- 有足夠磁碟空間
- 網路連接穩定
- 有足夠時間等待

### 3. 虛擬環境
建議每個專案使用獨立虛擬環境：
```bash
# 在爬蟲資料夾內建立
python -m venv venv
```

### 4. 相對路徑
如果在整合中遇到路徑問題，使用相對路徑：
```python
from pathlib import Path
scraper_dir = Path(__file__).parent / 'tixcraft_scraper'
```

## 🔄 更新爬蟲

當爬蟲有更新時：

```bash
# 備份你的資料
cp -r tixcraft_scraper tixcraft_scraper.backup

# 用新版本替換程式檔案（保留 venv）
# 刪除舊的爬蟲程式
rm -rf tixcraft_scraper/*.py

# 複製新的程式檔案
cp /path/to/new/tixcraft_scraper/*.py tixcraft_scraper/

# 更新依賴（如有變更）
pip install -r tixcraft_scraper/requirements.txt
```

## 🚨 故障排除

### 問題：ModuleNotFoundError
```python
# 確保路徑正確
sys.path.insert(0, str(Path(__file__).parent / 'tixcraft_scraper'))
```

### 問題：Chrome 驅動版本不符
```bash
# 清除快取，重新下載
rm -rf ~/.wdm/  # macOS/Linux
# 或在 Windows 中刪除 C:\Users\USERNAME\.wdm\
```

### 問題：授權問題
```bash
# 確保檔案可執行
chmod +x tixcraft_scraper/*.py

# 或在 Windows 使用管理員模式
```

## 📚 相關資源

- [完整使用說明](README.md)
- [快速開始](QUICK_START.md)
- [檔案詳解](FILES_DESCRIPTION.md)

---

**安裝完成？** 現在你可以執行 `python run_scraper.py` 開始爬取資料了！
