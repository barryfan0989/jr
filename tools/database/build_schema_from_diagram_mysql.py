# -*- coding: utf-8 -*-
"""
依照使用者提供的 ER 圖建立 MySQL 資料表（中文命名）並匯入資料。

資料表：
- 使用者
- 活動
- 活動地點
- 藝人
- 售票平台

欄位對應（依圖，鍵名英文化）：
- 使用者: user_id_pk, ID, 密碼
- 活動: event_id_pk, venue_id_fk, artist_id_fk, 活動名稱, 票價, 票種, 活動時間, 售票時間, 活動連結
- 活動地點: venue_id_pk, 場地名稱, 地址
- 藝人: artist_id_pk, event_id_fk, 藝人名稱
- 售票平台: platform_id_pk, event_id_fk, artist_id_fk, 平台名稱
"""

import json
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parents[2]
MERGED_JSON = ROOT / "爬蟲資料" / "整理後" / "concerts_merged.json"
USERS_JSON = ROOT / "data" / "users.json"

DB_CONFIG = dict(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="barry0803",
    database="concerts",
    charset="utf8mb4",
    collation="utf8mb4_unicode_ci",
    autocommit=False,
)


def clean(value, default="未提供") -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return default
    if text in {"未公布", "未知", "Unknown", "UNKNOWN"}:
        return default
    return text


