#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check the `活動聯合檢視` view: show definition and sample rows.
"""

from __future__ import annotations

import traceback
import mysql.connector

DB_CONFIG = dict(
    host='ticketdb-ticket63.f.aivencloud.com',
    port=13599,
    user='avnadmin',
    password='AVNS_QqNVFqacdQinAgGmXY9',
    database='defaultdb',
    charset='utf8mb4',
    autocommit=False,
)


def main():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor()
        print('檢查 VIEW 定義: SHOW CREATE VIEW `活動聯合檢視`')
        try:
            cur.execute('SHOW CREATE VIEW `活動聯合檢視`')
            row = cur.fetchone()
            if row:
                print('FOUND VIEW definition (truncated):')
                print(row[1][:1000])
            else:
                print('VIEW `活動聯合檢視` 不存在 (SHOW returned no rows)')
        except Exception as e:
            print('SHOW CREATE VIEW failed:', e)

        print('\n嘗試查詢前 5 筆資料: SELECT * FROM `活動聯合檢視` LIMIT 5')
        try:
            cur.execute('SELECT * FROM `活動聯合檢視` LIMIT 5')
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
            print('columns:', cols)
            for r in rows:
                print(r)
        except Exception as e:
            print('SELECT failed:', e)

        cur.close()
        conn.close()
    except Exception:
        traceback.print_exc()


if __name__ == '__main__':
    main()
