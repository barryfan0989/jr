import mysql.connector

DB_CONFIG = dict(
    host='ticketdb-ticket63.f.aivencloud.com',
    port=13599,
    user='avnadmin',
    password='AVNS_QqNVFqacdQinAgGmXY9',
    database='defaultdb',
)

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 檢查 concerts
    cur.execute("SHOW TABLES LIKE 'concerts'")
    if not cur.fetchall():
        raise SystemExit('concerts table not found on remote')

    # 如果 events 不存在，建立為 concerts 的結構
    cur.execute("SHOW TABLES LIKE 'events'")
    if not cur.fetchall():
        cur.execute("CREATE TABLE events LIKE concerts")
        conn.commit()

    # 清空 events（保證只留下新資料）
    cur.execute("TRUNCATE TABLE events")
    conn.commit()

    # 插入資料
    cur.execute("INSERT INTO events SELECT * FROM concerts")
    conn.commit()

    # 重設自增
    cur.execute("SELECT COALESCE(MAX(id),0) FROM events")
    maxid = cur.fetchone()[0]
    nextval = maxid + 1
    cur.execute(f"ALTER TABLE events AUTO_INCREMENT = {nextval}")
    conn.commit()

    cur.close()
    conn.close()
    print('events created from concerts. rows moved:', maxid)

if __name__ == '__main__':
    main()
