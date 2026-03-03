# 📦 Tixcraft 爬蟲專案 - 完整資料夾

## ✅ 資料夾已準備完成！

你現在擁有一個完整組織的 Tixcraft 拓元售票網爬蟲專案，可以直接複製到任何地方使用。

## 📋 資料夾內容清單

```
tixcraft_scraper/
├── 📜 程式檔案（可直接執行）
│   ├── tixcraft_precision_field_scraper.py  [53 KB] ⭐ 主要爬蟲
│   ├── tixcraft_monitor.py                   [17 KB] 監控工具
│   ├── run_scraper.py                        [2 KB]  啟動器
│   └── requirements.txt                      [41 B]  依賴清單
│
└── 📚 說明文檔（詳細使用指南）
    ├── README.md                             [6.6 KB] 完整功能說明
    ├── QUICK_START.md                        [4 KB]   5分鐘快速開始
    ├── FILES_DESCRIPTION.md                  [6.3 KB] 檔案詳細說明
    ├── SETUP_AND_INTEGRATION.md              [7.5 KB] 安裝與整合指南
    └── 📄 MANIFEST.md                        [本檔案] 資料夾清單
```

## 🎯 快速開始（3 步驟）

### 1️⃣ 複製資料夾到你的專案

Windows:
```powershell
Copy-Item -Path "tixcraft_scraper" -Destination "你的專案路徑" -Recurse
```

macOS/Linux:
```bash
cp -r tixcraft_scraper /path/to/your/project/
```

### 2️⃣ 安裝依賴

```bash
cd tixcraft_scraper
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### 3️⃣ 執行爬蟲

```bash
python run_scraper.py
```

完成! 爬蟲會自動爬取資料並生成 `tixcraft_activities.json`

## 📖 文檔導覽

| 檔案 | 內容 | 閱讀時間 | 適合 |
|------|------|---------|------|
| **QUICK_START.md** | 立即開始使用 | 5 分鐘 | 想快速試用的人 |
| **README.md** | 完整功能介紹 | 15 分鐘 | 想深入了解的人 |
| **FILES_DESCRIPTION.md** | 各檔案詳細說明 | 10 分鐘 | 想理解結構的人 |
| **SETUP_AND_INTEGRATION.md** | 如何整合到專案 | 15 分鐘 | 想整合到自己專案的人 |

## 🚀 可用功能

### 1. 精準欄位爬蟲 ⭐（推薦）
```bash
python run_scraper.py
# 或
python run_scraper.py precision-field
```
**特點**:
- ✅ 智慧型日期時間提取
- ✅ 多層級地點識別
- ✅ 完整票價蒐集
- ✅ 反偵測機制
- ✅ 即時 JSON 存檔
- ✅ 自動去重複

### 2. 實時監控爬蟲
```bash
python run_scraper.py monitor
```
**特點**:
- 🔄 持續監控新活動
- 📊 狀態變更追蹤
- 💾 本地資料庫
- ⏰ 可自訂間隔

### 3. 見所有版本
```bash
python run_scraper.py --list
```

## 📊 輸出資料範例

爬蟲生成的 `tixcraft_activities.json`:

```json
{
  "total_events": 45,
  "success_rate": "84.4%",
  "events": [
    {
      "title": "演唱會名稱",
      "event_info": "2026/03/15 19:00",
      "location": "台北小巨蛋",
      "price": "NT$1500 ; NT$1200",
      "sale_time": "2026/02/28 10:00",
      "url": "https://tixcraft.com/..."
    }
  ]
}
```

## 💡 使用場景

1. **單次爬取**: 爬取當前所有活動
   ```bash
   python run_scraper.py
   ```

2. **定期監控**: 每天自動爬取新活動
   ```bash
   # Windows: 設定工作排程器
   # 或使用 cron (Linux/macOS)
   ```

3. **集成到應用**: 在你的 Python 程式中呼叫
   ```python
   from tixcraft_precision_field_scraper import TixcraftPrecisionFieldScraper
   scraper = TixcraftPrecisionFieldScraper()
   result = scraper.scrape_all_events()
   ```

4. **建立 API**: 提供爬蟲資料給前端
   ```python
   # Flask, FastAPI, Django 等框架
   ```

## 🔒 系統要求

- ✅ Python 3.7+
- ✅ Chrome 瀏覽器（自動下載驅動）
- ✅ 網路連接
- ✅ ~200 MB 磁碟空間（Chrome 驅動）

## 📌 重要特性

### 智慧資料合併
- 自動去重複（以 URL 為準）
- 保留歷史資料
- 增量更新

### 強化反偵測
- 隨機 User-Agent
- 動態等待時間
- WebDriver 特徵隱藏
- 自動化規避

### 多層級備援
- JavaScript 優先提取
- HTML 標籤掃描
- 正規表達式匹配
- 上下文推論

### 自動清洗
- 去除表情符號
- 移除裝飾標記
- 重複內容偵測
- 噪音過濾

## 📞 需要幫助？

1. **快速問題** → 見 [QUICK_START.md](QUICK_START.md)
2. **功能說明** → 見 [README.md](README.md)
3. **檔案詳解** → 見 [FILES_DESCRIPTION.md](FILES_DESCRIPTION.md)
4. **整合指南** → 見 [SETUP_AND_INTEGRATION.md](SETUP_AND_INTEGRATION.md)

## ⚠️ 免責聲明

本專案僅供學習與研究用途。使用者應：
- ✅ 遵守拓元售票網服務條款
- ✅ 不用於商業目的
- ✅ 合理使用頻率（避免伺服器壓力）
- ✅ 自行承擔使用後果

## 📈 預期效能

- ⏱️ 執行時間: 1-3 分鐘（視活動數量）
- 📊 成功率: 70-90%
- 💾 資料大小: ~50-100 KB (JSON)
- 🔄 增量更新: <1 分鐘

## 🎉 現在就開始！

```bash
# 進入資料夾
cd tixcraft_scraper

# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境（Windows）
venv\Scripts\activate
# 或 macOS/Linux
# source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 執行爬蟲
python run_scraper.py
```

## 📚 檔案清單

| 檔案 | 大小 | 用途 |
|------|------|------|
| tixcraft_precision_field_scraper.py | 53 KB | ⭐ 主要爬蟲 |
| tixcraft_monitor.py | 17 KB | 監控工具 |
| run_scraper.py | 2 KB | 啟動器 |
| requirements.txt | 41 B | 依賴清單 |
| README.md | 6.6 KB | 完整說明 |
| QUICK_START.md | 4 KB | 快速開始 |
| FILES_DESCRIPTION.md | 6.3 KB | 檔案詳解 |
| SETUP_AND_INTEGRATION.md | 7.5 KB | 整合指南 |

**總大小**: ~100 KB（不含 venv）

---

## ✅ 最後檢查清單

爬蟲資料夾已準備完成，請確認：

- [ ] 所有 8 個檔案都在 `tixcraft_scraper/` 中
- [ ] 可以看到 `README.md` 檔案（700+ 行）
- [ ] 可以看到 `tixcraft_precision_field_scraper.py`（1000+ 行）
- [ ] `requirements.txt` 包含 selenium 和 webdriver-manager
- [ ] 所有說明文檔都已生成

完成後，你可以：
1. ✅ 整個資料夾複製到任何地方
2. ✅ 跟著 QUICK_START.md 安裝執行
3. ✅ 在你的專案中使用這個爬蟲

**祝你使用愉快！** 🎉

---

**更新日期**: 2026-03-03
**版本**: 2.0
**狀態**: ✅ 完全就緒

下一步：閱讀 `QUICK_START.md` 開始使用！
