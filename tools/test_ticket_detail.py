import sys
import os
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from crawlers.tier1_crawlers import TicketComCrawler

DATA_PATH = "data/concerts.json"

def load_missing_ticket_urls(limit=8):
    with open(DATA_PATH, encoding='utf-8') as f:
        data = json.load(f)
    missing = []
    for i, item in enumerate(data):
        if item.get('來源網站') == 'TicketCom':
            if (not item.get('演出地點') or item.get('演出地點') in ('', '未公布')) or (not item.get('票價') or item.get('票價') in ('', '未公布')):
                missing.append((i, item.get('網址')))
        if len(missing) >= limit:
            break
    return missing

def main():
    tc = TicketComCrawler()
    urls = load_missing_ticket_urls(10)
    for idx, url in urls:
        print('---')
        print(idx, url)
        try:
            info = tc._scrape_event_detail(url)
            print(json.dumps(info, ensure_ascii=False, indent=2))
        except Exception as e:
            print('error', e)

if __name__ == '__main__':
    main()
