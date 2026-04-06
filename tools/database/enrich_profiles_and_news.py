# -*- coding: utf-8 -*-
"""
補全資料庫三個欄位：
1) artists.artist_intro（藝人介紹）
2) artist_news（藝人最近新聞）
3) venues.venue_intro（場地簡介）

資料來源：
- Wikipedia API（簡介）
- Google News RSS（近期新聞）
"""

from __future__ import annotations

import html
import hashlib
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import mysql.connector
import requests

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

HTTP_TIMEOUT = 12
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def summarize_text(value: str, max_len: int = 280) -> str:
    value = clean_text(value)
    if len(value) <= max_len:
        return value
    return value[: max_len - 1].rstrip() + "…"


def normalize_news_url(url: str, max_len: int = 500) -> str:
    text = clean_text(url)
    if len(text) <= max_len:
        return text

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    keep = max_len - len("#") - len(digest)
    if keep < 20:
        keep = 20
    return f"{text[:keep]}#{digest}"


def wiki_search_titles(query: str, lang: str = "zh", limit: int = 3) -> list[str]:
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "utf8": 1,
        "format": "json",
        "srlimit": limit,
    }
    try:
        resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT, headers=HTTP_HEADERS)
        resp.raise_for_status()
        data = resp.json()
        return [x.get("title", "") for x in data.get("query", {}).get("search", []) if x.get("title")]
    except Exception:
        return []


def wiki_summary_from_title(title: str, lang: str = "zh") -> tuple[str, str]:
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
    try:
        resp = requests.get(url, timeout=HTTP_TIMEOUT, headers=HTTP_HEADERS)
        if resp.status_code != 200:
            return "", ""
        data = resp.json()
        extract = clean_text(data.get("extract", ""))
        page_url = (
            data.get("content_urls", {})
            .get("desktop", {})
            .get("page", f"https://{lang}.wikipedia.org/wiki/{quote(title)}")
        )
        # 避免消歧義頁
        if not extract or "消歧義" in extract or "可能是指" in extract:
            return "", ""
        return summarize_text(extract, 320), page_url
    except Exception:
        return "", ""


def fetch_intro(entity_name: str, kind: str) -> tuple[str, str]:
    """kind: artist | venue"""
    name = clean_text(entity_name)
    if not name:
        return "", ""

    queries = [name]
    if kind == "artist":
        queries += [f"{name} 歌手", f"{name} 音樂人"]
    else:
        queries += [f"{name} 場館", f"{name} 演唱會", f"{name} 台灣"]

    for q in queries:
        for lang in ("zh", "en"):
            titles = wiki_search_titles(q, lang=lang, limit=3)
            for title in titles:
                intro, source_url = wiki_summary_from_title(title, lang=lang)
                if intro:
                    return intro, source_url
    return "", ""


def parse_google_news_rss(artist_name: str, max_items: int = 3) -> list[dict]:
    query = f'"{artist_name}" (演唱會 OR 音樂 OR 唱片 OR 表演)'
    url = "https://news.google.com/rss/search"
    params = {
        "q": query,
        "hl": "zh-TW",
        "gl": "TW",
        "ceid": "TW:zh-Hant",
    }

    try:
        resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT, headers=HTTP_HEADERS)
        resp.raise_for_status()
    except Exception:
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return []

    out = []
    for item in root.findall("./channel/item"):
        title = clean_text(item.findtext("title", default=""))
        link = normalize_news_url(item.findtext("link", default=""), max_len=500)
        desc = summarize_text(item.findtext("description", default=""), 350)
        pub_raw = item.findtext("pubDate", default="")

        published_at = None
        if pub_raw:
            try:
                published_at = parsedate_to_datetime(pub_raw).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                published_at = None

        source_name = "Google News"
        if " - " in title:
            title_parts = title.rsplit(" - ", 1)
            if len(title_parts) == 2 and len(title_parts[1]) <= 80:
                title, source_name = title_parts[0], title_parts[1]

        if not title or not link:
            continue

        out.append(
            {
                "title": title,
                "summary": desc,
                "source_name": source_name,
                "source_url": link,
                "published_at": published_at,
            }
        )

        if len(out) >= max_items:
            break

    return out


