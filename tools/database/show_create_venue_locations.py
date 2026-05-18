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
cur.execute("SHOW CREATE TABLE venue_locations")
row = cur.fetchone()
if row:
    print(row[1])
else:
    print('venue_locations not found')
cur.close()
conn.close()
