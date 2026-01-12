# 演唱會通知助手 🎵

一個完整的演唱會爬蟲系統，包含用戶認證、演唱會列表、關注功能和售票提醒。

## 功能特性

### 前端 (React Native Expo)
- **用戶認證**
  - 註冊新賬戶
  - 郵箱 + 密碼登入
  - 登出

- **演唱會列表**
  - 瀏覽所有爬蟲數據中的演唱會
  - 搜尋功能（按藝人名稱或地點）
  - 按標籤頁切換（所有演唱會 / 我的關注）

- **關注功能** ⭐
  - 關注喜歡的演唱會
  - 查看關注列表
  - 一鍵取消關注

- **售票提醒** 🔔
  - 為關注的演唱會設置提醒
  - 支援多種提醒類型：售票時、演唱會前一天
  - 管理提醒設置

- **詳細信息**
  - 查看演唱會完整資訊（時間、地點、來源、購票連結）
  - 直接跳轉到購票網站

### 後端 (Flask API)
- **RESTful API 端點**
  - 用戶認證：註冊、登入、登出
  - 演唱會管理：取得列表、搜尋、過濾
  - 關注管理：新增、移除、查詢關注狀態
  - 提醒管理：建立、刪除、查詢提醒

- **數據持久化**
  - JSON 檔案存儲
  - 自動創建必要的目錄和文件

- **安全性**
  - Werkzeug 密碼雜湊
  - Session 管理
  - CORS 支援

## 系統架構

```
演唱會爬蟲系統
├── 爬蟲層 (concert_crawler.py)
│   └── 爬取 KKTIX、Indievox、年代售票的演唱會數據
│
├── 後端 API (app.py)
│   ├── /api/auth/* - 用戶認證
│   ├── /api/concerts/* - 演唱會數據
│   ├── /api/follows/* - 關注管理
│   └── /api/reminders/* - 提醒管理
│
└── 前端應用 (mobile_ui/)
    ├── App.js - 主應用組件
    └── 登入屏幕 / 演唱會列表屏幕
```

## 快速開始

### 1. 安裝依賴

#### 後端依賴
```bash
pip install -r requirements.txt
```

#### 前端依賴（可選，在 mobile_ui 目錄）
```bash
cd mobile_ui
npm install
# 或
yarn install
```

### 2. 爬取數據

運行爬蟲獲取最新演唱會數據：
```bash
python concert_crawler.py --format json
```

### 3. 啟動後端 API

```bash
python app.py
```

API 將在 `http://localhost:5000` 運行

### 4. 啟動前端應用

#### 使用 Expo
```bash
cd mobile_ui
npm start
# 掃描 QR code 用 Expo Go 開啟
```

#### 選項
```bash
# Android 模擬器
npm run android

# iOS 模擬器
npm run ios

# Web 版本
npm run web
```

## API 端點詳細說明

### 認證 (Authentication)

**POST /api/auth/register**
```json
{
  "username": "用戶名",
  "email": "user@example.com",
  "password": "密碼"
}
```

**POST /api/auth/login**
```json
{
  "email": "user@example.com",
  "password": "密碼"
}
```

**POST /api/auth/logout**
- 登出當前用戶

**GET /api/auth/profile**
- 獲取當前用戶資訊

**PUT /api/auth/profile**
```json
{
  "preferences": {
    "genres": ["搖滾", "爵士"],
    "venues": ["小巨蛋"],
    "notification_enabled": true
  }
}
```

### 演唱會 (Concerts)

**GET /api/concerts**
- 查詢參數：
  - `q` - 搜尋關鍵詞
  - `venue` - 地點過濾
  - `artist` - 藝人過濾

**GET /api/concerts/<concert_id>**
- 獲取單個演唱會詳細資訊

### 關注 (Follows)

**GET /api/follows**
- 獲取當前用戶的關注列表

**POST /api/follows/<concert_id>**
- 關注一個演唱會

**DELETE /api/follows/<concert_id>**
- 取消關注

**GET /api/follows/<concert_id>/check**
- 檢查是否已關注該演唱會

### 提醒 (Reminders)

**GET /api/reminders**
- 獲取所有提醒設置

**POST /api/reminders/<concert_id>**
```json
{
  "type": "on_sale"  // 或 "one_day_before"
}
```

**DELETE /api/reminders/<concert_id>**
- 刪除提醒

## 數據結構

### 演唱會數據
```json
{
  "id": "演唱會ID",
  "來源網站": "KKTIX",
  "演出藝人": "五月天",
  "演出時間": "2026-02-15",
  "演出地點": "台北小巨蛋",
  "網址": "https://...",
  "爬取時間": "2026-01-12 14:30:00"
}
```

### 用戶數據
```json
{
  "user_id": "uuid",
  "username": "用戶名",
  "email": "user@example.com",
  "password": "哈希密碼",
  "created_at": "2026-01-12T14:30:00",
  "preferences": {
    "genres": [],
    "venues": [],
    "artists": [],
    "notification_enabled": true
  }
}
```

## 文件結構

```
jr/
├── concert_crawler.py      # 爬蟲主程序
├── app.py                  # Flask 後端 API
├── requirements.txt        # Python 依賴
├── kktix_state.json       # 爬蟲狀態文件
├── README.md              # 本文件
├── ticket_sites_list.py   # 售票網站配置
├── mobile_ui/             # React Native 應用
│   ├── App.js            # 主應用組件
│   ├── app.json          # Expo 配置
│   ├── package.json      # npm 依賴
│   └── babel.config.js   # Babel 配置
└── data/                  # 運行時創建
    ├── users.json        # 用戶數據
    ├── concerts.json     # 演唱會數據
    ├── follows.json      # 關注記錄
    └── reminders.json    # 提醒設置
```

## 開發指南

### 添加新的爬蟲源

在 `concert_crawler.py` 中繼承 `ConcertCrawler` 類：

```python
class NewSiteCrawler(ConcertCrawler):
    def __init__(self):
        super().__init__()
        self.base_url = "https://new-site.com"
        self.site_name = "新網站"
    
    def crawl(self) -> List[dict]:
        # 實現爬蟲邏輯
        return self.concerts
```

### 自定義提醒類型

在 API 中修改 `POST /api/reminders/<concert_id>`：

```python
reminder_types = {
    "on_sale": "售票開始時",
    "one_day_before": "演唱會前一天",
    "one_week_before": "演唱會前一週"
}
```

## 故障排除

### API 連接失敗
- 確保 Flask 後端正在運行：`python app.py`
- 檢查 API 基礎 URL 配置（App.js 中的 `API_BASE_URL`）
- 如果在真機上運行，使用電腦 IP 地址而非 `localhost`

### 爬蟲數據為空
- 檢查網站是否有反爬蟲機制
- 嘗試運行 `python concert_crawler.py` 測試
- 查看控制台輸出了解具體錯誤

### 登入問題
- 確認郵箱和密碼沒有拼寫錯誤
- 檢查 `data/users.json` 是否包含用戶記錄
- 清除 app session 後重試

## 未來規劃

- [ ] 推送通知 (Firebase Cloud Messaging)
- [ ] 票價監控
- [ ] AI 推薦演唱會
- [ ] 社交分享功能
- [ ] 票根收集功能
- [ ] 數據庫遷移 (SQLite/PostgreSQL)
- [ ] 前端優化和動畫

---

**更新時間**: 2026年1月12日
