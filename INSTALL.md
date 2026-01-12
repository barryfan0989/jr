# 演唱會通知助手 - 安裝指南

## 系統要求

- **Python**: 3.8 或更高版本
- **Node.js**: 14.0 或更高版本
- **npm** 或 **yarn**
- **Git**

## 快速安裝

### Step 1: 克隆倉庫

```bash
cd ~/Documents/GitHub
git clone https://github.com/yourusername/jr.git
cd jr
```

### Step 2: 設置 Python 環境

#### Windows
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: 設置環境變量

```bash
cp .env.example .env
# 編輯 .env 文件，修改你的配置
```

### Step 4: 爬取演唱會數據

```bash
python concert_crawler.py --format json
```

### Step 5: 啟動後端 API

```bash
python app.py
```

你應該看到：
```
 * Running on http://0.0.0.0:5000
 * Debugger is active!
```

### Step 6: 設置前端（在新終端窗口）

```bash
cd mobile_ui
npm install
npm start
```

## 使用方式

### 方式 1: 使用啟動腳本 (推薦)

#### Windows
```bash
start.bat
```

#### macOS / Linux
```bash
bash start.sh
```

### 方式 2: 手動啟動

#### 終端 1 - 後端
```bash
python app.py
```

#### 終端 2 - 前端
```bash
cd mobile_ui
npm start
```

### 方式 3: Docker (未來支援)

```bash
docker-compose up
```

## 首次使用

1. **打開應用** - 掃描 QR code 或在瀏覽器中打開 Expo 應用
2. **註冊賬戶** - 點擊「還沒有賬戶？點擊註冊」
3. **填寫信息**:
   - 用戶名：任意
   - 郵箱：youremail@example.com
   - 密碼：至少 6 個字符
4. **登入** - 使用註冊的郵箱和密碼登入
5. **瀏覽演唱會** - 查看爬蟲爬取的演唱會列表
6. **關注與提醒** - 點擊 ☆ 關注，點擊 🔕 設置提醒

## API 測試

使用 curl 或 Postman 測試 API：

### 測試健康狀況
```bash
curl http://localhost:5000/api/health
```

### 測試註冊
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

### 獲取演唱會列表
```bash
curl http://localhost:5000/api/concerts
```

## 故障排除

### 問題 1: 找不到 Python
**解決方案**:
```bash
# 檢查 Python 版本
python --version
# 或
python3 --version
```

如果都不行，請[下載並安裝 Python](https://www.python.org/downloads/)

### 問題 2: npm 找不到
**解決方案**:
- [下載並安裝 Node.js](https://nodejs.org/)
- 安裝後重啟終端

### 問題 3: API 連接失敗
**解決方案**:
1. 確認後端在運行: `python app.py`
2. 檢查 `mobile_ui/App.js` 中的 `API_BASE_URL`
3. 如果在真機運行，使用電腦的 IP 地址而非 `localhost`

### 問題 4: 沒有演唱會數據
**解決方案**:
1. 運行爬蟲: `python concert_crawler.py --format json`
2. 檢查 `data/concerts.json` 是否存在
3. 查看控制台輸出了解具體錯誤

### 問題 5: 登入後看不到演唱會
**解決方案**:
1. 檢查 API 是否在運行
2. 在瀏覽器打開 `http://localhost:5000/api/concerts` 檢查數據
3. 清除 app cache 後重試

## 開發模式

### 啟用調試模式

編輯 `.env`:
```env
FLASK_ENV=development
FLASK_DEBUG=True
```

然後重啟 API:
```bash
python app.py
```

### 查看日誌

```bash
# 查看最後 100 行
tail -100 logs/app.log

# 實時監控
tail -f logs/app.log
```

### 重置數據

```bash
# 刪除所有用戶數據
rm -rf data/

# API 會自動重新創建
python app.py
```

## 生產部署

### 前置條件

- 購買域名
- 租用服務器 (AWS, DigitalOcean, Heroku 等)
- 配置 SSL/TLS

### 部署步驟

1. **上傳代碼到服務器**
2. **安裝依賴**
3. **配置環境變量**
4. **使用 Gunicorn 運行 API**:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```
5. **配置 Nginx 反向代理**
6. **設置 SSL 證書 (Let's Encrypt)**
7. **部署前端到 Vercel 或 Netlify**

## 常用命令

```bash
# 激活虛擬環境
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# 安裝所有依賴
pip install -r requirements.txt

# 啟動爬蟲
python concert_crawler.py

# 啟動 API
python app.py

# 啟動前端
cd mobile_ui && npm start

# 停止服務 (Ctrl+C)

# 進入 Python shell 測試
python
>>> import app
>>> app.app.config
```

## 獲取幫助

- 📖 查看 [PROJECT_GUIDE.md](PROJECT_GUIDE.md)
- 🐛 檢查已知問題和解決方案
- 💬 在 GitHub Issues 提問

---

**祝你使用愉快！** 🎵✨