def enrich_artist_intro(cur) -> tuple[int, int]:
    cur.execute(
        """
        SELECT artist_id, artist_name
        FROM artists
        WHERE artist_intro = '待補充' OR artist_intro IS NULL OR artist_intro = ''
        ORDER BY artist_id
        """
    )
    rows = cur.fetchall()

    updated = 0
    attempted = 0

    for artist_id, artist_name in rows:
        attempted += 1
        intro, source_url = fetch_intro(artist_name, kind="artist")
        if intro:
            cur.execute(
                """
                UPDATE artists
                SET artist_intro = %s,
                    intro_source_url = %s,
                    intro_updated_at = NOW()
                WHERE artist_id = %s
                """,
                (intro, source_url, artist_id),
            )
            updated += 1
        time.sleep(0.15)

    return attempted, updated


def enrich_venue_intro(cur) -> tuple[int, int]:
    cur.execute(
        """
        SELECT venue_id, venue_name
        FROM venues
        WHERE venue_intro = '待補充' OR venue_intro IS NULL OR venue_intro = ''
        ORDER BY venue_id
        """
    )
    rows = cur.fetchall()

    updated = 0
    attempted = 0

    for venue_id, venue_name in rows:
        if not clean_text(venue_name) or venue_name == "未提供":
            continue

        attempted += 1
        intro, source_url = fetch_intro(venue_name, kind="venue")
        if intro:
            cur.execute(
                """
                UPDATE venues
                SET venue_intro = %s,
                    intro_source_url = %s,
                    intro_updated_at = NOW()
                WHERE venue_id = %s
                """,
                (intro, source_url, venue_id),
            )
            updated += 1
        time.sleep(0.15)

    return attempted, updated


def enrich_artist_news(cur) -> tuple[int, int]:
    cur.execute(
        """
        SELECT DISTINCT a.artist_id, a.artist_name
        FROM artists a
        JOIN event_artists ea ON ea.artist_id = a.artist_id
        ORDER BY a.artist_id
        """
    )
    artists = cur.fetchall()

    artist_attempted = 0
    news_inserted = 0

    for artist_id, artist_name in artists:
        if not clean_text(artist_name):
            continue
        artist_attempted += 1
        items = parse_google_news_rss(artist_name, max_items=3)
        for item in items:
            cur.execute(
                """
                INSERT INTO artist_news (
                    artist_id, title, summary, source_name, source_url, published_at, sentiment
                ) VALUES (%s, %s, %s, %s, %s, %s, 'neutral')
                ON DUPLICATE KEY UPDATE
                    title = VALUES(title),
                    summary = VALUES(summary),
                    source_name = VALUES(source_name),
                    published_at = VALUES(published_at),
                    fetched_at = CURRENT_TIMESTAMP
                """,
                (
                    artist_id,
                    item["title"],
                    item["summary"],
                    item["source_name"],
                    item["source_url"],
                    item["published_at"],
                ),
            )
            if cur.rowcount > 0:
                news_inserted += 1
        time.sleep(0.2)

    return artist_attempted, news_inserted


def fill_remaining_artist_intro(cur) -> int:
    cur.execute(
        """
        SELECT a.artist_id, a.artist_name
        FROM artists a
        WHERE a.artist_intro = '待補充' OR a.artist_intro IS NULL OR a.artist_intro = ''
        """
    )
    rows = cur.fetchall()
    filled = 0

    for artist_id, artist_name in rows:
        cur.execute(
            """
            SELECT title, source_url
            FROM artist_news
            WHERE artist_id = %s
            ORDER BY COALESCE(published_at, fetched_at) DESC
            LIMIT 1
            """,
            (artist_id,),
        )
        news_row = cur.fetchone()

        if news_row:
            title, source_url = news_row
            intro = (
                f"{artist_name} 為本資料庫收錄之演出藝人。"
                f"近期相關報導包含：{clean_text(title)}。"
            )
            src = clean_text(source_url)
        else:
            intro = f"{artist_name} 為本資料庫收錄之演出藝人，後續將持續補充完整介紹。"
            src = None

        cur.execute(
            """
            UPDATE artists
            SET artist_intro = %s,
                intro_source_url = COALESCE(%s, intro_source_url),
                intro_updated_at = NOW()
            WHERE artist_id = %s
            """,
            (summarize_text(intro, 320), src, artist_id),
        )
        filled += 1

    return filled


