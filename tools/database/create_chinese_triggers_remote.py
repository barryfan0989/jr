#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在指定的遠端資料庫上建立中文複本的同步觸發器（不修改表結構）
"""
import mysql.connector

MAPPINGS = {
    'events': '活動',
    'venue_locations': '活動地點',
    'sales_channels': '售票平台',
    'artists': '藝人',
    'users': '使用者',
}

import os
DB_CONFIG = dict(
    host=os.getenv('DB_HOST', 'ticketdb-ticket63.f.aivencloud.com'),
    port=int(os.getenv('DB_PORT', '13599')),
    user=os.getenv('DB_USER', 'avnadmin'),
    password=os.getenv('DB_PASSWORD', 'AVNS_QqNVFqacdQinAgGmXY9'),
    database=os.getenv('DB_NAME', 'defaultdb'),
    charset='utf8mb4',
    autocommit=True,
)

conn = mysql.connector.connect(**DB_CONFIG)
cur = conn.cursor()
try:
    for eng, chi in MAPPINGS.items():
        print(f'Processing: {eng} -> {chi}')
        # check both tables exist
        cur.execute('SELECT COUNT(1) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s', (DB_CONFIG['database'], eng))
        if cur.fetchone()[0] == 0:
            print(f'  source not found: {eng}, skip')
            continue
        cur.execute('SELECT COUNT(1) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s', (DB_CONFIG['database'], chi))
        if cur.fetchone()[0] == 0:
            print(f'  target not found: {chi}, skip')
            continue
        cur.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position', (DB_CONFIG['database'], eng))
        eng_cols = [r[0] for r in cur.fetchall()]
        cur.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position', (DB_CONFIG['database'], chi))
        chi_cols = [r[0] for r in cur.fetchall()]
        common = [c for c in eng_cols if c in chi_cols]
        if not common:
            print(f'  no common cols for {eng} -> {chi}, skip')
            continue
        col_list = ','.join([f'`{c}`' for c in common])
        val_list_new = ','.join([f'NEW.`{c}`' for c in common])
        ins_name = f'tr_{eng}_ins_to_{chi}'
        upd_name = f'tr_{eng}_upd_to_{chi}'
        del_name = f'tr_{eng}_del_from_{chi}'
        for t in (ins_name, upd_name, del_name):
            try:
                cur.execute(f'DROP TRIGGER IF EXISTS `{t}`')
            except Exception:
                pass
        try:
            ins_sql = f'CREATE TRIGGER `{ins_name}` AFTER INSERT ON `{eng}` FOR EACH ROW REPLACE INTO `{chi}` ({col_list}) VALUES ({val_list_new})'
            upd_sql = f'CREATE TRIGGER `{upd_name}` AFTER UPDATE ON `{eng}` FOR EACH ROW REPLACE INTO `{chi}` ({col_list}) VALUES ({val_list_new})'
            # attempt to find primary key
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s AND column_key='PRI'", (DB_CONFIG['database'], eng))
            pkrow = cur.fetchone()
            if pkrow and pkrow[0] in common:
                pk = pkrow[0]
                del_sql = f'CREATE TRIGGER `{del_name}` AFTER DELETE ON `{eng}` FOR EACH ROW DELETE FROM `{chi}` WHERE `{pk}` = OLD.`{pk}`'
            else:
                pk = None
                del_sql = None
            cur.execute(ins_sql)
            cur.execute(upd_sql)
            if del_sql:
                cur.execute(del_sql)
            print(f'  triggers created for {eng} -> {chi} (cols: {len(common)})')
        except Exception as e:
            print('  failed to create triggers:', e)
finally:
    cur.close()
    conn.close()

print('done')
