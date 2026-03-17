-- ============================================
-- ER 圖結構查詢 - 表格與欄位
-- ============================================

USE concerts;

-- 查詢1：所有表格及其欄位
SELECT 
    TABLE_NAME AS '表格名稱',
    COLUMN_NAME AS '欄位名稱',
    COLUMN_TYPE AS '資料型態',
    IS_NULLABLE AS '可空值',
    COLUMN_KEY AS '鍵類型',
    EXTRA AS '額外屬性'
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'concerts'
  AND TABLE_NAME IN ('使用者','活動','活動地點','藝人','售票平台')
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- ============================================
-- 查詢2：外鍵關係圖
-- ============================================

SELECT 
    CONSTRAINT_NAME AS '約束名',
    TABLE_NAME AS '來源表',
    COLUMN_NAME AS '來源欄位',
    REFERENCED_TABLE_NAME AS '目標表',
    REFERENCED_COLUMN_NAME AS '目標欄位',
    REFERENTIAL_ACTION AS '更新規則'
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'concerts'
  AND TABLE_NAME IN ('使用者','活動','活動地點','藝人','售票平台')
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, COLUMN_NAME;

-- ============================================
-- 查詢3：所有主鍵
-- ============================================

SELECT 
    TABLE_NAME AS '表格',
    GROUP_CONCAT(COLUMN_NAME) AS '主鍵欄位'
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'concerts'
  AND TABLE_NAME IN ('使用者','活動','活動地點','藝人','售票平台')
  AND COLUMN_KEY = 'PRI'
GROUP BY TABLE_NAME;

-- ============================================
-- 查詢4：ER 圖摘要 (表格關係)
-- ============================================

SELECT 
    '使用者' AS '表格',
    COUNT(*) AS '記錄數'
FROM 使用者

UNION ALL

SELECT '活動', COUNT(*) FROM 活動

UNION ALL

SELECT '活動地點', COUNT(*) FROM 活動地點

UNION ALL

SELECT '藝人', COUNT(*) FROM 藝人

UNION ALL

SELECT '售票平台', COUNT(*) FROM 售票平台;

-- ============================================
-- 查詢5：外鍵完整性檢查
-- ============================================

-- 檢查 活動.venue_id_fk 的完整性
SELECT '活動.venue_id_fk' AS '檢查項目',
       COUNT(*) AS '孤立記錄'
FROM 活動
LEFT JOIN 活動地點 ON 活動.venue_id_fk = 活動地點.venue_id_pk
WHERE 活動.venue_id_fk IS NOT NULL 
  AND 活動地點.venue_id_pk IS NULL

UNION ALL

-- 檢查 活動.artist_id_fk 的完整性
SELECT '活動.artist_id_fk',
       COUNT(*)
FROM 活動
LEFT JOIN 藝人 ON 活動.artist_id_fk = 藝人.artist_id_pk
WHERE 活動.artist_id_fk IS NOT NULL 
  AND 藝人.artist_id_pk IS NULL

UNION ALL

-- 檢查 藝人.event_id_fk 的完整性
SELECT '藝人.event_id_fk',
       COUNT(*)
FROM 藝人
LEFT JOIN 活動 ON 藝人.event_id_fk = 活動.event_id_pk
WHERE 藝人.event_id_fk IS NOT NULL 
  AND 活動.event_id_pk IS NULL

UNION ALL

-- 檢查 售票平台.event_id_fk 的完整性
SELECT '售票平台.event_id_fk',
       COUNT(*)
FROM 售票平台
LEFT JOIN 活動 ON 售票平台.event_id_fk = 活動.event_id_pk
WHERE 售票平台.event_id_fk IS NOT NULL 
  AND 活動.event_id_pk IS NULL

UNION ALL

-- 檢查 售票平台.artist_id_fk 的完整性
SELECT '售票平台.artist_id_fk',
       COUNT(*)
FROM 售票平台
LEFT JOIN 藝人 ON 售票平台.artist_id_fk = 藝人.artist_id_pk
WHERE 售票平台.artist_id_fk IS NOT NULL 
  AND 藝人.artist_id_pk IS NULL;

-- ============================================
-- 查詢6：聯合檢視結構
-- ============================================

DESCRIBE 活動聯合檢視;