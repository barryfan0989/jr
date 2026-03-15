# Tools 整理說明

此資料夾集中放置非主流程腳本，讓專案根目錄保持乾淨。

## 目錄說明

- `legacy/`：歷史 debug/診斷腳本
- `maintenance/`：維運/檢查/清理腳本
- `database/`：資料庫匯入與檢視工具
- `testing/`：快速測試與測試腳本

## 主流程入口（仍在根目錄）

- `concert_crawler.py`
- `app.py`
- `run_server.py`
- `run_all_crawlers.py`
- `start.bat` / `start.sh`

## 常用執行範例

```bash
python tools/maintenance/check_dependencies.py
python tools/database/json_to_mysql.py
python tools/testing/quick_test.py
```
