#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backfill Chinese mirror tables from their English source tables."""
import os
import mysql.connector

DB_CONFIG = dict(
    host=os.getenv('DB_HOST', 'ticketdb-ticket63.f.aivencloud.com'),
    port=int(os.getenv('DB_PORT', '13599')),
    user=os.getenv('DB_USER', 'avnadmin'),
    password=os.getenv('DB_PASSWORD', 'AVNS_QqNVFqacdQinAgGmXY9'),
    database=os.getenv('DB_NAME', 'defaultdb'),
    charset='utf8mb4',
    autocommit=False,
)

MAPPINGS = [
    ('events', '活動'),
    ('venue_locations', '活動地點'),
    ('sales_channels', '售票平台'),
    ('artists', '藝人'),
    ('users', '使用者'),
]


def table_exists(cur, db, table):
    cur.execute(
        'SELECT COUNT(1) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s',
        (db, table),
    )
    return cur.fetchone()[0] > 0


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        cur.execute('SET FOREIGN_KEY_CHECKS=0')
        for eng, chi in MAPPINGS:
            if not table_exists(cur, DB_CONFIG['database'], eng):
                print(f'skip {eng} -> {chi}: source missing')
                continue

            if not table_exists(cur, DB_CONFIG['database'], chi):
                print(f'create {chi} from {eng}')
                cur.execute(f'CREATE TABLE `{chi}` LIKE `{eng}`')

            print(f'backfill {chi} from {eng}')
            cur.execute(f'TRUNCATE TABLE `{chi}`')
            cur.execute(f'INSERT INTO `{chi}` SELECT * FROM `{eng}`')
            print(f'  rows={cur.rowcount}')

        conn.commit()
        print('done')
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.execute('SET FOREIGN_KEY_CHECKS=1')
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
