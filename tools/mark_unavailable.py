import os
import json
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_PATH = os.path.join(ROOT, 'data', 'concerts.json')

def backup(path):
    ts = time.strftime('%Y%m%d_%H%M%S')
    dst = path.replace('.json', f'_backup_markunavail_{ts}.json')
    with open(path, 'r', encoding='utf-8') as f:
        data = f.read()
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(data)
    return dst

def is_missing(item):
    # consider missing if any of the main fields are empty or '未公布'
    for k in ('演出地點', '票價', '演出時間'):
        v = item.get(k)
        if not v or (isinstance(v, str) and v.strip() in ('', '未公布')):
            return True
    return False

def mark_unavailable():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    backup_path = backup(DATA_PATH)
    changed = 0
    total = 0
    now = time.strftime('%Y-%m-%d %H:%M:%S')

    for item in data:
        if item.get('來源網站') == 'TicketCom' and is_missing(item):
            total += 1
            item['資料狀態'] = '資料不可得'
            item['資料不可得原因'] = '站內無 detail 或下架 / 僅為 category/dm 列表，無票價/地點資訊'
            item['資料處理時間'] = now
            changed += 1

    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'備份檔案: {backup_path}')
    print(f'處理完成，TicketCom 欄位缺失項目: {total}，已標記: {changed}')

if __name__ == '__main__':
    mark_unavailable()
