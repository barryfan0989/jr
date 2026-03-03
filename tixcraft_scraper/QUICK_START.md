# ⚡ 快速開始指南 (5 分鐘上手)

## 💻 安裝步驟

### Windows 用戶

```powershell
# 1. 進入資料夾
cd tixcraft_scraper

# 2. 建立虛擬環境
python -m venv venv

# 3. 啟動虛擬環境
.\venv\Scripts\activate

# 4. 安裝依賴
pip install -r requirements.txt

# 5. 執行爬蟲
python run_scraper.py
```

### macOS/Linux 用戶

```bash
# 1. 進入資料夾
cd tixcraft_scraper

# 2. 建立虛擬環境
python3 -m venv venv

# 3. 啟動虛擬環境
source venv/bin/activate

# 4. 安裝依賴
pip3 install -r requirements.txt

# 5. 執行爬蟲
python3 run_scraper.py
```

## 🎬 執行爬蟲

### 最簡單的方式
```bash
python run_scraper.py
```

程式會自動：
1. ✅ 啟動 Chrome 瀏覽器
2. ✅ 訪問拓元售票網
3. ✅ 抓取所有活動資訊
4. ✅ 儲存為 JSON 檔案
5. ✅ 即時更新進度

### 選擇不同版本
```bash
# 精準欄位版（推薦）- 預設執行
python run_scraper.py

# 或明確指定
python run_scraper.py precision-field

# 監控版
python run_scraper.py monitor

# 查看所有版本
python run_scraper.py --list
```

## 📊 執行完成後

程式會生成 `tixcraft_activities.json` 檔案，內容如下：

```json
{
  "total_events": 45,
  "success_count": 38,
  "success_rate": "84.4%",
  "events": [
    {
      "title": "演唱會名稱",
      "event_info": "2026/03/15 19:00",
      "location": "台北小巨蛋",
      "price": "NT$1500",
      "sale_time": "2026/02/28 10:00",
      "url": "https://tixcraft.com/..."
    }
  ]
}
```

## 🔧 故障排除

### ❌ 無法安裝依賴
```bash
# 升級 pip
python -m pip install --upgrade pip

# 重試安裝
pip install -r requirements.txt
```

### ❌ 無法找到 Chrome
程式會自動下載適配你 Chrome 版本的驅動。如仍有問題：
1. 確认已安装 Chrome 浏览器
2. 手動下載：https://chromedriver.chromium.org/

### ❌ 爬蟲一直停止
- 檢查網路連接
- 等幾分鐘後重試（可能被暫時限制）
- 檢查 `tixcraft_precision_field.log` 日誌文件

### ❌ 某些欄位為「未找到」
這是正常的，表示頁面未提供該資訊。程式設計上會嘗試多種方法提取，但某些欄位確實可能不存在。

## 📱 預期輸出

#### 運行時
```
🎯 找到 45 個活動，開始即時處理...
處理活動 1：https://tixcraft.com/activity/detail/...
💾 已同步至 JSON 檔案，目前進度：1/45 (2.2%)
```

#### 完成時
```
🎉 所有活動處理完成！
📈 本次工作階段成功處理：43/45 個活動
📂 最終資料庫包含：89 個活動
```

## 💡 常見問題

**Q: 爬蟲需要多長時間？**
A: 約 1-3 分鐘（取決於活動數量，每個活動 2-4 秒）

**Q: 可以在後台執行嗎？**
A: 可以，但目前程式需要 Chrome 視窗可見（反偵測要求）

**Q: JSON 檔案可以用什麼打開？**
A: VS Code、任何文字編輯器、線上 JSON 檢視器、Excel（需轉換）

**Q: 可以多台電腦同時運行嗎？**
A: 可以，但建議使用不同的輸出檔案名（修改程式碼）

## 🚀 進階使用

### 定期自動運行（Windows 工作排程器）
```bash
# 建立批次檔 run_daily.bat
@echo off
cd /d "C:\path\to\tixcraft_scraper"
call venv\Scripts\activate.bat
python run_scraper.py
pause
```

然後在 Windows 工作排程器中設定每天執行。

### 監控模式（持續掃描）
```bash
python run_scraper.py monitor
```

將每 10 分鐘檢查一次新活動。

## ✅ 確認成功的標誌

1. ✅ Chrome 瀏覽器自動啟動
2. ✅ 看見「找到 X 個活動」訊息
3. ✅ 進度條逐漸增加
4. ✅ 完成後顯示統計資訊
5. ✅ 生成 `tixcraft_activities.json` 檔案

## 📞 需要幫助？

1. 檢查 `tixcraft_precision_field.log` 日誌
2. 檢查網路連接
3. 確認 Chrome 瀏覽器已安裝
4. 嘗試重新啟動程式

---

**祝你使用愉快！** 🎉
