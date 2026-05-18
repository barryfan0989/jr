# -*- coding: utf-8 -*-
"""
將本地 concerts 資料完整復原到遠端 Aiven defaultdb。

策略：
1. 先清空遠端核心表
2. 從本地複製核心資料
3. 以 events / venues 重新補齊 sales_channels / venue_locations
4. 驗證筆數
"""

from __future__ import annotations

import re

import mysql.connector

LOCAL_CONFIG = dict(
    host="127.0.0.1",
    user="root",
    password="barry0803",
    database="concerts",
    charset="utf8mb4",
    collation="utf8mb4_unicode_ci",
)

REMOTE_CONFIG = dict(
    host="ticketdb-ticket63.f.aivencloud.com",
    port=13599,
    user="avnadmin",
    password="AVNS_QqNVFqacdQinAgGmXY9",
    database="defaultdb",
    charset="utf8mb4",
    collation="utf8mb4_unicode_ci",
    ssl_verify_cert=False,
    ssl_verify_identity=False,
)

CORE_TABLES = [
    "artist_news",
    "artist_segments",
    "event_artists",
    "event_schedules",
    "event_segments",
    "ticket_pricing",
    "events",
    "artists",
    "venues",
]

OPTIONAL_TABLES = ["sales_channels", "venue_locations"]


def city_from_text(text: str) -> str:
    city_map = [
        ("台北", "台北市"), ("臺北", "台北市"), ("新北", "新北市"), ("桃園", "桃園市"),
        ("台中", "台中市"), ("臺中", "台中市"), ("台南", "台南市"), ("臺南", "台南市"),
        ("高雄", "高雄市"), ("基隆", "基隆市"), ("新竹", "新竹市"), ("嘉義", "嘉義市"),
        ("宜蘭", "宜蘭縣"), ("苗栗", "苗栗縣"), ("彰化", "彰化縣"), ("南投", "南投縣"),
        ("雲林", "雲林縣"), ("屏東", "屏東縣"), ("台東", "台東縣"), ("臺東", "台東縣"),
        ("花蓮", "花蓮縣"), ("澎湖", "澎湖縣"), ("金門", "金門縣"), ("連江", "連江縣"),
    ]
    for keyword, city in city_map:
        if keyword in text:
            return city
    return "未知"


def parse_sale_status(sale_text: str) -> str:
    if not sale_text or sale_text == "未提供":
        return "未提供"
    if "完售" in sale_text or "已售完" in sale_text:
        return "已售完"
    if "預售" in sale_text or "開賣" in sale_text or "即將" in sale_text:
        return "待開賣"
    return "販售中/未明"


