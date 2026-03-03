"""
MySQL 資料庫查看器（互動式）
"""
import mysql.connector
from mysql.connector import Error
import getpass

def connect_and_view():
    """連接並查看 MySQL 資料庫"""
    print("=" * 60)
    print("🎵 MySQL 演唱會資料庫查看器")
    print("=" * 60)
    
    # 輸入連接資訊
    print("\n請輸入 MySQL 連接資訊：")
    host = input("主機 (Enter=localhost): ").strip() or "localhost"
    port = input("埠號 (Enter=3306): ").strip() or "3306"
    user = input("使用者 (Enter=root): ").strip() or "root"
    password = getpass.getpass("密碼: ")
    
    try:
        print(f"\n🔗 正在連接 {user}@{host}:{port}...")
        
        # 先連接不指定資料庫
        connection = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        
        if connection.is_connected():
            print(f"✅ 連接成功！")
            cursor = connection.cursor()
            
            # 檢查是否有 concerts 資料庫
            cursor.execute("SHOW DATABASES LIKE 'concerts'")
            result = cursor.fetchone()
            
            if not result:
                print("\n⚠️  'concerts' 資料庫不存在！")
                create = input("\n是否要建立資料庫並匯入資料？(y/n): ").lower()
                
                if create == 'y':
                    print("\n正在建立資料庫...")
                    cursor.execute("CREATE DATABASE concerts DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    print("✅ 資料庫建立成功！")
                    print("\n請執行以下指令匯入資料：")
                    print(f"  python json_to_mysql.py --host {host} --port {port} --user {user} --password [密碼]")
                else:
                    print("\n取消操作")
                cursor.close()
                connection.close()
                return
            
            # 切換到 concerts 資料庫
            cursor.execute("USE concerts")
            
            # 顯示統計資訊
            print("\n" + "=" * 60)
            print("📊 資料庫統計")
            print("=" * 60)
            
            cursor.execute("SELECT COUNT(*) FROM events")
            total_count = cursor.fetchone()[0]
            print(f"總活動數: {total_count:,} 筆")
            
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
                print(f"  • {source or 'Unknown'}: {count:,} 筆")
            
            # 最近的活動
            print("\n" + "=" * 60)
            print("🎵 最近匯入的 10 筆活動：")
            print("=" * 60)
            cursor.execute("""
                SELECT artist, event_time, venue, source, url
                FROM events 
                ORDER BY id DESC 
                LIMIT 10
            """)
            events = cursor.fetchall()
            for i, (artist, event_time, venue, source, url) in enumerate(events, 1):
                print(f"\n{i}. {artist or '未知'}")
                print(f"   時間: {event_time or '未公布'}")
                print(f"   地點: {venue or '未公布'}")
                print(f"   來源: {source or 'Unknown'}")
                if url:
                    print(f"   網址: {url}")
            
            # 匯入記錄
            print("\n" + "=" * 60)
            print("📝 最近的匯入記錄：")
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
                print(f"\n  📄 {source_file}")
                print(f"     時間: {imported_at}")
                print(f"     新增: {inserted_count}/{record_count} 筆")
            
            cursor.close()
            connection.close()
            
            print("\n" + "=" * 60)
            print("✅ 查看完成！")
            print("=" * 60)
            
            # 詢問是否啟動網頁查看器
            print("\n💡 提示：你也可以使用網頁介面查看資料庫")
            web = input("是否啟動網頁查看器？(y/n): ").lower()
            if web == 'y':
                print("\n正在啟動網頁查看器...")
                print("建立網頁版本需要修改程式碼，請稍後...")
            
    except Error as e:
        print(f"\n❌ 錯誤: {e}")
        print("\n請檢查：")
        print("  1. MySQL 服務是否已啟動")
        print("  2. 使用者名稱和密碼是否正確")
        print("  3. 使用者是否有足夠的權限")

if __name__ == "__main__":
    try:
        connect_and_view()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n發生錯誤: {e}")
