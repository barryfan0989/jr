"""
強制刪除「檢核錯誤清單」資料
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
print("🧹 強制刪除「檢核錯誤清單」")
print("=" * 70)

# 查詢所有「檢核錯誤清單」資料
cursor.execute("SELECT COUNT(*) FROM events WHERE artist = '檢核錯誤清單'")
count = cursor.fetchone()[0]

print(f"\n找到 {count} 筆「檢核錯誤清單」")

if count > 0:
    # 刪除
    cursor.execute("DELETE FROM events WHERE artist = '檢核錯誤清單'")
    print(f"✅ 已刪除 {cursor.rowcount} 筆\n")
    
    # 提交
    conn.commit()
    
    # 確認刪除
    cursor.execute("SELECT COUNT(*) FROM events WHERE artist = '檢核錯誤清單'")
    remaining = cursor.fetchone()[0]
    print(f"刪除後剩餘: {remaining} 筆")

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

print("\n✅ 完成！")
