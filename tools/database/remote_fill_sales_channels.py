# -*- coding: utf-8 -*-
import re
import mysql.connector

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

cur.execute("SELECT event_id, `來源網站`, `搶票時間` FROM events")
rows = cur.fetchall()
inserted = 0
for event_id, source_site, sale_text in rows:
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

    m1 = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', sale_text)
    if m1:
        y, m, d = m1.groups()
        start_date = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    else:
        m2 = re.search(r'(\d{1,2})/(\d{1,2})', sale_text)
        if m2:
            m, d = m2.groups()
            start_date = f"2026-{int(m):02d}-{int(d):02d}"

    mt = re.search(r'(\d{1,2}):(\d{2})', sale_text)
    if mt:
        hh, mm = mt.groups()
        start_time = f"{int(hh):02d}:{int(mm):02d}:00"

    cur.execute(
        "INSERT INTO sales_channels (event_id, platform, channel_type, start_date, start_time, sales_status, notes) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (event_id, source_site, 'general', start_date, start_time, status, sale_text[:1000])
    )
    inserted += 1

conn.commit()
cur.execute('SELECT COUNT(*) FROM sales_channels')
total = cur.fetchone()[0]
print('inserted=', inserted)
print('total_sales_channels=', total)

cur.execute("SELECT sales_status, COUNT(*) FROM sales_channels GROUP BY sales_status ORDER BY COUNT(*) DESC")
for s, c in cur.fetchall():
    print(s, c)

cur.close()
conn.close()
