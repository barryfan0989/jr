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

conn = mysql.connector.connect(**DB_CONFIG)
cur = conn.cursor()
cur.execute('SELECT venue_id FROM venues LIMIT 1')
row = cur.fetchone()
if not row:
    print('no venues found, abort')
else:
    vid = row[0]
    try:
        cur.execute('INSERT INTO venue_locations (venue_id, city, district, street, venue_details) VALUES (%s,%s,%s,%s,%s)', (vid, '測試市', '測試區', '測試街', '測試'))
        print('inserted test row into venue_locations')
    except Exception as e:
        print('error during insert:', e)
cur.close()
conn.close()
