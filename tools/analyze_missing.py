import json
from collections import Counter

PATH = "data/concerts.json"

def is_missing(val):
    if val is None:
        return True
    v = str(val).strip()
    return v == "" or v in ("未公布", "TBD", "待公告")

def main():
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    missing_counts = Counter()
    source_missing = {}
    samples = []

    for item in data:
        src = item.get("來源網站", "unknown")
        missing_fields = []
        for k in ("演出時間", "演出地點", "票價"):
            if is_missing(item.get(k, None)):
                missing_counts[k] += 1
                missing_fields.append(k)
        if missing_fields:
            source_missing.setdefault(src, 0)
            source_missing[src] += 1
            if len(samples) < 30:
                samples.append({"演出藝人": item.get("演出藝人"), "網址": item.get("網址"), "缺失": missing_fields})

    print("總筆數:", total)
    print("缺失統計:")
    for k in ("演出時間", "演出地點", "票價"):
        print(f"  {k}: {missing_counts.get(k,0)}")

    print("\n來源網站缺失統計（前 20）:")
    for src, c in Counter(source_missing).most_common(20):
        print(f"  {src}: {c}")

    print("\n缺失樣本（最多 30）:")
    for s in samples:
        print(f"  - {s['演出藝人']} | {s['網址']} | 缺: {', '.join(s['缺失'])}")

if __name__ == '__main__':
    main()
