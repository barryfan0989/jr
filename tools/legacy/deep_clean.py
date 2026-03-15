"""
更深入的診斷和刪除「檢核錯誤」資料
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
print("🔍 詳細診斷")
print("=" * 70)

# 查詢所有包含「檢核」的資料
cursor.execute("SELECT COUNT(*) FROM events WHERE artist LIKE '%檢核%'")
like_count = cursor.fetchone()[0]
print(f"\n包含「檢核」的資料: {like_count} 筆")

if like_count > 0:
    # 顯示這些資料
    cursor.execute("""
        SELECT id, artist, source, event_time 
        FROM events 
        WHERE artist LIKE '%檢核%'
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    print("\n前 10 筆詳情：")
    for row in results:
        print(f"  ID {row[0]}: {row[1][:50]} | {row[2]}")
    
    # 刪除所有包含「檢核」的資料
    print(f"\n正在刪除 {like_count} 筆「檢核」相關資料...")
    cursor.execute("DELETE FROM events WHERE artist LIKE '%檢核%'")
    deleted = cursor.rowcount
    print(f"✅ 已刪除 {deleted} 筆")
    
    conn.commit()
    
    # 驗證刪除
    cursor.execute("SELECT COUNT(*) FROM events WHERE artist LIKE '%檢核%'")
    remaining = cursor.fetchone()[0]
    print(f"刪除後剩餘: {remaining} 筆")

else:
    print("✅ 沒有包含「檢核」的資料")

# 最終統計
print("\n" + "=" * 70)
print("最終資料統計:")
print("=" * 70)

cursor.execute("SELECT COUNT(*) FROM events")
total = cursor.fetchone()[0]
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

print("\n" + "=" * 70)
print("✅ 診斷和清理完成！")
print("=" * 70)
print("\n提示：請在 MySQL Workbench 中按 F5 刷新資料")
