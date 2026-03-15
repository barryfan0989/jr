"""
檢查 MySQL 資料庫內容
"""
import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    port=3306,
    user='root',
    password='barry0803',
    database='concerts',
    charset='utf8mb4'
)

cursor = conn.cursor()

# 總數
cursor.execute("SELECT COUNT(*) FROM events")
total = cursor.fetchone()[0]
print(f"總活動數: {total:,} 筆")

# 各來源統計
print("\n📊 各來源統計：")
cursor.execute("""
    SELECT source, COUNT(*) as cnt 
    FROM events 
    GROUP BY source 
    ORDER BY cnt DESC
""")
for source, count in cursor.fetchall():
    print(f"  • {source or 'Unknown'}: {count:,} 筆")

# KKTIX 最新活動
print("\n🎵 KKTIX 最新 5 筆活動：")
cursor.execute("""
    SELECT artist, event_time, venue
    FROM events
    WHERE source = 'KKTIX'
    ORDER BY id DESC
    LIMIT 5
""")
for artist, event_time, venue in cursor.fetchall():
    print(f"  • {artist or '未知'} - {event_time or '未公布'} @ {venue or '未公布'}")

cursor.close()
conn.close()