def fill_remaining_venue_intro(cur) -> int:
    cur.execute(
        """
        SELECT v.venue_id, v.venue_name, v.venue_address
        FROM venues v
        WHERE v.venue_intro = '待補充' OR v.venue_intro IS NULL OR v.venue_intro = ''
        """
    )
    rows = cur.fetchall()
    filled = 0

    for venue_id, venue_name, venue_address in rows:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM events
            WHERE venue_id = %s
            """,
            (venue_id,),
        )
        event_count = cur.fetchone()[0]

        address_text = clean_text(venue_address)
        if not address_text or address_text == "未提供":
            intro = f"{venue_name} 為本資料庫收錄之演出場地，近期收錄活動 {event_count} 場。"
        else:
            intro = (
                f"{venue_name} 為本資料庫收錄之演出場地，地址為 {address_text}，"
                f"近期收錄活動 {event_count} 場。"
            )

        cur.execute(
            """
            UPDATE venues
            SET venue_intro = %s,
                intro_updated_at = NOW()
            WHERE venue_id = %s
            """,
            (summarize_text(intro, 320), venue_id),
        )
        filled += 1

    return filled


def print_post_stats(cur):
    cur.execute("SELECT COUNT(*) FROM artists WHERE artist_intro IS NOT NULL AND artist_intro <> '' AND artist_intro <> '待補充'")
    artist_intro_done = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM artists")
    total_artists = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM venues WHERE venue_intro IS NOT NULL AND venue_intro <> '' AND venue_intro <> '待補充'")
    venue_intro_done = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM venues")
    total_venues = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM artist_news")
    total_news = cur.fetchone()[0]

    print("\n=== 補全結果 ===")
    print(f"藝人介紹：{artist_intro_done}/{total_artists}")
    print(f"場地簡介：{venue_intro_done}/{total_venues}")
    print(f"藝人新聞：{total_news} 筆")

    print("\n藝人介紹樣本：")
    cur.execute("SELECT artist_name, artist_intro FROM artists WHERE artist_intro <> '待補充' LIMIT 3")
    for name, intro in cur.fetchall():
        print(f"- {name}: {intro[:60]}")

    print("\n場地簡介樣本：")
    cur.execute("SELECT venue_name, venue_intro FROM venues WHERE venue_intro <> '待補充' LIMIT 3")
    for name, intro in cur.fetchall():
        print(f"- {name}: {intro[:60]}")

    print("\n新聞樣本：")
    cur.execute(
        """
        SELECT a.artist_name, n.title, n.source_name
        FROM artist_news n
        JOIN artists a ON a.artist_id = n.artist_id
        ORDER BY n.fetched_at DESC
        LIMIT 5
        """
    )
    for artist_name, title, source_name in cur.fetchall():
        print(f"- [{artist_name}] {title} ({source_name})")


def main():
    started_at = datetime.now()
    print(f"開始補全三個欄位：{started_at:%Y-%m-%d %H:%M:%S}")

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        a_attempted, a_updated = enrich_artist_intro(cur)
        conn.commit()
        print(f"藝人介紹完成：嘗試 {a_attempted}，更新 {a_updated}")

        v_attempted, v_updated = enrich_venue_intro(cur)
        conn.commit()
        print(f"場地簡介完成：嘗試 {v_attempted}，更新 {v_updated}")

        n_artist_attempted, n_upserts = enrich_artist_news(cur)
        conn.commit()
        print(f"藝人新聞完成：嘗試 {n_artist_attempted} 位藝人，新增/更新 {n_upserts} 筆")

        remaining_artist_filled = fill_remaining_artist_intro(cur)
        remaining_venue_filled = fill_remaining_venue_intro(cur)
        conn.commit()
        print(
            "補齊剩餘簡介完成："
            f"藝人 {remaining_artist_filled} 筆、場地 {remaining_venue_filled} 筆"
        )

        print_post_stats(cur)

        ended_at = datetime.now()
        print(f"\n全部完成：{ended_at:%Y-%m-%d %H:%M:%S}，耗時 {(ended_at - started_at).total_seconds():.1f} 秒")

    except Exception as exc:
        conn.rollback()
        print(f"補全失敗：{exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
