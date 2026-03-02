import time
import re
import unicodedata
from bs4 import BeautifulSoup
from seleniumbase import Driver

driver = None


def get_driver():
    global driver
    if driver is None:
        driver = Driver(uc=True, headless=False)
    return driver


def close_driver():
    global driver
    if driver:
        driver.quit()
        driver = None


def get_global_events(base_url):
    """自動翻頁巡航：抓取所有音樂類標籤下的活動網址"""
    driver = get_driver()
    all_urls = set()
    page = 1

    while True:
        paged_url = f"{base_url}&page={page}"
        print(f"📡 [巡航] 正在掃蕩第 {page} 頁...")

        driver.get(paged_url)
        time.sleep(5)

        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        current_page_urls = set()
        for a in soup.select('a[href*="/events/"]'):
            href = a["href"]
            if ".kktix.cc/events/" in href and "dashboard" not in href:
                full_url = "https:" + href if href.startswith("//") else href
                current_page_urls.add(full_url)

        new_urls = current_page_urls - all_urls
        if not new_urls or page > 15:
            break

        all_urls.update(new_urls)
        page += 1

    return list(all_urls)


def scrape_kktix_event_detail(url):
    driver = get_driver()

    try:
        driver.get(url)
        time.sleep(5)

        raw_source = driver.page_source
        norm_source = unicodedata.normalize('NFKC', raw_source)
        soup = BeautifulSoup(norm_source, "html.parser")

        h1 = soup.find("h1")
        if not h1:
            return None
        name = h1.text.strip()

        event_data = {
            "source_platform": "KKTIX",
            "original_url": url,
            "event_name": name,
            "artist": "無",
            "location": "未取得",
            "event_date": "未取得",
            "event_time_only": "未取得",
            "sale_date": "未取得",
            "sale_time_only": "未取得",
            "tickets": []
        }

        full_text = soup.get_text(separator=" ")
        condensed = re.sub(r'\s+', '', full_text)

        # =====  藝人 =====
        clean_name = re.sub(
            r'^(?:【.*?】|\[.*?\]|\(.*?\)|\d+/\d+|RE:|[0-9]{4}年?|\s*)+', '', name).strip()
        artist_match = re.search(r'^([^－\-—：:\s（]+)', clean_name)
        if artist_match:
            detected = artist_match.group(1).strip()
            if 1 < len(detected) < 15:
                event_data["artist"] = detected

        # =====  活動日期 =====
        d_match = re.search(
            r'(202[4-6][/年\-\.][0-9]{1,2}[/月\-\.][0-9]{1,2})', full_text)
        if d_match:
            event_data["event_date"] = d_match.group(1).replace(
                "年", "/").replace("月", "/").replace("日", "").strip()

        # =====  啟售時間 =====
        sale_match = re.search(
            r'(?:啟售|開賣|售票時間)[\s:：｜]*([0-9]{4}[/年\-\.][0-9]{1,2}[/月\-\.][0-9]{1,2}).*?([0-9]{1,2}[:：][0-9]{2})', full_text)
        if sale_match:
            event_data["sale_date"] = sale_match.group(1).replace(
                "年", "/").replace("月", "/").replace("日", "").strip()
            event_data["sale_time_only"] = sale_match.group(
                2).replace("：", ":")

        # =====  活動地點 =====
        venues = ["Legacy TERA", "Legacy Taipei", "THE WALL", "Zepp",
                  "小巨蛋", "海音館", "典空間", "河岸留言", "MOONDOG", "NUZONE", "Corner Max"]
        for v in venues:
            if v.lower() in full_text.lower():
                event_data["location"] = v
                break

        if event_data["location"] == "未取得":
            l_match = re.search(
                r'(?:地點|場地|VENUE)[\s:：｜]*([^(\n\r|｜]{2,30})', full_text)
            if l_match:
                event_data["location"] = l_match.group(
                    1).strip().split("地址")[0].strip()

        # =====  票價  =====
        temp_tickets = {}
        # A. 表格掃描
        for row in soup.find_all("tr"):
            cells = [c.get_text().strip() for c in row.find_all(["td", "th"])]
            if len(cells) >= 2:
                for i, cell in enumerate(cells):
                    p_m = re.search(r'([0-9,]{3,6})', cell)
                    if p_m:
                        try:
                            p = int(p_m.group(1).replace(",", ""))
                            if 400 <= p <= 15000 and p not in range(2024, 2027):
                                n_cand = cells[i-1] if i > 0 else cells[i+1]
                                n_cleaned = re.sub(r'[\s:：｜$・\-]+', '', n_cand)
                                if len(n_cleaned) <= 12:
                                    temp_tickets[p] = n_cleaned
                        except:
                            continue

        # B. 暴力補底
        b_matches = re.findall(
            r'([^\d\s$]{2,10})(?:\$|NT\$|NT\.|:|\.)([0-9]{3,5})', condensed)
        bad = ["地點", "日期", "說明", "地址", "時間", "TWD", "http", "下一步"]
        for n_raw, p_raw in b_matches:
            p = int(p_raw)
            n = n_raw.strip().strip('・｜-')
            if 400 <= p <= 15000 and p % 10 == 0:
                if any(bw in n for bw in bad):
                    continue
                if p not in temp_tickets:
                    temp_tickets[p] = n

        for p, n in sorted(temp_tickets.items(), reverse=True):
            event_data["tickets"].append({"ticket_type": n, "price": p})

        return event_data
    except Exception as e:
        print(f"💥 解析失敗: {e}")
        return None