def normalize_date(year: int, month: int, day: int) -> str | None:
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def ensure_tables_exist(cur):
    # 假設遠端已存在完整 schema；若部分表缺失則補建。
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_channels (
            channel_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            event_id BIGINT UNSIGNED NOT NULL,
            platform VARCHAR(100),
            channel_type VARCHAR(50),
            start_date DATE,
            start_time TIME,
            end_date DATE,
            end_time TIME,
            sales_status VARCHAR(50),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_sc_event FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS venue_locations (
            location_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            venue_id BIGINT UNSIGNED NOT NULL,
            city VARCHAR(100),
            district VARCHAR(100),
            street VARCHAR(255),
            postal_code VARCHAR(20),
            venue_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_vl_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def recreate_core_tables(cur):
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    for table in ["event_artists", "artist_news", "event_schedules", "ticket_pricing", "event_segments", "artist_segments", "events", "artists", "venues", "sales_channels", "venue_locations"]:
        cur.execute(f"DROP TABLE IF EXISTS `{table}`")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")

    # 與本地一致的核心結構
    cur.execute(
        """
        CREATE TABLE venues (
            venue_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            venue_name VARCHAR(255) NOT NULL,
            venue_address VARCHAR(255) NOT NULL,
            venue_intro LONGTEXT,
            intro_source_url VARCHAR(500) DEFAULT NULL,
            intro_updated_at DATETIME DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_venue_name_addr (venue_name, venue_address)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE artists (
            artist_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            artist_name VARCHAR(255) NOT NULL,
            artist_intro LONGTEXT,
            intro_source_url VARCHAR(500) DEFAULT NULL,
            intro_updated_at DATETIME DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_artist_name (artist_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE events (
            event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            venue_id BIGINT UNSIGNED DEFAULT NULL,
            `來源網站` TEXT,
            `活動名稱` TEXT,
            `藝人` TEXT,
            `搶票時間` TEXT,
            `活動時間` TEXT,
            `活動地點` TEXT,
            `活動地址` TEXT,
            `票價` TEXT,
            `票種` TEXT,
            `網址` TEXT,
            `爬取時間` TEXT,
            `資料來源檔` TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_events_venue
                FOREIGN KEY (venue_id) REFERENCES venues(venue_id)
                ON UPDATE CASCADE ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute("CREATE INDEX idx_events_source ON events(`來源網站`(64))")
    cur.execute(
        """
        CREATE TABLE event_artists (
            event_id BIGINT UNSIGNED NOT NULL,
            artist_id BIGINT UNSIGNED NOT NULL,
            role_name VARCHAR(100) NOT NULL DEFAULT 'main',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (event_id, artist_id),
            KEY fk_event_artists_artist (artist_id),
            CONSTRAINT fk_event_artists_event
                FOREIGN KEY (event_id) REFERENCES events(event_id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            CONSTRAINT fk_event_artists_artist
                FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
                ON UPDATE CASCADE ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE artist_news (
            news_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            artist_id BIGINT UNSIGNED NOT NULL,
            title VARCHAR(500) NOT NULL,
            summary TEXT,
            source_name VARCHAR(255) DEFAULT NULL,
            source_url VARCHAR(500) NOT NULL,
            published_at DATETIME DEFAULT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sentiment ENUM('positive', 'neutral', 'negative') DEFAULT 'neutral',
            UNIQUE KEY uq_artist_news_source_url (source_url),
            KEY idx_artist_news_artist_time (artist_id, published_at),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_artist_news_artist
                FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
                ON UPDATE CASCADE ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE artist_segments (
            artist_id BIGINT UNSIGNED PRIMARY KEY,
            artist_name VARCHAR(255) NOT NULL,
            region_group VARCHAR(50) NOT NULL,
            artist_form VARCHAR(50) NOT NULL,
            market_language VARCHAR(50) NOT NULL,
            confidence_score DECIMAL(4,2) NOT NULL,
            rule_trace VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_artist_segments_artist
              FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
              ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE event_segments (
            event_id BIGINT UNSIGNED PRIMARY KEY,
            event_name VARCHAR(500) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            price_band VARCHAR(50) NOT NULL,
            sale_status VARCHAR(50) NOT NULL,
            confidence_score DECIMAL(4,2) NOT NULL,
            rule_trace VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_event_segments_event
              FOREIGN KEY (event_id) REFERENCES events(event_id)
              ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE event_schedules (
            schedule_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            event_id BIGINT UNSIGNED NOT NULL,
            performance_date DATE,
            start_time TIME,
            end_time TIME,
            door_open_time TIME,
            venue_notes VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_es_event FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE ticket_pricing (
            price_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            event_id BIGINT UNSIGNED NOT NULL,
            tier_name VARCHAR(100),
            price_amount DECIMAL(10,0),
            max_quantity INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_tp_event FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    ensure_tables_exist(cur)


def copy_with_pk(cur_remote, cur_local, table, columns):
    placeholders = ', '.join(['%s'] * len(columns))
    cols_sql = ', '.join(f'`{c}`' for c in columns)
    cur_local.execute(f"SELECT {cols_sql} FROM `{table}`")
    rows = cur_local.fetchall()
    if not rows:
        return 0
    insert_sql = f"INSERT INTO `{table}` ({cols_sql}) VALUES ({placeholders})"
    cur_remote.executemany(insert_sql, rows)
    return len(rows)


def main():
    local = mysql.connector.connect(**LOCAL_CONFIG)
    remote = mysql.connector.connect(**REMOTE_CONFIG)
    lc = local.cursor()
    rc = remote.cursor()

    try:
        recreate_core_tables(rc)
        remote.commit()

        # copy core tables in dependency order
        counts = {}
        counts['venues'] = copy_with_pk(rc, lc, 'venues', [
            'venue_id', 'venue_name', 'venue_address', 'venue_intro',
            'intro_source_url', 'intro_updated_at', 'created_at', 'updated_at'
        ])
        remote.commit()

        counts['artists'] = copy_with_pk(rc, lc, 'artists', [
            'artist_id', 'artist_name', 'artist_intro', 'intro_source_url',
            'intro_updated_at', 'created_at', 'updated_at'
        ])
        remote.commit()

        counts['events'] = copy_with_pk(rc, lc, 'events', [
            'event_id', 'venue_id', '來源網站', '活動名稱', '藝人', '搶票時間',
            '活動時間', '活動地點', '活動地址', '票價', '票種', '網址',
            '爬取時間', '資料來源檔', 'created_at'
        ])
        remote.commit()

        counts['event_artists'] = copy_with_pk(rc, lc, 'event_artists', [
            'event_id', 'artist_id', 'role_name', 'created_at'
        ])
        remote.commit()

        counts['artist_news'] = copy_with_pk(rc, lc, 'artist_news', [
            'news_id', 'artist_id', 'title', 'summary', 'source_name',
            'source_url', 'published_at', 'fetched_at', 'sentiment'
        ])
        remote.commit()

        counts['artist_segments'] = copy_with_pk(rc, lc, 'artist_segments', [
            'artist_id', 'artist_name', 'region_group', 'artist_form',
            'market_language', 'confidence_score', 'rule_trace', 'created_at'
        ])
        remote.commit()

        counts['event_segments'] = copy_with_pk(rc, lc, 'event_segments', [
            'event_id', 'event_name', 'event_type', 'price_band', 'sale_status',
            'confidence_score', 'rule_trace', 'created_at'
        ])
        remote.commit()

        counts['event_schedules'] = copy_with_pk(rc, lc, 'event_schedules', [
            'schedule_id', 'event_id', 'performance_date', 'start_time', 'end_time',
            'door_open_time', 'venue_notes', 'created_at'
        ])
        remote.commit()

        counts['ticket_pricing'] = copy_with_pk(rc, lc, 'ticket_pricing', [
            'price_id', 'event_id', 'tier_name', 'price_amount', 'max_quantity', 'created_at'
        ])
        remote.commit()

        # rebuild venue_locations from venues
        rc.execute('DELETE FROM venue_locations')
        lc.execute('SELECT venue_id, venue_name, venue_address FROM venues')
        venues = lc.fetchall()
        vl_rows = []
        for venue_id, venue_name, addr in venues:
            text = f"{venue_name or ''} {addr or ''}"
            city = city_from_text(text)
            district = None
            m = re.search(r'([\u4e00-\u9fff]{2,3}[區鄉鎮市])', text)
            if m:
                district = m.group(1)
            vl_rows.append((venue_id, city, district, addr or '', venue_name or ''))
        if vl_rows:
            rc.executemany(
                "INSERT INTO venue_locations (venue_id, city, district, street, venue_details) VALUES (%s,%s,%s,%s,%s)",
                vl_rows,
            )
        counts['venue_locations'] = len(vl_rows)
        remote.commit()

        # rebuild sales_channels from events
        rc.execute('DELETE FROM sales_channels')
        lc.execute('SELECT event_id, `來源網站`, `搶票時間` FROM events')
        event_rows = lc.fetchall()
        sc_rows = []
        for event_id, source_site, sale_text in event_rows:
            sale_text = sale_text or ''
            status = parse_sale_status(sale_text)
            start_date = None
            start_time = None
            m1 = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', sale_text)
            if m1:
                y, m, d = m1.groups()
                start_date = normalize_date(int(y), int(m), int(d))
            else:
                m2 = re.search(r'(\d{1,2})/(\d{1,2})', sale_text)
                if m2:
                    m, d = m2.groups()
                    start_date = normalize_date(2026, int(m), int(d))
            mt = re.search(r'(\d{1,2}):(\d{2})', sale_text)
            if mt:
                hh, mm = mt.groups()
                start_time = f"{int(hh):02d}:{int(mm):02d}:00"
            sc_rows.append((event_id, source_site, 'general', start_date, start_time, status, sale_text[:1000]))
        if sc_rows:
            rc.executemany(
                "INSERT INTO sales_channels (event_id, platform, channel_type, start_date, start_time, sales_status, notes) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                sc_rows,
            )
        counts['sales_channels'] = len(sc_rows)
        remote.commit()

        # verify
        print('restore done')
        for k, v in counts.items():
            print(k, v)

        for t in ['artists','venues','events','event_artists','artist_news','artist_segments','event_segments','event_schedules','ticket_pricing','sales_channels','venue_locations']:
            rc.execute(f'SELECT COUNT(*) FROM `{t}`')
            print('verify', t, rc.fetchone()[0])

    except Exception as exc:
        remote.rollback()
        raise
    finally:
        lc.close()
        rc.close()
        local.close()
        remote.close()


if __name__ == '__main__':
    main()
