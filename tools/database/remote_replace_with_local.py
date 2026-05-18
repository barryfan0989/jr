import os
import time
import json
import mysql.connector
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / '爬蟲資料' / '整理後'
OUT_JSON = OUT_DIR / 'concerts_merged.json'

DB_CONFIG = dict(
    host='ticketdb-ticket63.f.aivencloud.com',
    port=13599,
    user='avnadmin',
    password='AVNS_QqNVFqacdQinAgGmXY9',
    database='defaultdb',
)


def dump_remote_sql(conn, out_path: Path):
    cur = conn.cursor()
    cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s", (DB_CONFIG['database'],))
    tables = [r[0] for r in cur.fetchall()]
    with out_path.open('w', encoding='utf-8') as f:
        f.write(f"-- Dump of database {DB_CONFIG['database']}\n-- Generated: {time.ctime()}\n\n")
        for t in tables:
            cur.execute(f"SHOW CREATE TABLE `{t}`")
            row = cur.fetchone()
            create_sql = row[1]
            f.write(f"DROP TABLE IF EXISTS `{t}`;\n")
            f.write(create_sql + ";\n\n")

            cur.execute(f"SELECT * FROM `{t}`")
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            if not rows:
                continue
            for r in rows:
                vals = []
                for v in r:
                    if v is None:
                        vals.append('NULL')
                    else:
                        escaped = str(v).replace("\\", "\\\\").replace("'", "\\'")
                        vals.append(f"'{escaped}'")
                f.write(f"INSERT INTO `{t}` (`{'`,`'.join(cols)}`) VALUES ({', '.join(vals)});\n")
            f.write('\n')
    cur.close()


def drop_all_tables(conn):
    cur = conn.cursor()
    cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s", (DB_CONFIG['database'],))
    tables = [r[0] for r in cur.fetchall()]
    cur.execute('SET FOREIGN_KEY_CHECKS=0')
    for t in tables:
        cur.execute(f"DROP TABLE IF EXISTS `{t}`")
    cur.execute('SET FOREIGN_KEY_CHECKS=1')
    conn.commit()
    cur.close()


def ensure_local_merged_json():
    # run build_unified_database.py to produce concerts_merged.json
    script = ROOT / 'tools' / 'database' / 'build_unified_database.py'
    subprocess.run([os.path.join('.', '.venv', 'Scripts', 'python.exe'), str(script)], check=True)


def create_and_import_concerts(conn, json_path: Path):
    with json_path.open('r', encoding='utf-8') as f:
        records = json.load(f)

    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE concerts (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        來源網站 TEXT,
        活動名稱 TEXT,
        藝人 TEXT,
        搶票時間 TEXT,
        活動時間 TEXT,
        活動地點 TEXT,
        活動地址 TEXT,
        票價 TEXT,
        票種 TEXT,
        網址 TEXT,
        爬取時間 TEXT,
        資料來源檔 TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    ''')

    inserted = 0
    for row in records:
        vals = (
            row.get('來源網站'),
            row.get('活動名稱'),
            row.get('藝人'),
            row.get('搶票時間'),
            row.get('活動時間'),
            row.get('活動地點'),
            row.get('活動地址'),
            row.get('票價'),
            row.get('票種'),
            row.get('網址'),
            row.get('爬取時間'),
            row.get('資料來源檔'),
        )
        cur.execute(
            "INSERT INTO concerts (來源網站,活動名稱,藝人,搶票時間,活動時間,活動地點,活動地址,票價,票種,網址,爬取時間,資料來源檔) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            vals,
        )
        inserted += cur.rowcount
    conn.commit()
    cur.close()
    return inserted


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    ts = time.strftime('%Y%m%d_%H%M%S')
    backup_path = Path.cwd() / f'remote_backup_{ts}.sql'

    print('Dumping remote DB to', backup_path)
    dump_remote_sql(conn, backup_path)
    print('Dump complete.')

    print('Dropping all remote tables...')
    drop_all_tables(conn)
    print('Dropped.')

    print('Building local merged JSON...')
    ensure_local_merged_json()
    if not OUT_JSON.exists():
        raise SystemExit('Local merged JSON not found')
    print('Local merged JSON ready:', OUT_JSON)

    print('Importing local concerts into remote...')
    inserted = create_and_import_concerts(conn, OUT_JSON)
    print('Inserted records:', inserted)

    conn.close()
    print('Remote replace completed. Backup:', backup_path)


if __name__ == '__main__':
    main()
