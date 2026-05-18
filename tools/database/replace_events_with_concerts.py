import mysql.connector
from pathlib import Path

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

    # 確認 concerts 存在
    cur.execute("SHOW TABLES LIKE 'concerts'")
    if not cur.fetchall():
        raise SystemExit('concerts table not found on remote')

    # 1) 清空 events（保險起見先刪除再建立）
    cur.execute("DROP TABLE IF EXISTS `events_old_backup`")
    cur.execute("CREATE TABLE IF NOT EXISTS events_old_backup LIKE events")
    cur.execute("INSERT INTO events_old_backup SELECT * FROM events")
    conn.commit()

    cur.execute('SET FOREIGN_KEY_CHECKS=0')
    cur.execute('TRUNCATE TABLE events')
    conn.commit()

    # 2) 將 concerts 的資料插入 events（欄位對應相同）
    cur.execute("SHOW COLUMNS FROM concerts")
    concert_cols = [r[0] for r in cur.fetchall()]

    # 只插入共有的欄位
    cur.execute("SHOW COLUMNS FROM events")
    event_cols = [r[0] for r in cur.fetchall()]

    common = [c for c in concert_cols if c in event_cols]
    if not common:
        raise SystemExit('No common columns between concerts and events')

    cols_sql = ','.join(f'`{c}`' for c in common)
    insert_sql = f"INSERT INTO events ({cols_sql}) SELECT {cols_sql} FROM concerts"
    cur.execute(insert_sql)
    conn.commit()

    # 3) 重設 events 的 AUTO_INCREMENT
    cur.execute("SELECT COALESCE(MAX(id),0) FROM events")
    maxid = cur.fetchone()[0]
    nextval = maxid + 1
    cur.execute(f"ALTER TABLE events AUTO_INCREMENT = {nextval}")
    conn.commit()

    cur.close()
    conn.close()
    print('Replace completed. Inserted rows into events and reset AUTO_INCREMENT to', nextval)


if __name__ == '__main__':
    main()
