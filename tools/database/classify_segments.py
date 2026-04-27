# -*- coding: utf-8 -*-
"""
將現有資料做可查詢的細項分類：
1) 藝人分類：國家/地區、型態、語系市場
2) 活動分類：活動類型、票價級距、售票狀態

可透過 DB_* 環境變數切換本地/遠端。
"""

from __future__ import annotations

import os
import re
from decimal import Decimal

import mysql.connector

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


def create_tables(cur):
    cur.execute("DROP TABLE IF EXISTS artist_segments")
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

    cur.execute("DROP TABLE IF EXISTS event_segments")
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


def classify_artist_region(name: str, intro: str) -> tuple[str, Decimal, str]:
    text = f"{name or ''} {intro or ''}".lower()

    tw_kw = ["台灣", "臺灣", "taiwan", "台北", "高雄", "台中"]
    jp_kw = ["日本", "japan", "tokyo", "osaka", "中島", "米津", "濱崎", "nakashima", "yonezu"]
    kr_kw = ["韓國", "korea", "seoul", "k-pop", "bts", "blackpink"]
    cn_kw = ["中國", "大陸", "北京", "上海", "廣州", "深圳", "香港", "澳門", "china", "hong kong", "macau"]
    west_kw = ["美國", "英國", "法國", "德國", "加拿大", "australia", "usa", "uk", "europe", "american", "british"]
    sea_kw = ["新加坡", "馬來西亞", "泰國", "印尼", "菲律賓", "singapore", "malaysia", "thailand", "indonesia", "philippines"]

    def has_any(kws: list[str]) -> bool:
        return any(k in text for k in kws)

    if has_any(tw_kw):
        return "台灣", Decimal("0.92"), "region:tw_keyword"
    if has_any(jp_kw):
        return "日本", Decimal("0.90"), "region:jp_keyword"
    if has_any(kr_kw):
        return "韓國", Decimal("0.90"), "region:kr_keyword"
    if has_any(cn_kw):
        return "中港澳", Decimal("0.86"), "region:cn_hk_mo_keyword"
    if has_any(west_kw):
        return "歐美", Decimal("0.85"), "region:west_keyword"
    if has_any(sea_kw):
        return "東南亞", Decimal("0.84"), "region:sea_keyword"

    # 羅馬字母比例高，且無中文地區線索，先歸為國際/未知
    latin_chars = sum(ch.isascii() and ch.isalpha() for ch in (name or ""))
    if latin_chars >= max(4, len(name or "") // 2):
        return "國際/未知", Decimal("0.60"), "region:latin_name_fallback"

    return "國際/未知", Decimal("0.45"), "region:default"


def classify_artist_form(name: str, intro: str) -> tuple[str, str]:
    text = f"{name or ''} {intro or ''}".lower()

    if any(k in text for k in ["樂團", "band", "團", "boyz", "girls", "orchestra"]):
        return "團體", "form:group_keyword"
    if any(k in text for k in ["交響", "弦樂", "合唱", "管弦"]):
        return "古典/合奏", "form:orchestra_keyword"
    if any(k in text for k in ["dj", "mc", "饒舌", "rapper"]):
        return "dj/饒舌", "form:dj_rap_keyword"
    return "個人", "form:solo_default"


def classify_market_language(name: str, intro: str) -> tuple[str, str]:
    text = f"{name or ''} {intro or ''}".lower()

    zh = any(k in text for k in ["華語", "中文", "國語", "台語", "臺語", "mandarin"])
    jp = any(k in text for k in ["日語", "日本", "j-pop", "japan"])
    kr = any(k in text for k in ["韓語", "k-pop", "korea"])
    en = any(k in text for k in ["english", "英語", "歐美", "american", "british"])

    count = sum([zh, jp, kr, en])
    if count >= 2:
        return "多語", "lang:multi_signal"
    if zh:
        return "華語", "lang:zh_signal"
    if jp:
        return "日語", "lang:jp_signal"
    if kr:
        return "韓語", "lang:kr_signal"
    if en:
        return "英語", "lang:en_signal"
    return "未明", "lang:default"


def parse_price_values(price_text: str) -> list[int]:
    if not price_text:
        return []
    vals = [int(x) for x in re.findall(r"\d{2,6}", price_text)]
    # 避免把年份等誤當票價，過濾不合理值
    vals = [v for v in vals if 50 <= v <= 200000]
    return vals


def classify_event_type(event_name: str) -> tuple[str, str, Decimal]:
    name = (event_name or "").lower()

    if any(k in name for k in ["音樂祭", "festival", "fest"]):
        return "音樂祭", "type:festival_keyword", Decimal("0.94")
    if any(k in name for k in ["音樂劇", "musical", "歌舞"]):
        return "音樂劇", "type:musical_keyword", Decimal("0.93")
    if any(k in name for k in ["演唱會", "concert", "tour", "live"]):
        return "演唱會", "type:concert_keyword", Decimal("0.90")
    if any(k in name for k in ["親子", "兒童", "kids"]):
        return "親子", "type:kids_keyword", Decimal("0.88")
    if any(k in name for k in ["動漫", "動畫", "acg", "game", "final fantasy"]):
        return "動漫/遊戲", "type:acg_keyword", Decimal("0.87")
    return "其他", "type:default", Decimal("0.55")


def classify_price_band(price_values: list[int]) -> tuple[str, str]:
    if not price_values:
        return "未提供", "price:no_value"

    mx = max(price_values)
    if mx < 1000:
        return "平價(<1000)", "price:max_lt_1000"
    if mx < 2500:
        return "中價(1000-2499)", "price:max_1000_2499"
    if mx < 4500:
        return "高價(2500-4499)", "price:max_2500_4499"
    return "旗艦(>=4500)", "price:max_gte_4500"


def classify_sale_status(sale_text: str) -> tuple[str, str]:
    t = (sale_text or "").lower()
    if not t or t == "未提供":
        return "未提供", "sale:missing"
    if any(k in t for k in ["已售完", "sold out", "完售"]):
        return "已售完", "sale:soldout"
    if any(k in t for k in ["即將", "coming", "開賣", "預售", "預購"]):
        return "待開賣", "sale:coming"
    if re.search(r"\d{4}/\d{1,2}/\d{1,2}", t) or re.search(r"\d{1,2}/\d{1,2}", t):
        return "已排程", "sale:has_date"
    return "販售中/未明", "sale:default"


def fill_artist_segments(cur):
    cur.execute("SELECT artist_id, artist_name, artist_intro FROM artists")
    rows = cur.fetchall()

    for artist_id, artist_name, artist_intro in rows:
        region, conf_region, trace_region = classify_artist_region(artist_name, artist_intro)
        form, trace_form = classify_artist_form(artist_name, artist_intro)
        lang, trace_lang = classify_market_language(artist_name, artist_intro)

        # 取三段中的最低信心當整體
        overall_conf = conf_region
        trace = f"{trace_region};{trace_form};{trace_lang}"

        cur.execute(
            """
            INSERT INTO artist_segments (
              artist_id, artist_name, region_group, artist_form, market_language,
              confidence_score, rule_trace
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (artist_id, artist_name, region, form, lang, overall_conf, trace),
        )


def fill_event_segments(cur):
    cur.execute("SELECT event_id, `活動名稱`, `票價`, `搶票時間` FROM events")
    rows = cur.fetchall()

    for event_id, event_name, price_text, sale_text in rows:
        event_type, trace_type, conf = classify_event_type(event_name)
        price_band, trace_price = classify_price_band(parse_price_values(price_text or ""))
        sale_status, trace_sale = classify_sale_status(sale_text)

        trace = f"{trace_type};{trace_price};{trace_sale}"

        cur.execute(
            """
            INSERT INTO event_segments (
              event_id, event_name, event_type, price_band, sale_status,
              confidence_score, rule_trace
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (event_id, event_name, event_type, price_band, sale_status, conf, trace),
        )


def print_summary(cur):
    print("artist_segments by region:")
    cur.execute("SELECT region_group, COUNT(*) FROM artist_segments GROUP BY region_group ORDER BY COUNT(*) DESC")
    for region, cnt in cur.fetchall():
        print(f"  - {region}: {cnt}")

    print("event_segments by type:")
    cur.execute("SELECT event_type, COUNT(*) FROM event_segments GROUP BY event_type ORDER BY COUNT(*) DESC")
    for et, cnt in cur.fetchall():
        print(f"  - {et}: {cnt}")

    print("event_segments by price_band:")
    cur.execute("SELECT price_band, COUNT(*) FROM event_segments GROUP BY price_band ORDER BY COUNT(*) DESC")
    for pb, cnt in cur.fetchall():
        print(f"  - {pb}: {cnt}")


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        print("start classify segments...")
        create_tables(cur)
        fill_artist_segments(cur)
        fill_event_segments(cur)
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM artist_segments")
        a_cnt = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM event_segments")
        e_cnt = cur.fetchone()[0]

        print(f"artist_segments={a_cnt}")
        print(f"event_segments={e_cnt}")
        print_summary(cur)
    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"classify failed: {exc}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
