"""
互動式 MySQL 資料匯入工具
"""
import mysql.connector
from mysql.connector import Error
import getpass
import glob
import json
import os
from datetime import datetime

def import_to_mysql():
    """互動式匯入資料到 MySQL"""
    print("=" * 70)
    print("📥 演唱會資料匯入工具 (MySQL)")
    print("=" * 70)
    
    # 輸入連接資訊
    print("\n請輸入 MySQL 連接資訊：")
    host = input("主機 (Enter=localhost): ").strip() or "localhost"
    port = input("埠號 (Enter=3306): ").strip() or "3306"
    user = input("使用者 (Enter=root): ").strip() or "root"
    password = getpass.getpass("密碼: ")
    database = input("資料庫名稱 (Enter=concerts): ").strip() or "concerts"
    
    try:
        print(f"\n🔗 正在連接 {user}@{host}:{port}...")
        
        # 連接
        connection = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            autocommit=False
        )
        
        if connection.is_connected():
            print("✅ 連接成功！")
            cursor = connection.cursor()
            
            # 查詢現有資料量
            cursor.execute("SELECT COUNT(*) FROM events")
            current_count = cursor.fetchone()[0]
            print(f"\n目前資料庫中有 {current_count:,} 筆活動")
            
            # 找到所有 JSON 檔案
            json_files = []
            patterns = ["all_events_*.json", "演唱會資訊彙整_*.json"]
            for pattern in patterns:
                json_files.extend(glob.glob(pattern))
            
            json_files = sorted(set(json_files), reverse=True)  # 最新的在前面
            
            if not json_files:
                print("\n⚠️  找不到 JSON 檔案")
                return
            
            print(f"\n📄 找到 {len(json_files)} 個 JSON 檔案")
            print("\n要匯入哪些檔案？")
            print("  1. 最新的一個檔案")
            print("  2. 全部檔案")
            print("  3. 最新的 5 個檔案")
            
            choice = input("\n請選擇 (1/2/3): ").strip() or "1"
            
            if choice == "1":
                files_to_import = json_files[:1]
            elif choice == "3":
                files_to_import = json_files[:5]
            else:
                files_to_import = json_files
            
            print(f"\n準備匯入 {len(files_to_import)} 個檔案...")
            
            total_inserted = 0
            total_skipped = 0
            
            for i, file_path in enumerate(files_to_import, 1):
                print(f"\n[{i}/{len(files_to_import)}] 處理: {os.path.basename(file_path)}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 解析資料
                records = []
                if isinstance(data, list):
                    records = [item for item in data if isinstance(item, dict)]
                elif isinstance(data, dict):
                    for key in ["data", "records", "items"]:
                        if key in data and isinstance(data[key], list):
                            records = [item for item in data[key] if isinstance(item, dict)]
                            break
                
                if not records:
                    print(f"  ⚠️  無資料")
                    continue
                
                inserted = 0
                for record in records:
                    source = record.get("來源網站")
                    artist = record.get("演出藝人")
                    event_time = record.get("演出時間")
                    venue = record.get("演出地點")
                    price = record.get("票價")
                    url = record.get("網址")
                    scraped_at = record.get("爬取時間")
                    
                    try:
                        cursor.execute("""
                            INSERT IGNORE INTO events 
                            (source, artist, event_time, venue, price, url, scraped_at, source_file, raw_json)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            source, artist, event_time, venue, price, url, 
                            scraped_at, os.path.basename(file_path),
                            json.dumps(record, ensure_ascii=False)
                        ))
                        
                        if cursor.rowcount:
                            inserted += 1
                    except Exception as e:
                        print(f"  ❌ 匯入失敗: {e}")
                        continue
                
                skipped = len(records) - inserted
                total_inserted += inserted
                total_skipped += skipped
                
                print(f"  ✅ 新增: {inserted} 筆, 略過: {skipped} 筆")
                
                # 記錄匯入log
                cursor.execute("""
                    INSERT INTO import_log 
                    (source_file, imported_at, record_count, inserted_count, skipped_count)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    os.path.basename(file_path),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    len(records),
                    inserted,
                    skipped
                ))
            
            connection.commit()
            
            # 最終統計
            cursor.execute("SELECT COUNT(*) FROM events")
            final_count = cursor.fetchone()[0]
            
            print("\n" + "=" * 70)
            print("✅ 匯入完成！")
            print("=" * 70)
            print(f"\n總計新增: {total_inserted:,} 筆")
            print(f"總計略過: {total_skipped:,} 筆（重複資料）")
            print(f"資料庫總數: {final_count:,} 筆")
            
            # 顯示來源統計
            print("\n📊 各來源統計：")
            cursor.execute("""
                SELECT source, COUNT(*) as cnt 
                FROM events 
                GROUP BY source 
                ORDER BY cnt DESC
            """)
            sources = cursor.fetchall()
            for source, count in sources:
                print(f"  • {source or 'Unknown'}: {count:,} 筆")
            
            cursor.close()
            connection.close()
            
            print("\n" + "=" * 70)
            print("💡 現在可以在 MySQL Workbench 重新查詢資料了！")
            print("   執行: SELECT * FROM events ORDER BY id DESC LIMIT 100;")
            print("=" * 70)
            
    except Error as e:
        print(f"\n❌ 錯誤: {e}")
        print("\n請檢查連接資訊和密碼是否正確")

if __name__ == "__main__":
    try:
        import_to_mysql()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n發生錯誤: {e}")
