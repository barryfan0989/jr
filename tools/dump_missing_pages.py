import json
import os
import time
import requests
from bs4 import BeautifulSoup

DATA_PATH = "data/concerts.json"
OUT_DIR = "tmp_pages"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def is_missing(v):
    if v is None:
        return True
    s = str(v).strip()
    return s == "" or s in ("未公布", "TBD", "待公告")

def main(n=8):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(DATA_PATH, encoding='utf-8') as f:
        data = json.load(f)

    missing = []
    for i, item in enumerate(data):
        miss = []
        for k in ("演出時間", "演出地點", "票價"):
            if is_missing(item.get(k, None)):
                miss.append(k)
        if miss:
            missing.append((i, item))

    for idx, item in missing[:n]:
        url = item.get('網址')
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.encoding = r.apparent_encoding
            html = r.text
            fname = f"{idx}.html"
            with open(os.path.join(OUT_DIR, fname), 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"Saved {idx} -> {fname}")
        except Exception as e:
            print(f"Failed {idx} {url}: {e}")
        time.sleep(0.5)

if __name__ == '__main__':
    main()
