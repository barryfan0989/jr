# -*- coding: utf-8 -*-
import mysql.connector
import sys

# 本地
local = mysql.connector.connect(host="127.0.0.1", user="root", password="barry0803", database="concerts")
lc = local.cursor()

# 遠端
remote = mysql.connector.connect(
    host="ticketdb-ticket63.f.aivencloud.com", port=13599, user="avnadmin",
    password="AVNS_QqNVFqacdQinAgGmXY9", database="defaultdb",
    ssl_verify_cert=False, ssl_verify_identity=False
)
rc = remote.cursor()

print("Sync refined tables to Aiven...")

# 複製 event_schedules
print("\n1. event_schedules")
lc.execute("SELECT event_id, performance_date, start_time FROM event_schedules")
rows = lc.fetchall()

for r in rows:
    rc.execute("INSERT INTO event_schedules (event_id, performance_date, start_time) VALUES (%s, %s, %s)", r)
    
remote.commit()
print(f"   Inserted {len(rows)} rows")

# 複製 ticket_pricing
print("\n2. ticket_pricing")
lc.execute("SELECT event_id, tier_name, price_amount FROM ticket_pricing")
rows = lc.fetchall()

for r in rows:
    rc.execute("INSERT INTO ticket_pricing (event_id, tier_name, price_amount) VALUES (%s, %s, %s)", r)
    
remote.commit()
print(f"   Inserted {len(rows)} rows")

# 驗證
print("\n3. Verify:")
rc.execute("SELECT COUNT(*) FROM event_schedules")
print(f"   event_schedules: {rc.fetchone()[0]}")
rc.execute("SELECT COUNT(*) FROM ticket_pricing")
print(f"   ticket_pricing: {rc.fetchone()[0]}")

local.close()
remote.close()
print("\nDone!")
