# -*- coding: utf-8 -*-
import re
import mysql.connector
import datetime

conn = mysql.connector.connect(
    host='ticketdb-ticket63.f.aivencloud.com',
    port=13599,
    user='avnadmin',
    password='AVNS_QqNVFqacdQinAgGmXY9',
    database='defaultdb',
    ssl_verify_cert=False,
    ssl_verify_identity=False,
)
cur = conn.cursor()

# 1) Drop legacy tables
cur.execute(
    """
    SELECT TABLE_NAME
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA='defaultdb' AND TABLE_TYPE='BASE TABLE'
      AND TABLE_NAME NOT IN (
        'artists','venues','events','event_artists','artist_news',
        'artist_segments','event_segments','event_schedules','ticket_pricing',
        'sales_channels','venue_locations','users','reminders','import_log'
      )
    """
)
legacy_tables = [r[0] for r in cur.fetchall()]

cur.execute('SET FOREIGN_KEY_CHECKS=0')
for t in legacy_tables:
    cur.execute(f"DROP TABLE IF EXISTS `{t}`")
cur.execute('SET FOREIGN_KEY_CHECKS=1')

# 2) Fill venue_locations if missing
cur.execute("SELECT venue_id, venue_name, venue_address FROM venues")
venue_rows = cur.fetchall()
insert_vl = 0
for venue_id, venue_name, addr in venue_rows:
    cur.execute("SELECT COUNT(*) FROM venue_locations WHERE venue_id=%s", (venue_id,))
    if cur.fetchone()[0] > 0:
        continue

    text = f"{venue_name or ''} {addr or ''}"
    city = '未知'
    district = None

    city_map = [
        ('台北', '台北市'), ('臺北', '台北市'), ('新北', '新北市'), ('桃園', '桃園市'),
        ('台中', '台中市'), ('臺中', '台中市'), ('台南', '台南市'), ('臺南', '台南市'),
        ('高雄', '高雄市'), ('基隆', '基隆市'), ('新竹', '新竹市'), ('嘉義', '嘉義市'),
        ('宜蘭', '宜蘭縣'), ('苗栗', '苗栗縣'), ('彰化', '彰化縣'), ('南投', '南投縣'),
        ('雲林', '雲林縣'), ('屏東', '屏東縣'), ('台東', '台東縣'), ('臺東', '台東縣'),
        ('花蓮', '花蓮縣'), ('澎湖', '澎湖縣'), ('金門', '金門縣'), ('連江', '連江縣')
    ]
    for k, v in city_map:
        if k in text:
            city = v
            break

    m = re.search(r'([\u4e00-\u9fff]{2,3}[區鄉鎮市])', text)
    if m:
        district = m.group(1)

    cur.execute(
        "INSERT INTO venue_locations (venue_id, city, district, street, venue_details) VALUES (%s,%s,%s,%s,%s)",
        (venue_id, city, district, (addr or ''), (venue_name or '')),
    )
    insert_vl += 1

# 3) Fill sales_channels from events
cur.execute("SELECT event_id, `來源網站`, `搶票時間` FROM events")
event_rows = cur.fetchall()
insert_sc = 0
for event_id, source_site, sale_text in event_rows:
    cur.execute("SELECT COUNT(*) FROM sales_channels WHERE event_id=%s", (event_id,))
    if cur.fetchone()[0] > 0:
        continue

    sale_text = sale_text or ''
    status = '販售中/未明'
    if not sale_text or sale_text == '未提供':
        status = '未提供'
    elif ('完售' in sale_text) or ('已售完' in sale_text):
        status = '已售完'
    elif ('預售' in sale_text) or ('開賣' in sale_text) or ('即將' in sale_text):
        status = '待開賣'

    start_date = None
    start_time = None

    # parse dates safely and validate ranges
    m1 = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', sale_text)
    if m1:
        y, m, d = map(int, m1.groups())
        if 1 <= m <= 12 and 1 <= d <= 31:
            start_date = f"{y:04d}-{m:02d}-{d:02d}"
        else:
            start_date = None
    else:
        m2 = re.search(r'(\d{1,2})/(\d{1,2})', sale_text)
        if m2:
            mm, dd = map(int, m2.groups())
            year = datetime.date.today().year
            if 1 <= mm <= 12 and 1 <= dd <= 31:
                start_date = f"{year}-{mm:02d}-{dd:02d}"
            else:
                start_date = None

    mt = re.search(r'(\d{1,2}):(\d{2})', sale_text)
    if mt:
        hh, mm = map(int, mt.groups())
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            start_time = f"{hh:02d}:{mm:02d}:00"
        else:
            start_time = None

    cur.execute(
        "INSERT INTO sales_channels (event_id, platform, channel_type, start_date, start_time, sales_status, notes) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (event_id, source_site, 'general', start_date, start_time, status, sale_text[:1000]),
    )
    insert_sc += 1

conn.commit()

print('dropped_legacy_tables=', len(legacy_tables))
for t in legacy_tables:
    print('drop:', t)
print('inserted_venue_locations=', insert_vl)
print('inserted_sales_channels=', insert_sc)

cur.close()
conn.close()
