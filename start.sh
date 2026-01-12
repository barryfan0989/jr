#!/bin/bash
# 演唱會通知助手 - 啟動腳本

echo "🎵 演唱會通知助手 - 啟動系統"
echo "======================================"

# 檢查 Python 版本
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ 檢測到 Python $python_version"

# 安裝依賴
echo ""
echo "📦 正在安裝 Python 依賴..."
pip install -r requirements.txt

# 爬取數據
echo ""
echo "🕷️  正在爬取演唱會數據..."
python concert_crawler.py --format json

# 啟動 API
echo ""
echo "🚀 啟動後端 API (http://localhost:5000)..."
python app.py &
API_PID=$!

# 啟動前端
echo ""
echo "📱 啟動前端應用..."
cd mobile_ui
npm install
npm start

# 清理
trap "kill $API_PID" EXIT
