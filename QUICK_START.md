# 🎵 演唱會通知助手 - 快速參考

## 🚀 一分鐘啟動

### Windows
```bash
cd c:\Users\USER\Documents\GitHub\jr
start.bat
```

### macOS/Linux
```bash
cd ~/Documents/GitHub/jr
bash start.sh
```

---

## 📱 UI 畫面快覽

### 登入屏幕
```
┌──────────────────────────┐
│   演唱會通知助手          │
│   找到你的下一場演出       │
├──────────────────────────┤
│   📧 郵箱欄              │
│   🔐 密碼欄              │
│   [登入]                 │
│   還沒有賬戶？點擊註冊   │
└──────────────────────────┘
```

### 演唱會列表
```
┌──────────────────────────┐
│ 歡迎, John! 👋    [登出] │
├─[所有演唱會]  [我的關注]─┤
│ [🔍 搜尋演唱會...]       │
├──────────────────────────┤
│ ┌────────────────────┐   │
│ │ 五月天             │   │
│ │ 📅 2026-02-15     │   │
│ │ 📍 台北小巨蛋     │   │
│ │ KKTIX   [★] [🔔] │   │
│ └────────────────────┘   │
│ ┌────────────────────┐   │
│ │ Coldplay           │   │
│ │ 📅 2026-03-20     │   │
│ │ 📍 台北南港展覽館  │   │
│ │ Indievox [☆] [🔕] │   │
│ └────────────────────┘   │
└──────────────────────────┘
```

### 詳細信息
```
┌──────────────────────────┐
│ [✕]  演唱會詳情  [ ]    │
├──────────────────────────┤
│ 五月天                   │
│                          │
│ 📅 時間: 2026-02-15     │
│ 📍 地點: 台北小巨蛋      │
│ 🌐 來源: KKTIX           │
│ 🔗 購票: https://...    │
│                          │
│ [取消關注 ★]            │
│ [移除提醒 🔔]           │
└──────────────────────────┘
```

---

## 🔌 API 端點速查表

### 認證
```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/profile
PUT    /api/auth/profile
```

### 演唱會
```
GET    /api/concerts
GET    /api/concerts/<id>
```

### 關注
```
GET    /api/follows
POST   /api/follows/<id>
DELETE /api/follows/<id>
GET    /api/follows/<id>/check
```

### 提醒
```
GET    /api/reminders
POST   /api/reminders/<id>
DELETE /api/reminders/<id>
```

### 健康檢查
```
GET    /api/health
```

---

## 📁 重要文件位置

| 文件 | 用途 | 位置 |
|------|------|------|
| `app.py` | 後端 API | 項目根目錄 |
| `App.js` | 前端應用 | `mobile_ui/` |
| `concert_crawler.py` | 爬蟲 | 項目根目錄 |
| `requirements.txt` | Python 依賴 | 項目根目錄 |
| `package.json` | npm 依賴 | `mobile_ui/` |

---

## 🔧 常用命令

```bash
# 激活 Python 虛擬環境
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# 安裝依賴
pip install -r requirements.txt
cd mobile_ui && npm install

# 啟動爬蟲
python concert_crawler.py

# 啟動後端
python app.py

# 啟動前端
cd mobile_ui && npm start

# 測試 API
curl http://localhost:5000/api/health
```

---

## 🎯 功能速查表

| 功能 | 按鈕/操作 | 效果 |
|------|---------|------|
| 登入 | 輸入郵箱+密碼→登入 | 進入應用 |
| 註冊 | 點擊「點擊註冊」 | 創建新賬戶 |
| 搜尋 | 搜尋欄輸入 | 過濾演唱會 |
| 關注 | 點擊 ☆/★ | 添加/移除關注 |
| 提醒 | 點擊 🔕/🔔 | 添加/移除提醒 |
| 詳情 | 點擊卡片 | 打開 Modal |
| 查看關注 | 點擊「我的關注」 | 只顯示關注的 |
| 登出 | 點擊「登出」 | 退出應用 |

---

## 📊 數據模型

### 用戶
```json
{
  "user_id": "uuid",
  "username": "用戶名",
  "email": "email@example.com",
  "password": "hash",
  "created_at": "2026-01-12T...",
  "preferences": {
    "genres": [],
    "venues": [],
    "notification_enabled": true
  }
}
```

### 演唱會
```json
{
  "id": "12345678",
  "來源網站": "KKTIX",
  "演出藝人": "五月天",
  "演出時間": "2026-02-15",
  "演出地點": "台北小巨蛋",
  "網址": "https://kktix.com/...",
  "爬取時間": "2026-01-12 14:30:00"
}
```

### 關注
```json
{
  "user_id": ["concert_id_1", "concert_id_2"]
}
```

### 提醒
```json
{
  "user_id": {
    "concert_id": {
      "type": "on_sale",
      "enabled": true,
      "created_at": "2026-01-12T..."
    }
  }
}
```

---

## 🎨 顏色代碼

| 名稱 | 顏色 | 用途 |
|------|------|------|
| 背景 | `#0e1629` | 主背景 |
| 卡片 | `#162b54` | 卡片背景 |
| 邊框 | `#24407a` | 邊框色 |
| 文字 | `#f5f7ff` | 主文字 |
| 次文字 | `#c7d4ff` | 輔助文字 |
| 強調 | `#007AFF` | 按鈕、連結 |
| 關注 | `#fbbf24` | 已關注 |
| 提醒 | `#10b981` | 已提醒 |

---

## ❓ 常見問題

### Q: API 無法連接？
A: 確保 `python app.py` 在運行，檢查 `http://localhost:5000/api/health`

### Q: 沒有演唱會數據？
A: 運行 `python concert_crawler.py --format json` 爬取數據

### Q: 忘記密碼？
A: 刪除 `data/users.json`，重新創建賬戶（開發環境）

### Q: 如何連接到遠程服務器？
A: 在 `App.js` 中修改 `API_BASE_URL` 為服務器地址

---

## 🔗 文檔導航

- 📖 [完整安裝指南](INSTALL.md)
- 📘 [詳細項目文檔](PROJECT_GUIDE.md)
- 📝 [項目完成總結](SUMMARY.md)
- ✅ [檢查清單](CHECKLIST.md)

---

**快速參考版本**: 1.0  
**最後更新**: 2026年1月12日  
**狀態**: ✅ 就緒
