import json

PATH = "data/concerts.json"

def is_missing(v):
    if v is None:
        return True
    s = str(v).strip()
    return s == "" or s in ("未公布", "TBD", "待公告")

def main():
    with open(PATH, encoding='utf-8') as f:
        data = json.load(f)

    missing = []
    for i, item in enumerate(data):
        miss = []
        for k in ("演出時間", "演出地點", "票價"):
            if is_missing(item.get(k, None)):
                miss.append(k)
        if miss:
            missing.append((i, item.get('來源網站'), item.get('演出藝人'), item.get('網址'), miss))

    print(f"總缺失筆數: {len(missing)}")
    for idx, src, artist, url, miss in missing[:50]:
        print(f"[{idx}] {src} | {artist} | {url} | 缺: {','.join(miss)}")

if __name__ == '__main__':
    main()
