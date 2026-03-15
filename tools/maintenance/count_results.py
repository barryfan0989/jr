#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

data = json.load(open('all_events_20260303_025644.json', 'r', encoding='utf-8'))
print(f'總記錄數: {len(data)}\n')

sources = {}
for e in data:
    src = e.get('來源網站', '未知')
    sources[src] = sources.get(src, 0) + 1

print('各網站統計:')
for k, v in sorted(sources.items(), key=lambda x: x[1], reverse=True):
    print(f'  {k}: {v}')
