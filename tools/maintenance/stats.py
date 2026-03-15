import sqlite3

conn = sqlite3.connect('data/concerts.db')
cursor = conn.cursor()

# 統計總數
cursor.execute('SELECT COUNT(*) FROM events')
total = cursor.fetchone()[0]

# 按來源統計
cursor.execute('SELECT source, COUNT(*) as count FROM events GROUP BY source ORDER BY count DESC')
sources = cursor.fetchall()

print('='*70)
print('           完整演唱會資料庫統計')
print('='*70)
print(f'\n總記錄數: {total} 場活動\n')
print('各網站統計:')
for i, (source, count) in enumerate(sources, 1):
    source_name = source or '未知來源'
    bar = '█' * (count // 20)
    print(f'  {i}. {source_name:20} {count:3d} 場 {bar}')

# 顯示導入的檔案
cursor.execute('SELECT DISTINCT source_file FROM events ORDER BY source_file')
files = cursor.fetchall()
print(f'\n已導入檔案數: {len(files)}')

conn.close()
print('='*70)
print('所有數據已保存至: data/concerts.db')
print('='*70)
