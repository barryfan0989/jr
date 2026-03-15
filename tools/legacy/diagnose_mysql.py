"""
MySQL 連接診斷工具
"""
import mysql.connector
from mysql.connector import Error

def diagnose_mysql():
    """診斷 MySQL 連接問題"""
    print("=" * 60)
    print("🔍 MySQL 連接診斷")
    print("=" * 60)
    
    test_configs = [
        {"user": "root", "password": "", "desc": "無密碼"},
        {"user": "root", "password": "root", "desc": "密碼: root"},
        {"user": "root", "password": "password", "desc": "密碼: password"},
        {"user": "root", "password": "mysql", "desc": "密碼: mysql"},
        {"user": "root", "password": "123456", "desc": "密碼: 123456"},
    ]
    
    for i, config in enumerate(test_configs, 1):
        print(f"\n測試 {i}: {config['desc']}")
        try:
            conn = mysql.connector.connect(
                host='localhost',
                port=3306,
                user=config['user'],
                password=config['password'],
                charset='utf8mb4'
            )
            
            if conn.is_connected():
                print(f"  ✅ 連接成功！")
                cursor = conn.cursor()
                
                # 檢查是否有 concerts 資料庫
                cursor.execute("SHOW DATABASES LIKE 'concerts'")
                has_db = cursor.fetchone()
                
                if has_db:
                    print(f"  ✅ 'concerts' 資料庫存在")
                    cursor.execute("USE concerts")
                    cursor.execute("SELECT COUNT(*) FROM events")
                    count = cursor.fetchone()[0]
                    print(f"  📊 活動數量: {count:,} 筆")
                else:
                    print(f"  ⚠️  'concerts' 資料庫不存在")
                
                cursor.close()
                conn.close()
                
                print("\n" + "=" * 60)
                print("🎉 找到可用的設定！")
                print("=" * 60)
                print(f"\n使用以下設定:")
                print(f"  主機: localhost")
                print(f"  埠號: 3306")
                print(f"  使用者: {config['user']}")
                print(f"  密碼: {config['password'] or '(空白)'}")
                
                if not has_db:
                    print(f"\n建立 concerts 資料庫:")
                    print(f"  python json_to_mysql.py --create-db --user {config['user']} --password {config['password']}")
                else:
                    print(f"\n啟動網頁查看器:")
                    print(f"  python view_mysql_web.py")
                    print(f"  然後輸入上述的使用者和密碼")
                
                return True
                
        except Error as e:
            print(f"  ❌ {e}")
            continue
    
    print("\n" + "=" * 60)
    print("❌ 所有測試都失敗")
    print("=" * 60)
    print("\n可能的原因:")
    print("  1. MySQL 密碼不在常見列表中")
    print("  2. root 使用者被停用")
    print("  3. MySQL 設定不允許 localhost 連接")
    print("\n建議:")
    print("  1. 使用 MySQL Workbench 查看已儲存的連接")
    print("  2. 或直接使用 SQLite (已經可用)")
    print("     → http://localhost:5555")
    
    return False

if __name__ == "__main__":
    diagnose_mysql()
