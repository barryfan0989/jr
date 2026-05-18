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
cur.execute("SELECT TRIGGER_NAME, ACTION_STATEMENT FROM information_schema.triggers WHERE TRIGGER_SCHEMA=%s AND EVENT_OBJECT_TABLE='venue_locations'", (DB_CONFIG['database'],))
for r in cur.fetchall():
    print('TRIGGER:', r[0])
    print(r[1])
    print('---')
cur.close()
conn.close()
