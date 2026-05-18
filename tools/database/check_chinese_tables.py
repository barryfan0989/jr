#!/usr/bin/env python3
import mysql.connector
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

NAMES = ['活動', '活動地點', '售票平台', '藝人', '使用者']

conn = mysql.connector.connect(**DB_CONFIG)
cur = conn.cursor()
for t in NAMES:
    cur.execute('SELECT COUNT(1) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s', (DB_CONFIG['database'], t))
    exists = cur.fetchone()[0] > 0
    if exists:
        cur.execute(f'SELECT COUNT(*) FROM `{t}`')
        count = cur.fetchone()[0]
        print(f"{t}: EXISTS ({count} rows)")
    else:
        print(f"{t}: MISSING")
print('\nTables containing 活 or 藝 or 售:')
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND (table_name LIKE %s OR table_name LIKE %s OR table_name LIKE %s)", (DB_CONFIG['database'], '%活%', '%藝%', '%售%'))
for r in cur.fetchall():
    print('  -', r[0])
cur.close()
conn.close()
