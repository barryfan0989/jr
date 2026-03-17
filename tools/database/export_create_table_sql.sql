-- ============================================
-- 從 MySQL 資料庫查詢並導出建立表格的 SQL 語句
-- ============================================

USE concerts;

-- 查詢1：導出所有表格的建立語句
SHOW CREATE TABLE 使用者;
SHOW CREATE TABLE 活動地點;
SHOW CREATE TABLE 藝人;
SHOW CREATE TABLE 活動;
SHOW CREATE TABLE 售票平台;

-- 查詢2：導出所有檢視的建立語句
SHOW CREATE VIEW 活動聯合檢視;