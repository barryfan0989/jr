"""
自動清理 MySQL 資料庫中的錯誤資料
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

print("=" * 70)
print("🧹 自動清理錯誤資料")
print("=" * 70)

# 1. 刪除藝人名稱為「檢核錯誤清單」的資料
cursor.execute("SELECT COUNT(*) FROM events WHERE artist LIKE '%檢核%'")
error_count = cursor.fetchone()[0]

if error_count > 0:
    cursor.execute("DELETE FROM events WHERE artist LIKE '%檢核%'")
    print(f"✅ 已刪除 {cursor.rowcount} 筆「檢核錯誤」資料")
else:
    print("✅ 沒有「檢核錯誤」資料")

# 2. 刪除藝人名稱為空的資料
cursor.execute("SELECT COUNT(*) FROM events WHERE artist IS NULL OR artist = ''")
null_count = cursor.fetchone()[0]

if null_count > 0:
    cursor.execute("DELETE FROM events WHERE artist IS NULL OR artist = ''")
    print(f"✅ 已刪除 {cursor.rowcount} 筆藝人名稱為空的資料")
else:
    print("✅ 沒有藝人名稱為空的資料")

# 3. 刪除重複資料（保留 id 最小的一筆）
print("\n檢查重複資料...")
cursor.execute("""
    DELETE FROM events
    WHERE id NOT IN (
        SELECT MIN(id) FROM (
            SELECT MIN(id) FROM events
            WHERE url IS NOT NULL AND url != ''
            GROUP BY url, artist, event_time
        ) as min_ids
    ) AND url IS NOT NULL AND url != ''
""")
deleted_duplicates = cursor.rowcount
if deleted_duplicates > 0:
    print(f"✅ 已刪除 {deleted_duplicates} 筆重複資料")

# 提交變更
conn.commit()

# 顯示清理後的統計
cursor.execute("SELECT COUNT(*) FROM events")
total = cursor.fetchone()[0]

print("\n" + "=" * 70)
print("清理後統計：")
print("=" * 70)
print(f"總活動數: {total:,} 筆\n")

cursor.execute("""
    SELECT source, COUNT(*) as cnt 
    FROM events 
    GROUP BY source 
    ORDER BY cnt DESC
""")

for source, count in cursor.fetchall():
    print(f"  • {source or 'Unknown'}: {count:,} 筆")

cursor.close()
conn.close()

print("\n✅ 清理完成！")
