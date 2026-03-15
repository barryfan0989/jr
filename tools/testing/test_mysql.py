"""
測試 MySQL 連接並查看資料庫狀態
"""
import mysql.connector
from mysql.connector import Error

def test_mysql_connection():
    """測試 MySQL 連接"""
    print("=" * 60)
    print("🔗 測試 MySQL 連接")
    print("=" * 60)
    
    # 預設連接設定
    configs = [
        {"host": "127.0.0.1", "port": 3306, "user": "root", "password": ""},
        {"host": "localhost", "port": 3306, "user": "root", "password": ""},
        {"host": "127.0.0.1", "port": 3306, "user": "root", "password": "root"},
    ]
    
    connection = None
    for config in configs:
        try:
            print(f"\n嘗試連接: {config['user']}@{config['host']}:{config['port']}")
            connection = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                user=config['user'],
                password=config['password'],
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            
            if connection.is_connected():
                db_info = connection.get_server_info()
                print(f"✅ 連接成功！MySQL 版本: {db_info}")
                
                cursor = connection.cursor()
                cursor.execute("SHOW DATABASES")
                databases = cursor.fetchall()
                
                print("\n📊 可用的資料庫：")
                has_concerts = False
                for (db_name,) in databases:
                    if db_name == 'concerts':
                        print(f"  ✓ {db_name} ← 演唱會資料庫存在！")
                        has_concerts = True
                    else:
                        print(f"  • {db_name}")
                
                if has_concerts:
                    # 檢查 concerts 資料庫內容
                    cursor.execute("USE concerts")
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    
                    print("\n📋 concerts 資料庫中的表格：")
                    for (table_name,) in tables:
                        print(f"  • {table_name}")
                        
                        # 計算每個表的記錄數
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        print(f"    → {count:,} 筆資料")
                    
                    # 顯示最近的活動
                    try:
                        cursor.execute("""
                            SELECT artist, event_time, venue, source 
                            FROM events 
                            ORDER BY id DESC 
                            LIMIT 5
                        """)
                        events = cursor.fetchall()
                        
                        print("\n🎵 最近的 5 筆活動：")
                        for i, (artist, event_time, venue, source) in enumerate(events, 1):
                            print(f"\n  {i}. {artist or '未知'}")
                            print(f"     時間: {event_time or '未公布'}")
                            print(f"     地點: {venue or '未公布'}")
                            print(f"     來源: {source or 'Unknown'}")
                    except Error as e:
                        print(f"  無法讀取活動資料: {e}")
                else:
                    print("\n⚠️  'concerts' 資料庫不存在")
                    print("\n建議操作：")
                    print("  1️⃣  建立資料庫並匯入資料：")
                    print("     python json_to_mysql.py --create-db --user root --password 你的密碼")
                
                cursor.close()
                
                print("\n" + "=" * 60)
                print("✅ MySQL 可以使用！")
                print("=" * 60)
                print(f"\n連接資訊：")
                print(f"  主機: {config['host']}")
                print(f"  埠號: {config['port']}")
                print(f"  使用者: {config['user']}")
                print(f"  密碼: {'(空白)' if not config['password'] else '***'}")
                
                connection.close()
                return config
                
        except Error as e:
            print(f"❌ 連接失敗: {e}")
            continue
    
    print("\n" + "=" * 60)
    print("❌ 無法連接到 MySQL")
    print("=" * 60)
    print("\n請確認：")
    print("  1. MySQL 服務是否已啟動")
    print("  2. 使用者名稱和密碼是否正確")
    print("  3. 防火牆是否允許連接")
    return None

if __name__ == "__main__":
    test_mysql_connection()
