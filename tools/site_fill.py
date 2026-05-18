import json
import time
import sys
import os

# ensure project root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from crawlers.tier1_crawlers import TicketComCrawler
from concert_crawler import IndievoxCrawler

DATA_PATH = "data/concerts.json"
BACKUP_PATH = "data/concerts_backup_sitefill.json"

def is_missing(v):
    if v is None:
        return True
    s = str(v).strip()
    return s == "" or s in ("未公布", "TBD", "待公告")

def main():
    with open(DATA_PATH, encoding='utf-8') as f:
        data = json.load(f)

    ticket_crawler = TicketComCrawler()
    indie_crawler = IndievoxCrawler()

    updated = 0
    inspected = 0

    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    for item in data:
        src = item.get('來源網站', '')
        if src not in ('TicketCom', 'Indievox'):
            continue

        url = item.get('網址')
        if not url:
            continue

        # only process if missing some fields
        if not (is_missing(item.get('演出地點')) or is_missing(item.get('票價')) or is_missing(item.get('演出時間'))):
            continue

        inspected += 1
        info = {}
        try:
            if src == 'TicketCom':
                info = ticket_crawler._scrape_event_detail(url) or {}
            elif src == 'Indievox':
                info = indie_crawler._extract_detail(url) or {}
        except Exception:
            info = {}

        changed = False
        # map fields
        if is_missing(item.get('演出時間')):
            date = info.get('date') or info.get('event_time') or info.get('event_date')
            if date:
                item['演出時間'] = date
                changed = True
        if is_missing(item.get('演出地點')):
            venue = info.get('venue') or info.get('location')
            if venue:
                item['演出地點'] = venue
                changed = True
        if is_missing(item.get('票價')):
            price = info.get('price')
            if price:
                item['票價'] = price
                changed = True

        if changed:
            updated += 1

        time.sleep(0.6)

    if updated:
        with open(DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"檢查筆數: {inspected}, 用 site crawlers 更新筆數: {updated}")

if __name__ == '__main__':
    main()
