#!/usr/bin/env python3
import mysql.connector
import os

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

conn = mysql.connector.connect(**DB_CONFIG)
cur = conn.cursor()
for eng, chi in MAPPINGS.items():
    ins_name = f'tr_{eng}_ins_to_{chi}'
    upd_name = f'tr_{eng}_upd_to_{chi}'
    del_name = f'tr_{eng}_del_from_{chi}'
    for t in (ins_name, upd_name, del_name):
        try:
            cur.execute(f'DROP TRIGGER IF EXISTS `{t}`')
            print('dropped trigger', t)
        except Exception as e:
            print('failed drop', t, e)

cur.close()
conn.close()
