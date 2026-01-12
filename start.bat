@echo off
REM 演唱會通知助手 - Windows 啟動腳本

echo.
echo 🎵 演唱會通知助手 - 啟動系統
echo ======================================

REM 檢查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，請先安裝 Python
    pause
    exit /b 1
)

REM 安裝依賴
echo.
echo 📦 正在安裝 Python 依賴...
pip install -r requirements.txt

REM 爬取數據
echo.
echo 🕷️  正在爬取演唱會數據...
python concert_crawler.py --format json

REM 啟動 API
echo.
echo 🚀 啟動後端 API ^(http://localhost:5000^)...
start python app.py

REM 等待一下讓 API 啟動
timeout /t 3 /nobreak

REM 啟動前端
echo.
echo 📱 正在啟動前端應用...
cd mobile_ui
call npm install
call npm start

pause
