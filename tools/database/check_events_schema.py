import os
import mysql.connector

host = os.getenv('CHECK_DB_HOST', 'ticketdb-ticket63.f.aivencloud.com')
port = int(os.getenv('CHECK_DB_PORT', '13599'))
user = os.getenv('CHECK_DB_USER', 'avnadmin')
password = os.getenv('CHECK_DB_PASSWORD', 'AVNS_QqNVFqacdQinAgGmXY9')
db = os.getenv('CHECK_DB_NAME', 'defaultdb')

def main():
    conn = mysql.connector.connect(host=host, port=port, user=user, password=password, database=db)
    cur = conn.cursor()
    cur.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='events'", (db,))
    rows = cur.fetchall()
    if not rows:
        print('events table not found in', db)
    else:
        print('columns in events:')
        for r in rows:
            print(r[0], r[1])
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
