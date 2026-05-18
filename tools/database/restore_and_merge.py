import mysql.connector
from pathlib import Path
import time
import json
from datetime import datetime

DB_CONFIG = dict(
    host='ticketdb-ticket63.f.aivencloud.com',
    port=13599,
    user='avnadmin',
    password='AVNS_QqNVFqacdQinAgGmXY9',
    database='defaultdb',
)

BACKUP_PATH = Path.cwd() / 'remote_backup_20260518_214226.sql'
LOCAL_JSON = Path.cwd() / '爬蟲資料' / '整理後' / 'concerts_merged.json'

# heuristics for parsing sale_time strings
DATE_FORMATS = [
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y/%m/%d %H:%M:%S',
    '%Y/%m/%d %H:%M',
    '%Y.%m.%d %H:%M',
    '%Y.%m.%d %H:%M:%S',
    '%Y/%m/%d',
    '%Y-%m-%d',
]


def exec_sql_file(conn, sql_path: Path):
    cur = conn.cursor()
    stmt = ''
    with sql_path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('--') or line.startswith('/*'):
                continue
            stmt += ' ' + line
            if line.endswith(';'):
                try:
                    cur.execute(stmt)
                except Exception as e:
                    print('Warning executing statement:', e)
                stmt = ''
    conn.commit()
    cur.close()


def parse_date_try(s: str):
    if not s:
        return None
    s = s.strip()
    # remove common trailing notes
    s = s.replace('（FRI）', '').replace('（SAT）', '')
    s = s.replace('（', ' ').replace('）', ' ')
    s = s.replace('\u3000', ' ')
    # Try numeric formats
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    # try extracting YYYY/MM/DD pattern
    import re
    m = re.search(r'(\d{4}[./-]\d{1,2}[./-]\d{1,2})', s)
    if m:
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d']:
            try:
                return datetime.strptime(m.group(1), fmt)
            except Exception:
                pass
    return None


def upsert_local_to_events(conn, json_path: Path):
    with json_path.open('r', encoding='utf-8') as f:
        records = json.load(f)

    cur = conn.cursor()
    # get events columns
    cur.execute("SHOW COLUMNS FROM events")
    event_cols = [r[0] for r in cur.fetchall()]

    inserted = 0
    updated = 0
    for r in records:
        # map common fields
        data = {
            '來源網站': r.get('來源網站'),
            '活動名稱': r.get('活動名稱'),
            '藝人': r.get('藝人'),
            '搶票時間': r.get('搶票時間'),
            '活動時間': r.get('活動時間'),
            '活動地點': r.get('活動地點'),
            '活動地址': r.get('活動地址'),
            '票價': r.get('票價'),
            '票種': r.get('票種'),
            '網址': r.get('網址'),
            '爬取時間': r.get('爬取時間'),
            '資料來源檔': r.get('資料來源檔'),
        }
        # build insert columns that exist in events
        cols = [c for c in data.keys() if c in event_cols]
        vals = [data[c] for c in cols]
        url = data.get('網址')
        if url:
            cur.execute('SELECT id FROM events WHERE 網址=%s', (url,))
            row = cur.fetchone()
            if row:
                # update
                sets = ','.join(f'`{c}`=%s' for c in cols)
                sql = f'UPDATE events SET {sets} WHERE id=%s'
                cur.execute(sql, vals + [row[0]])
                updated += 1
            else:
                placeholders = ','.join(['%s'] * len(cols))
                sql = f'INSERT INTO events (`' + '`,`'.join(cols) + f'`) VALUES ({placeholders})'
                cur.execute(sql, vals)
                inserted += 1
        else:
            # no URL: insert based on name+time+venue uniqueness
            cur.execute('SELECT id FROM events WHERE 活動名稱=%s AND 活動時間=%s AND 活動地點=%s',
                        (data.get('活動名稱'), data.get('活動時間'), data.get('活動地點')))
            row = cur.fetchone()
            if row:
                sets = ','.join(f'`{c}`=%s' for c in cols)
                sql = f'UPDATE events SET {sets} WHERE id=%s'
                cur.execute(sql, vals + [row[0]])
                updated += 1
            else:
                placeholders = ','.join(['%s'] * len(cols))
                sql = f'INSERT INTO events (`' + '`,`'.join(cols) + f'`) VALUES ({placeholders})'
                cur.execute(sql, vals)
                inserted += 1
    conn.commit()
    cur.close()
    return inserted, updated


def delete_expired_sale_time(conn):
    cur = conn.cursor()
    cur.execute('SELECT id, 搶票時間 FROM events WHERE 搶票時間 IS NOT NULL AND 搶票時間<>"未提供" AND 搶票時間<>""')
    rows = cur.fetchall()
    now = datetime.now()
    to_delete = []
    for id_, s in rows:
        dt = parse_date_try(str(s))
        if dt and dt < now:
            to_delete.append(id_)
    deleted = 0
    if to_delete:
        # chunk deletes
        for i in range(0, len(to_delete), 200):
            chunk = to_delete[i:i+200]
            q = 'DELETE FROM events WHERE id IN (%s)' % ','.join(['%s']*len(chunk)
                                                                  )
            cur.execute(q, tuple(chunk))
            deleted += cur.rowcount
        conn.commit()
    cur.close()
    return deleted


def main():
    if not BACKUP_PATH.exists():
        raise SystemExit('Backup SQL not found: ' + str(BACKUP_PATH))
    if not LOCAL_JSON.exists():
        raise SystemExit('Local merged JSON not found: ' + str(LOCAL_JSON))

    conn = mysql.connector.connect(**DB_CONFIG)

    print('Restoring backup SQL...')
    exec_sql_file(conn, BACKUP_PATH)
    print('Restore complete.')

    # ensure events exists
    cur = conn.cursor()
    cur.execute("SHOW TABLES LIKE 'events'")
    if not cur.fetchall():
        print('events not found after restore; creating from concerts if available')
        cur.execute("SHOW TABLES LIKE 'concerts'")
        if cur.fetchall():
            cur.execute("CREATE TABLE events LIKE concerts")
            conn.commit()
    cur.close()

    print('Upserting local concerts into events...')
    ins, upd = upsert_local_to_events(conn, LOCAL_JSON)
    print('Inserted:', ins, 'Updated:', upd)

    print('Deleting expired sale_time entries...')
    deleted = delete_expired_sale_time(conn)
    print('Deleted expired rows:', deleted)

    conn.close()
    print('Done.')


if __name__ == '__main__':
    main()
