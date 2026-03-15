import sqlite3
from datetime import datetime

def view_database():
    """查看資料庫狀態"""
    conn = sqlite3.connect('data/concerts.db')
    cursor = conn.cursor()
    
    # 列出所有資料表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("=" * 60)
    print("資料表清單：")
    print("=" * 60)
    for table in tables:
        print(f"  📊 {table[0]}")
    
    # 統計 events 表
    print("\n" + "=" * 60)
    print("演唱會活動統計")
    print("=" * 60)
    
    cursor.execute("SELECT COUNT(*) FROM events")
    total_count = cursor.fetchone()[0]
    print(f"總活動數量: {total_count:,} 筆")
    
    # 各來源統計
    print("\n📍 各來源統計：")
    cursor.execute("""
        SELECT source, COUNT(*) as cnt 
        FROM events 
        GROUP BY source 
        ORDER BY cnt DESC
    """)
    sources = cursor.fetchall()
    for source, count in sources:
        print(f"  • {source}: {count:,} 筆")
    
    # 最近的活動
    print("\n" + "=" * 60)
    print("最近匯入的 5 筆活動：")
    print("=" * 60)
    cursor.execute("""
        SELECT artist, event_time, venue, source 
        FROM events 
        ORDER BY id DESC 
        LIMIT 5
    """)
    recent_events = cursor.fetchall()
    for i, (artist, event_time, venue, source) in enumerate(recent_events, 1):
        print(f"\n{i}. {artist}")
        print(f"   時間: {event_time}")
        print(f"   地點: {venue}")
        print(f"   來源: {source}")
    
    # 匯入記錄
    print("\n" + "=" * 60)
    print("最近的匯入記錄：")
    print("=" * 60)
    cursor.execute("""
        SELECT source_file, imported_at, record_count, inserted_count 
        FROM import_log 
        ORDER BY imported_at DESC 
        LIMIT 5
    """)
    import_logs = cursor.fetchall()
    for log in import_logs:
        source_file, imported_at, record_count, inserted_count = log
        print(f"  📄 {source_file}")
        print(f"     匯入時間: {imported_at}")
        print(f"     新增: {inserted_count}/{record_count} 筆\n")
    
    conn.close()
    print("=" * 60)
    print("✅ 資料庫查看完成！")
    print("=" * 60)

if __name__ == "__main__":
    view_database()
