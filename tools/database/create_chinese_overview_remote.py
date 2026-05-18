#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import mysql.connector

DB_CONFIG = dict(
    host=os.getenv('DB_HOST', 'ticketdb-ticket63.f.aivencloud.com'),
    port=int(os.getenv('DB_PORT', '13599')),
    user=os.getenv('DB_USER', 'avnadmin'),
    password=os.getenv('DB_PASSWORD', 'AVNS_QqNVFqacdQinAgGmXY9'),
    database=os.getenv('DB_NAME', 'defaultdb'),
    charset='utf8mb4',
    autocommit=True,
)

VIEW_SQL = '''
DROP VIEW IF EXISTS `活動聯合檢視`;
CREATE VIEW `活動聯合檢視` AS
SELECT
  event_id AS `event_id`,
  event_name AS `活動名稱`,
  source_site AS `來源網站`,
  event_url AS `網址`,
  raw_event_time AS `活動時間`,
  raw_sale_time AS `搶票時間`,
  raw_price AS `票價`,
  raw_venue_name AS `活動地點`,
  raw_venue_address AS `活動地址`,

  venue_id AS `場地_id`,
  venue_name AS `場地名稱`,
  venue_address AS `場地地址`,
  venue_intro AS `場地介紹`,

  event_type AS `活動類型`,
  price_band AS `票價區間`,
  sale_status AS `售票狀態`,
  event_segment_confidence AS `分群信心`,

  first_performance_date AS `首場`,
  last_performance_date AS `末場`,
  schedule_count AS `場次數`,

  min_price AS `最低票價`,
  max_price AS `最高票價`,
  price_tier_count AS `票種數`,

  artist_count AS `藝人數`,
  artist_names AS `藝人名稱`,
  artist_regions AS `藝人地區`,
  artist_languages AS `藝人語言`,
  artist_forms AS `藝人型態`,

  event_created_at AS `活動建立時間`
FROM concert_overview;
'''

conn = mysql.connector.connect(**DB_CONFIG)
cur = conn.cursor()
try:
    # split and execute statements to support mysql-connector
    stmts = [s.strip() for s in VIEW_SQL.split(';') if s.strip()]
    for s in stmts:
        cur.execute(s)
    # verify
    cur.execute('SELECT COUNT(1) FROM `活動聯合檢視`')
    row = cur.fetchone()
    cnt = row[0] if row else 0
    print('活動聯合檢視 rows=', cnt)
finally:
    cur.close()
    conn.close()
