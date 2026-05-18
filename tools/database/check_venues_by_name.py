#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check specific venue names in the remote `venues` table."""
from __future__ import annotations
import mysql.connector
DB_CONFIG = dict(
    host='ticketdb-ticket63.f.aivencloud.com',
    port=13599,
    user='avnadmin',
    password='AVNS_QqNVFqacdQinAgGmXY9',
    database='defaultdb',
    charset='utf8mb4',
    autocommit=False,
)
NAMES = [
    '台北小巨蛋',
    '高雄國家體育場',
    '台北國際會議中心',
    'Zepp New Taipei',
    '台北小巨蛋（',
    '台北小巨蛋 (',
]

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    for name in NAMES:
        q = "SELECT venue_id, venue_name, venue_address FROM venues WHERE venue_name LIKE %s LIMIT 20"
        cur.execute(q, (name+'%',))
        rows = cur.fetchall()
        print('==', name, '==')
        if not rows:
            # try contains
            cur.execute("SELECT venue_id, venue_name, venue_address FROM venues WHERE venue_name LIKE %s LIMIT 20", ('%'+name+'%',))
            rows = cur.fetchall()
        for r in rows:
            print(r)
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