def create_schema(cur):
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("DROP VIEW IF EXISTS `活動聯合檢視`")
    cur.execute("DROP TABLE IF EXISTS `售票平台`")
    cur.execute("DROP TABLE IF EXISTS `藝人`")
    cur.execute("DROP TABLE IF EXISTS `活動`")
    cur.execute("DROP TABLE IF EXISTS `活動地點`")
    cur.execute("DROP TABLE IF EXISTS `使用者`")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")

    cur.execute(
        """
        CREATE TABLE `使用者` (
            `user_id_pk` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            `ID` VARCHAR(120) NOT NULL,
            `密碼` TEXT NOT NULL,
            PRIMARY KEY (`user_id_pk`),
            UNIQUE KEY `uk_user_id` (`ID`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute(
        """
        CREATE TABLE `活動地點` (
            `venue_id_pk` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            `場地名稱` VARCHAR(255) NOT NULL,
            `地址` VARCHAR(255) NOT NULL,
            PRIMARY KEY (`venue_id_pk`),
            UNIQUE KEY `uk_venue` (`場地名稱`, `地址`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute(
        """
        CREATE TABLE `藝人` (
            `artist_id_pk` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            `event_id_fk` BIGINT UNSIGNED NULL,
            `藝人名稱` VARCHAR(255) NOT NULL,
            PRIMARY KEY (`artist_id_pk`),
            UNIQUE KEY `uk_artist_name` (`藝人名稱`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute(
        """
        CREATE TABLE `活動` (
            `event_id_pk` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            `venue_id_fk` BIGINT UNSIGNED NULL,
            `artist_id_fk` BIGINT UNSIGNED NULL,
            `活動名稱` VARCHAR(500) NOT NULL,
            `票價` TEXT NOT NULL,
            `票種` TEXT NOT NULL,
            `活動時間` TEXT NOT NULL,
            `售票時間` TEXT NOT NULL,
            `活動連結` TEXT NOT NULL,
            PRIMARY KEY (`event_id_pk`),
            CONSTRAINT `fk_event_venue` FOREIGN KEY (`venue_id_fk`)
                REFERENCES `活動地點` (`venue_id_pk`)
                ON UPDATE CASCADE ON DELETE SET NULL,
            CONSTRAINT `fk_event_artist` FOREIGN KEY (`artist_id_fk`)
                REFERENCES `藝人` (`artist_id_pk`)
                ON UPDATE CASCADE ON DELETE SET NULL,
            UNIQUE KEY `uk_event_dedupe` (`活動名稱`(255), `活動時間`(120), `venue_id_fk`, `artist_id_fk`, `活動連結`(255))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    cur.execute(
        """
        CREATE TABLE `售票平台` (
            `platform_id_pk` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            `event_id_fk` BIGINT UNSIGNED NULL,
            `artist_id_fk` BIGINT UNSIGNED NULL,
            `平台名稱` VARCHAR(255) NOT NULL,
            PRIMARY KEY (`platform_id_pk`),
            CONSTRAINT `fk_platform_event` FOREIGN KEY (`event_id_fk`)
                REFERENCES `活動` (`event_id_pk`)
                ON UPDATE CASCADE ON DELETE CASCADE,
            CONSTRAINT `fk_platform_artist` FOREIGN KEY (`artist_id_fk`)
                REFERENCES `藝人` (`artist_id_pk`)
                ON UPDATE CASCADE ON DELETE SET NULL,
            UNIQUE KEY `uk_platform_event_artist` (`平台名稱`, `event_id_fk`, `artist_id_fk`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )

    # 補上圖中的 藝人.event_id_fk 外鍵（活動表已建立後再加）
    cur.execute(
        """
        ALTER TABLE `藝人`
        ADD CONSTRAINT `fk_artist_event`
            FOREIGN KEY (`event_id_fk`)
            REFERENCES `活動` (`event_id_pk`)
            ON UPDATE CASCADE ON DELETE SET NULL
        """
    )


def create_views(cur):
    cur.execute(
        """
        CREATE VIEW `活動聯合檢視` AS
        SELECT
            a.`event_id_pk` AS `event_id_pk`,
            a.`活動名稱` AS `活動名稱`,
            r.`artist_id_pk` AS `artist_id_pk`,
            r.`藝人名稱` AS `藝人名稱`,
            v.`venue_id_pk` AS `venue_id_pk`,
            v.`場地名稱` AS `場地名稱`,
            v.`地址` AS `地址`,
            p.`platform_id_pk` AS `platform_id_pk`,
            p.`平台名稱` AS `平台名稱`,
            a.`票價` AS `票價`,
            a.`票種` AS `票種`,
            a.`活動時間` AS `活動時間`,
            a.`售票時間` AS `售票時間`,
            a.`活動連結` AS `活動連結`
        FROM `活動` a
        LEFT JOIN `藝人` r ON a.`artist_id_fk` = r.`artist_id_pk`
        LEFT JOIN `活動地點` v ON a.`venue_id_fk` = v.`venue_id_pk`
        LEFT JOIN `售票平台` p ON p.`event_id_fk` = a.`event_id_pk`
        """
    )


def get_or_create_venue(cur, cache, name, address):
    key = (clean(name), clean(address))
    if key in cache:
        return cache[key]
    cur.execute(
        "INSERT IGNORE INTO `活動地點` (`場地名稱`, `地址`) VALUES (%s, %s)",
        key,
    )
    cur.execute(
        "SELECT `venue_id_pk` FROM `活動地點` WHERE `場地名稱`=%s AND `地址`=%s",
        key,
    )
    venue_id = cur.fetchone()[0]
    cache[key] = venue_id
    return venue_id


def get_or_create_artist(cur, cache, artist_name):
    name = clean(artist_name)
    if name in cache:
        return cache[name]
    cur.execute("INSERT IGNORE INTO `藝人` (`藝人名稱`) VALUES (%s)", (name,))
    cur.execute("SELECT `artist_id_pk` FROM `藝人` WHERE `藝人名稱`=%s", (name,))
    artist_id = cur.fetchone()[0]
    cache[name] = artist_id
    return artist_id


def import_users(cur):
    if not USERS_JSON.exists():
        return 0
    raw = json.loads(USERS_JSON.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return 0

    inserted = 0
    for _, user in raw.items():
        user_id = clean(user.get("username") or user.get("email") or user.get("user_id"), "")
        password_hash = clean(user.get("password"), "")
        if not user_id:
            continue
        cur.execute(
            "INSERT IGNORE INTO `使用者` (`ID`, `密碼`) VALUES (%s, %s)",
            (user_id, password_hash),
        )
        inserted += cur.rowcount
    return inserted


def import_events(cur):
    if not MERGED_JSON.exists():
        raise SystemExit(f"找不到檔案: {MERGED_JSON}")

    rows = json.loads(MERGED_JSON.read_text(encoding="utf-8"))
    venue_cache = {}
    artist_cache = {}

    inserted_events = 0
    inserted_platform_rows = 0

    for row in rows:
        venue_id = get_or_create_venue(cur, venue_cache, row.get("活動地點"), row.get("活動地址"))
        artist_id = get_or_create_artist(cur, artist_cache, row.get("藝人"))

        cur.execute(
            """
            INSERT IGNORE INTO `活動` (
                `venue_id_fk`, `artist_id_fk`, `活動名稱`, `票價`, `票種`,
                `活動時間`, `售票時間`, `活動連結`
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                venue_id,
                artist_id,
                clean(row.get("活動名稱")),
                clean(row.get("票價")),
                clean(row.get("票種")),
                clean(row.get("活動時間")),
                clean(row.get("搶票時間")),
                clean(row.get("網址"), ""),
            ),
        )
        inserted_events += cur.rowcount

        cur.execute(
            """
            SELECT `event_id_pk`
            FROM `活動`
            WHERE `活動名稱`=%s AND `活動時間`=%s AND `venue_id_fk`=%s AND `artist_id_fk`=%s AND `活動連結`=%s
            LIMIT 1
            """,
            (
                clean(row.get("活動名稱")),
                clean(row.get("活動時間")),
                venue_id,
                artist_id,
                clean(row.get("網址"), ""),
            ),
        )
        event_id = cur.fetchone()[0]

        # 藝人表的 event_id_fk：保留第一筆關聯
        cur.execute(
            """
            UPDATE `藝人`
            SET `event_id_fk`=%s
            WHERE `artist_id_pk`=%s AND `event_id_fk` IS NULL
            """,
            (event_id, artist_id),
        )

        platform_name = clean(row.get("來源網站"))
        cur.execute(
            """
            INSERT IGNORE INTO `售票平台` (`event_id_fk`, `artist_id_fk`, `平台名稱`)
            VALUES (%s, %s, %s)
            """,
            (event_id, artist_id, platform_name),
        )
        inserted_platform_rows += cur.rowcount

    return inserted_events, inserted_platform_rows


def verify(cur):
    print("\n=== 表格筆數 ===")
    for t in ["使用者", "活動地點", "藝人", "活動", "售票平台"]:
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        print(f"{t}: {cur.fetchone()[0]}")

    print("\n=== 外鍵孤兒檢查（應為 0）===")
    checks = {
        "活動.venue_id_fk": """
            SELECT COUNT(*)
            FROM `活動` a
            LEFT JOIN `活動地點` v ON a.`venue_id_fk`=v.`venue_id_pk`
            WHERE a.`venue_id_fk` IS NOT NULL AND v.`venue_id_pk` IS NULL
        """,
        "活動.artist_id_fk": """
            SELECT COUNT(*)
            FROM `活動` a
            LEFT JOIN `藝人` r ON a.`artist_id_fk`=r.`artist_id_pk`
            WHERE a.`artist_id_fk` IS NOT NULL AND r.`artist_id_pk` IS NULL
        """,
        "藝人.event_id_fk": """
            SELECT COUNT(*)
            FROM `藝人` r
            LEFT JOIN `活動` a ON r.`event_id_fk`=a.`event_id_pk`
            WHERE r.`event_id_fk` IS NOT NULL AND a.`event_id_pk` IS NULL
        """,
        "售票平台.event_id_fk": """
            SELECT COUNT(*)
            FROM `售票平台` p
            LEFT JOIN `活動` a ON p.`event_id_fk`=a.`event_id_pk`
            WHERE p.`event_id_fk` IS NOT NULL AND a.`event_id_pk` IS NULL
        """,
        "售票平台.artist_id_fk": """
            SELECT COUNT(*)
            FROM `售票平台` p
            LEFT JOIN `藝人` r ON p.`artist_id_fk`=r.`artist_id_pk`
            WHERE p.`artist_id_fk` IS NOT NULL AND r.`artist_id_pk` IS NULL
        """,
    }
    for name, sql in checks.items():
        cur.execute(sql)
        print(f"{name}: {cur.fetchone()[0]}")


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    create_schema(cur)
    users_count = import_users(cur)
    events_count, platform_count = import_events(cur)
    create_views(cur)

    conn.commit()

    print("✅ 已依照圖建立資料庫主鍵外鍵")
    print(f"匯入 使用者: {users_count}")
    print(f"匯入 活動: {events_count}")
    print(f"匯入 售票平台關聯: {platform_count}")
    print("已建立 聯合檢視: 活動聯合檢視")

    verify(cur)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
