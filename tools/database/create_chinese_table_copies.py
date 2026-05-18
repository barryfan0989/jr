#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在指定的遠端資料庫上建立或重建中文表複本（非破壞英文表）。

用法:
  python create_chinese_table_copies.py [--force-recreate]

行為:
  - 以 `CREATE TABLE `目標` LIKE `來源`` 建立中文表結構複本
  - 若加上 `--force-recreate`，會先 `DROP TABLE IF EXISTS` 再建立
  - 僅同步表結構（不會複製外鍵的參照約束），不會修改來源表
"""
import argparse
import os
import mysql.connector

MAPPINGS = {
    'events': '活動',
    'venue_locations': '活動地點',
    'sales_channels': '售票平台',
    'artists': '藝人',
    'users': '使用者',
}

DB_CONFIG = dict(
    host=os.getenv('DB_HOST', 'ticketdb-ticket63.f.aivencloud.com'),
    port=int(os.getenv('DB_PORT', '13599')),
    user=os.getenv('DB_USER', 'avnadmin'),
    password=os.getenv('DB_PASSWORD', 'AVNS_QqNVFqacdQinAgGmXY9'),
    database=os.getenv('DB_NAME', 'defaultdb'),
    charset='utf8mb4',
    autocommit=True,
)


def table_exists(cur, db, table):
    cur.execute('SELECT COUNT(1) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s', (db, table))
    return cur.fetchone()[0] > 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--force-recreate', action='store_true', help='若存在則先 DROP 再建立')
    args = p.parse_args()

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        for eng, chi in MAPPINGS.items():
            print(f'Processing: {eng} -> {chi}')
            if not table_exists(cur, DB_CONFIG['database'], eng):
                print(f'  source not found: {eng}, skip')
                continue
            if table_exists(cur, DB_CONFIG['database'], chi):
                if args.force_recreate:
                    print(f'  target {chi} exists, dropping because --force-recreate')
                    cur.execute(f'DROP TABLE IF EXISTS `{chi}`')
                else:
                    print(f'  target {chi} already exists, skip')
                    continue
            try:
                sql = f'CREATE TABLE `{chi}` LIKE `{eng}`'
                cur.execute(sql)
                print(f'  created {chi} from {eng}')
            except Exception as e:
                print(f'  failed to create {chi}:', e)
    finally:
        cur.close()
        conn.close()

    print('done')


if __name__ == '__main__':
    main()
