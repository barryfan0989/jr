#!/usr/bin/env python3
import os
import mysql.connector

HOST='ticketdb-ticket63.f.aivencloud.com'
PORT=13599
USER='avnadmin'
PWD='AVNS_QqNVFqacdQinAgGmXY9'
DB='defaultdb'

conn = mysql.connector.connect(host=HOST, port=PORT, user=USER, password=PWD, database=DB, charset='utf8mb4')
cur = conn.cursor()
try:
    print('--- Views ---')
    cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema=%s", (DB,))
    for (v,) in cur.fetchall():
        print('  VIEW:', v)
    print('\n--- Triggers ---')
    cur.execute("SELECT trigger_name, event_manipulation, event_object_table FROM information_schema.triggers WHERE trigger_schema=%s", (DB,))
    for r in cur.fetchall():
        print('  TRIGGER:', r)
    print('\n--- Check expected triggers/views ---')
    expected_views = ['concert_overview', '活動聯合檢視']
    for v in expected_views:
        cur.execute("SELECT COUNT(1) FROM information_schema.views WHERE table_schema=%s AND table_name=%s", (DB, v))
        print(f"  {v}:", cur.fetchone()[0])
    expected_triggers = [
        'tr_events_ins_to_活動','tr_events_upd_to_活動','tr_events_del_from_活動',
        'tr_venue_locations_ins_to_活動地點','tr_venue_locations_upd_to_活動地點','tr_venue_locations_del_from_活動地點',
        'tr_sales_channels_ins_to_售票平台','tr_sales_channels_upd_to_售票平台','tr_sales_channels_del_from_售票平台',
        'tr_artists_ins_to_藝人','tr_artists_upd_to_藝人','tr_artists_del_from_藝人'
    ]
    for t in expected_triggers:
        cur.execute("SELECT COUNT(1) FROM information_schema.triggers WHERE trigger_schema=%s AND trigger_name=%s", (DB, t))
        print(f"  {t}:", cur.fetchone()[0])
finally:
    cur.close()
    conn.close()
