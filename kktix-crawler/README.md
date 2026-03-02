# KKTIX 活動爬蟲

自動爬取 KKTIX 平台的音樂類活動資訊。

## 功能

- **自動翻頁** - 自動掃描所有活動頁面
- **詳細資訊提取** - 自動解析活動名稱、藝人、日期、地點、票種等
- **反爬蟲繞過** - 使用 SeleniumBase + UC 模式和 curl_cffi 穿透 Cloudflare 防火牆

## 安裝

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 簡單測試（測試單個活動）

```bash
python test_kktix.py
```

### 2. 全量爬取

```bash
python main.py
```

## 核心函數

在 `crawlers/kktix_crawler.py` 中：

```python
# 自動翻頁爬取所有活動 URL
event_urls = get_global_events(base_url)

# 解析單個活動詳細資訊
event_data = scrape_kktix_event_detail(url)
```

## 回傳的活動資料結構

```python
{
    "source_platform": "KKTIX",
    "original_url": "...",
    "event_name": "活動名称",
    "artist": "演出藝人",
    "location": "活動地點",
    "event_date": "2025/01/01",
    "event_time_only": "19:30",
    "sale_date": "2024/12/01",
    "sale_time_only": "10:00",
    "tickets": [
        {"ticket_type": "預售票", "price": 1500},
        {"ticket_type": "全票", "price": 2000}
    ]
}
```

## 依賴套件

- `seleniumbase` - 自動化瀏覽器（用 UC 模式繞過反爬蟲）
- `beautifulsoup4` - HTML 解析
- `curl-cffi` - 穿透 Cloudflare 防火牆
