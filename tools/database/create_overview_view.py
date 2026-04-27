# -*- coding: utf-8 -*-
"""
建立總表檢視：concert_overview
整合 events / venues / artists / segments / pricing / schedules，供查詢查看。
"""

from __future__ import annotations

import os

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


CREATE_VIEW_SQL = """
CREATE VIEW concert_overview AS
SELECT
  e.event_id AS event_id,
  e.`活動名稱` AS event_name,
  e.`來源網站` AS source_site,
  e.`網址` AS event_url,
  e.`活動時間` AS raw_event_time,
  e.`搶票時間` AS raw_sale_time,
  e.`票價` AS raw_price,
  e.`活動地點` AS raw_venue_name,
  e.`活動地址` AS raw_venue_address,

  v.venue_id AS venue_id,
  v.venue_name AS venue_name,
  v.venue_address AS venue_address,
  v.venue_intro AS venue_intro,

  es.event_type AS event_type,
  es.price_band AS price_band,
  es.sale_status AS sale_status,
  es.confidence_score AS event_segment_confidence,

  sch.first_performance_date AS first_performance_date,
  sch.last_performance_date AS last_performance_date,
  sch.schedule_count AS schedule_count,

  pr.min_price AS min_price,
  pr.max_price AS max_price,
  pr.price_tier_count AS price_tier_count,

  aa.artist_count AS artist_count,
  aa.artist_names AS artist_names,
  aa.artist_regions AS artist_regions,
  aa.artist_languages AS artist_languages,
  aa.artist_forms AS artist_forms,

  e.created_at AS event_created_at
FROM events e
LEFT JOIN venues v
  ON e.venue_id = v.venue_id
LEFT JOIN event_segments es
  ON e.event_id = es.event_id
LEFT JOIN (
  SELECT
    event_id,
    MIN(performance_date) AS first_performance_date,
    MAX(performance_date) AS last_performance_date,
    COUNT(*) AS schedule_count
  FROM event_schedules
  GROUP BY event_id
) sch
  ON e.event_id = sch.event_id
LEFT JOIN (
  SELECT
    event_id,
    MIN(price_amount) AS min_price,
    MAX(price_amount) AS max_price,
    COUNT(*) AS price_tier_count
  FROM ticket_pricing
  GROUP BY event_id
) pr
  ON e.event_id = pr.event_id
LEFT JOIN (
  SELECT
    ea.event_id,
    COUNT(DISTINCT a.artist_id) AS artist_count,
    GROUP_CONCAT(DISTINCT a.artist_name ORDER BY a.artist_name SEPARATOR ' | ') AS artist_names,
    GROUP_CONCAT(DISTINCT COALESCE(ags.region_group, '未分類') ORDER BY ags.region_group SEPARATOR ' | ') AS artist_regions,
    GROUP_CONCAT(DISTINCT COALESCE(ags.market_language, '未分類') ORDER BY ags.market_language SEPARATOR ' | ') AS artist_languages,
    GROUP_CONCAT(DISTINCT COALESCE(ags.artist_form, '未分類') ORDER BY ags.artist_form SEPARATOR ' | ') AS artist_forms
  FROM event_artists ea
  JOIN artists a
    ON ea.artist_id = a.artist_id
  LEFT JOIN artist_segments ags
    ON a.artist_id = ags.artist_id
  GROUP BY ea.event_id
) aa
  ON e.event_id = aa.event_id
"""


def main() -> None:
  conn = mysql.connector.connect(**DB_CONFIG)
  cur = conn.cursor()
  try:
    cur.execute("DROP VIEW IF EXISTS concert_overview")
    cur.execute(CREATE_VIEW_SQL)

    cur.execute("SELECT COUNT(*) FROM concert_overview")
    total = cur.fetchone()[0]

    cur.execute(
      """
      SELECT event_id, event_name, source_site, event_type, price_band, artist_count
      FROM concert_overview
      ORDER BY event_id
      LIMIT 5
      """
    )
    sample = cur.fetchall()

    conn.commit()

    print("create view success")
    print(f"rows={total}")
    print("sample:")
    for row in sample:
      print(row)
  finally:
    cur.close()
    conn.close()


if __name__ == "__main__":
  main()
