# -*- coding: utf-8 -*-
"""
修正 MySQL events 資料品質問題：
1. 年代售票：搶票時間 被誤寫為活動名稱 → 改為 '未提供'
2. 年代售票：活動地址 被誤寫為公司辦公室地址 → 改為 '未提供'
3. 遠大售票：藝人 = 活動名稱（因原始資料無獨立藝人欄）→ 保留，無法改善
"""
import mysql.connector

FAKE_ADDRESSES = [
    "中清路一段447號",
    "台中市北區中清路",
]

conn = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="barry0803",
    database="concerts",
    charset="utf8mb4",
    collation="utf8mb4_unicode_ci",
    autocommit=False,
)
cur = conn.cursor()

# ── 1. 搶票時間 被誤設為活動名稱 (年代售票) ──────────────────────────────
cur.execute("""
    UPDATE events
    SET `搶票時間` = '未提供'
    WHERE `來源網站` = '年代售票'
      AND TRIM(`搶票時間`) = TRIM(`活動名稱`)
""")
fixed_sale_time = cur.rowcount
print(f"[FIX1] 搶票時間誤寫活動名稱 → 已修正 {fixed_sale_time} 筆")

# ── 2. 活動地址 = 公司固定地址 (年代售票 footer) ──────────────────────────
for fake in FAKE_ADDRESSES:
    cur.execute("""
        UPDATE events
        SET `活動地址` = '未提供'
        WHERE `活動地址` LIKE %s
    """, (f"%{fake}%",))
    print(f"[FIX2] 活動地址含 '{fake}' → 已修正 {cur.rowcount} 筆")

# ── 3. 藝人 = 活動名稱 統計（年代售票無法改善，但遠大應該也一樣）──────
cur.execute("""
    SELECT `來源網站`, COUNT(*) as cnt
    FROM events
    WHERE TRIM(`藝人`) = TRIM(`活動名稱`)
    GROUP BY `來源網站`
""")
print("\n[INFO] 藝人 = 活動名稱 統計（這類資料原始來源即無獨立藝人欄）:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} 筆")

conn.commit()

# ── 驗證 ────────────────────────────────────────────────────────────────
print("\n=== 年代售票 修正後樣本 ===")
cur.execute("""
    SELECT `活動名稱`, `藝人`, `搶票時間`, `活動地址`
    FROM events
    WHERE `來源網站` = '年代售票'
    LIMIT 5
""")
for r in cur.fetchall():
    print(f"  活動名稱: {r[0][:40]}")
    print(f"  藝人:     {r[1][:40]}")
    print(f"  搶票時間: {r[2][:40]}")
    print(f"  活動地址: {r[3][:40]}")
    print()

cur.close()
conn.close()
print("✅ 資料品質修正完成")
