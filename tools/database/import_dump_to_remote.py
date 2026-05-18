#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
將本機 SQL dump 覆寫匯入遠端資料庫（覆寫遠端 DB）
用法:
  python tools/database/import_dump_to_remote.py --file local_dump.sql --remote-host HOST --remote-port PORT --remote-user USER --remote-password PWD --remote-db DB

行為:
 - 先備份遠端（若需要，可在此前呼叫），本腳本假設你已備份。
 - 以 DROP DATABASE IF EXISTS <remote-db>; CREATE DATABASE <remote-db>; USE <remote-db>; 開始
 - 讀入 dump，移除 dump 中的 DROP/CREATE/USE database 指令，然後執行剩餘語句
 - 匯入期間暫時關閉 foreign_key_checks
 - 匯入完成後檢查主要表列數（events, venue_locations, sales_channels, artists）
"""
import argparse
import mysql.connector
import re

parser = argparse.ArgumentParser()
parser.add_argument('--file', required=True)
parser.add_argument('--remote-host', required=True)
parser.add_argument('--remote-port', type=int, default=3306)
parser.add_argument('--remote-user', required=True)
parser.add_argument('--remote-password', required=True)
parser.add_argument('--remote-db', required=True)
args = parser.parse_args()

# 讀入 dump，移除 DROP/CREATE/USE database 指令
with open(args.file, 'r', encoding='utf-8') as f:
    sql = f.read()

# 移除 DROP DATABASE / CREATE DATABASE / USE `...` 以避免干擾
sql = re.sub(r"DROP DATABASE IF EXISTS `[^`]+`;\s*", "", sql, flags=re.IGNORECASE)
sql = re.sub(r"CREATE DATABASE `[^`]+`;\s*", "", sql, flags=re.IGNORECASE)
sql = re.sub(r"USE `[^`]+`;\s*", "", sql, flags=re.IGNORECASE)

# 建立連線到遠端
conn = mysql.connector.connect(host=args.remote_host, port=args.remote_port, user=args.remote_user, password=args.remote_password, charset='utf8mb4')
cur = conn.cursor()

try:
    print(f"Dropping and creating remote database `{args.remote_db}`...")
    cur.execute(f"DROP DATABASE IF EXISTS `{args.remote_db}`")
    cur.execute(f"CREATE DATABASE `{args.remote_db}`")
    cur.execute(f"USE `{args.remote_db}`")
    try:
        cur.execute("SET foreign_key_checks = 0")
    except Exception:
        pass

    print("Executing dump SQL (this may take a while)...")
    # 將 dump 切成語句並逐一執行。注意：此方法對包含複雜 DELIMITER 的 dump 可能不完美，
    # 但對於由本工具產生的 dump（未使用自訂 DELIMITER）通常可行。
    import re
    statements = [s.strip() for s in re.split(r';\s*\n', sql) if s.strip()]
    executed = 0
    for stmt in statements:
        try:
            cur.execute(stmt)
            executed += 1
            if executed % 100 == 0:
                conn.commit()
        except Exception as e:
            print(f"  Statement failed: {e}\n  SQL snippet: {stmt[:200]}")
    conn.commit()
    try:
        cur.execute("SET foreign_key_checks = 1")
    except Exception:
        pass

    print("Import finished. Verifying row counts for main tables...")
    tables = ['events', 'venue_locations', 'sales_channels', 'artists']
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(1) FROM `{t}`")
            r = cur.fetchone()
            print(f"  {t}: {r[0] if r else 'N/A'} rows")
        except Exception as e:
            print(f"  {t}: error: {e}")
finally:
    cur.close()
    conn.close()
