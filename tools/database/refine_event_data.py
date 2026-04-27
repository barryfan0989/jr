# -*- coding: utf-8 -*-
"""
細分現有演唱會資料 - 將粗糙的 events 表切割為多個細分表
"""

import mysql.connector
import re
import os
from datetime import datetime
from pathlib import Path

DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "barry0803"),
    database=os.getenv("DB_NAME", "concerts"),
    charset="utf8mb4",
    collation="utf8mb4_unicode_ci",
    autocommit=False,
    ssl_verify_cert=False,
    ssl_verify_identity=False,
)


def create_refined_tables(cur):
    """建立細分表"""
    print("建立細分表...")

    # 演出時間表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_schedules (
            schedule_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            event_id BIGINT UNSIGNED NOT NULL,
            performance_date DATE,
            start_time TIME,
            end_time TIME,
            door_open_time TIME,
            venue_notes VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_schedule_event FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("  ✓ event_schedules")

    # 票價階級表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ticket_pricing (
            price_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            event_id BIGINT UNSIGNED NOT NULL,
            tier_name VARCHAR(100),
            price_amount DECIMAL(10, 0),
            max_quantity INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_pricing_event FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("  ✓ ticket_pricing")

    # 購票管道時間表
    cur.execute("""
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
            CONSTRAINT fk_channel_event FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("  ✓ sales_channels")

    # 場地位置細分
    cur.execute("""
        CREATE TABLE IF NOT EXISTS venue_locations (
            location_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            venue_id BIGINT UNSIGNED NOT NULL,
            city VARCHAR(100),
            district VARCHAR(100),
            street VARCHAR(255),
            postal_code VARCHAR(20),
            venue_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_location_venue FOREIGN KEY (venue_id) REFERENCES venues(venue_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("  ✓ venue_locations")


def parse_event_time(time_str):
    """解析活動時間字串 - 提取日期和時間"""
    if not time_str or time_str == '未提供':
        return None, None

    # 嘗試幾個正則模式
    patterns = [
        r'(\d{4})/(\d{2})/(\d{2})\(.\)(\d{1,2}):(\d{2})',  # 2026/05/30(五)14:30
        r'(\d{4})/(\d{2})/(\d{2})\s(\d{1,2}):(\d{2})',      # 2026/05/30 14:30
        r'(\d{2})/(\d{2})\(.\)(\d{1,2}):(\d{2})',           # 05/30(五)14:30
        r'(\d{2})/(\d{2})\s(\d{1,2}):(\d{2})',              # 05/30 14:30
        r'(\d{1,2})/(\d{1,2})\s(\d{1,2}):(\d{2})',          # 5/30 14:30
    ]

    for pattern in patterns:
        match = re.search(pattern, time_str)
        if match:
            groups = match.groups()
            if len(groups) == 5 and len(groups[0]) == 4:  # 年月日時分
                year, month, day, hour, minute = groups
            elif len(groups) == 4 and len(groups[0]) == 2:  # 月日時分 (需補年份)
                year = 2026
                month, day, hour, minute = groups
            else:
                continue
            try:
                date_str = f"2026-{int(month):02d}-{int(day):02d}"
                time_str = f"{int(hour):02d}:{int(minute):02d}:00"
                return date_str, time_str
            except:
                continue
    
    return None, None


def parse_prices(price_str):
    """解析票價字串 - 提取各級價格"""
    if not price_str or price_str == '未提供':
        return []

    prices = []
    # 分割多個價格
    parts = price_str.split('/')
    for i, part in enumerate(parts):
        part = part.strip()
        # 提取數字
        match = re.search(r'(\d+)', part)
        if match:
            price = int(match.group(1))
            tier_name = f"Tier {i+1}"
            prices.append({
                'tier_name': tier_name,
                'price': price,
                'sequence': i
            })
    
    return prices


def parse_sales_time(sale_str):
    """解析搶票時間 - 提取日期、時間、平台"""
    if not sale_str or sale_str == '未提供':
        return None

    # 簡單模式
    patterns = [
        r'(\d{4})/(\d{2})/(\d{2})\(.\)(\d{1,2}):(\d{2})',
        r'(\d{1,2})/(\d{1,2})\(.\)(\d{1,2}):(\d{2})',
    ]

    for pattern in patterns:
        match = re.search(pattern, sale_str)
        if match:
            return match.group(0)
    
    return None


def migrate_data(cur):
    """遷移現有數據到細分表"""
    print("\n遷移數據到細分表...")

    # 讀取所有 events
    cur.execute("SELECT event_id, venue_id, `活動時間`, `票價`, `搶票時間`, `活動地點`, `活動地址` FROM events")
    events = cur.fetchall()
    print(f"  讀取 {len(events)} 筆事件")

    schedule_count = 0
    pricing_count = 0
    channel_count = 0

    for event_id, venue_id, event_time_str, price_str, sale_time_str, venue_name, address in events:
        # 1. 解析演出時間
        if event_time_str and event_time_str != '未提供':
            perf_date, perf_time = parse_event_time(event_time_str)
            if perf_date and perf_time:
                cur.execute(
                    "INSERT INTO event_schedules (event_id, performance_date, start_time, venue_notes) VALUES (%s, %s, %s, %s)",
                    (event_id, perf_date, perf_time, venue_name)
                )
                schedule_count += 1

        # 2. 解析票價
        if price_str and price_str != '未提供':
            prices = parse_prices(price_str)
            for p in prices:
                cur.execute(
                    "INSERT INTO ticket_pricing (event_id, tier_name, price_amount) VALUES (%s, %s, %s)",
                    (event_id, p['tier_name'], p['price'])
                )
                pricing_count += 1

        # 3. 解析購票時間
        if sale_time_str and sale_time_str != '未提供':
            sale_date, sale_time = parse_event_time(sale_time_str)
            if sale_date and sale_time:
                cur.execute(
                    "INSERT INTO sales_channels (event_id, platform, channel_type, start_date, start_time) VALUES (%s, %s, %s, %s, %s)",
                    (event_id, "TicketCom", "presale", sale_date, sale_time)
                )
                channel_count += 1

        # 4. 解析場地位置
        if address and address != '未提供':
            # 簡單的城市提取
            city = "未知"
            if '台北' in address or 'taipei' in address.lower():
                city = "台北市"
            elif '台中' in address or 'taichung' in address.lower():
                city = "台中市"
            elif '高雄' in address or 'kaohsiung' in address.lower():
                city = "高雄市"
            elif '桃園' in address:
                city = "桃園市"
            elif '新竹' in address:
                city = "新竹市"
            elif '台南' in address or 'tainan' in address.lower():
                city = "台南市"

            # 檢查是否已有此場地位置紀錄
            cur.execute("SELECT COUNT(*) FROM venue_locations WHERE venue_id = %s", (venue_id,))
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO venue_locations (venue_id, city, street) VALUES (%s, %s, %s)",
                    (venue_id, city, address)
                )

    return schedule_count, pricing_count, channel_count


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        print("="*60)
        print("開始細分演唱會資料")
        print("="*60)

        create_refined_tables(cur)
        conn.commit()

        schedule_cnt, pricing_cnt, channel_cnt = migrate_data(cur)
        conn.commit()

        print(f"\n✅ 遷移完成:")
        print(f"  - event_schedules: {schedule_cnt} 筆")
        print(f"  - ticket_pricing: {pricing_cnt} 筆")
        print(f"  - sales_channels: {channel_cnt} 筆")

        # 驗證
        print("\n驗證新表:")
        cur.execute("SELECT COUNT(*) FROM event_schedules")
        print(f"  - event_schedules: {cur.fetchone()[0]} 筆 ✓")
        cur.execute("SELECT COUNT(*) FROM ticket_pricing")
        print(f"  - ticket_pricing: {cur.fetchone()[0]} 筆 ✓")
        cur.execute("SELECT COUNT(*) FROM sales_channels")
        print(f"  - sales_channels: {cur.fetchone()[0]} 筆 ✓")
        cur.execute("SELECT COUNT(*) FROM venue_locations")
        print(f"  - venue_locations: {cur.fetchone()[0]} 筆 ✓")

        print("\n✅ 細分完成！")

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
