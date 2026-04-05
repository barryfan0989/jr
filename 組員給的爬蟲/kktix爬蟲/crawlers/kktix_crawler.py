import time
import re
import json
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
        print(f" 正在掃蕩第 {page} 頁...")

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
        norm_source = unicodedata.normalize('NFKC', driver.page_source)
        soup = BeautifulSoup(norm_source, "html.parser")

        # 1. 結構化資料優先 (取得正確的時間地點)
        json_ld = {}
        script_tag = soup.find("script", type="application/ld+json")
        if script_tag:
            try:
                raw_json = json.loads(script_tag.string)
                json_ld = raw_json[0] if isinstance(
                    raw_json, list) else raw_json
            except:
                pass

        h1 = soup.find("h1")
        name = h1.text.strip() if h1 else "未知"
        event_data = {
            "event_name": name, "artist": "無", "event_date": "未取得",
            "event_time_only": "未取得", "sale_date": "未取得",
            "sale_time_only": "未取得", "original_url": url,
            "location": "未取得", "address": "未取得", "tickets": []
        }

        # 2. 核心變數定義
        reg_box = soup.find("div", class_="register-new")
        reg_text = reg_box.get_text(separator=" ") if reg_box else ""
        all_text = soup.get_text(separator=" ")
        clean_text = re.sub(r'\s+', ' ', all_text)

        # 3. 藝人名稱提取 (通用拆分法)
        noise = r'^(?:【.*?】|\[.*?\]|Cancelled|\d+[\.\-/]\d+|\d+/\d+|RE:|[0-9]{4}年?|SOLD OUT|VIP|福利|加購|門票|\s*)+'
        title_clean = re.sub(noise, '', name, flags=re.I).strip()
        parts = re.split(r'[\s\-－—:：\(\)（）「」『』【】\[\]<>〈〉]', title_clean)
        for p in parts:
            p = p.strip()
            if len(p) >= 2 and not p.isdigit():
                if not any(stop in p for stop in ["巡迴", "演唱會", "Live", "Tour", "音樂會"]):
                    event_data["artist"] = p
                    break

        # ---  4. 售票時間：精準過濾與狀態偵測 ---
        sale_keywords = r'(?:啟售|售票|開賣|START|ON SALE|售票時間|開賣時間|發售)'
        date_pattern = r'(202[4-6][/\-\.年\s][0-9]{1,2}[/\-\.月\s][0-9]{1,2}日?)'
        time_pattern = r'([0-9]{1,2}[:：][0-9]{2})'

        # 優先檢查：是否已經有「立即購票」按鈕？ (代表已開賣)
        buy_button = soup.find("a", class_="btn-register")
        is_selling = False
        if buy_button and "立即購票" in buy_button.get_text():
            is_selling = True

        # A. 優先掃描右側按鈕區
        s_m = re.search(date_pattern + r'.*?' + time_pattern, reg_text)

        # B. 如果按鈕區沒抓到，改用全網頁「語意熱點」掃描
        if not s_m:
            s_m = re.search(
                sale_keywords + r'[\s\S]{0,50}?' + date_pattern + r'[\s\S]{0,20}?' + time_pattern, clean_text, re.I)

        if s_m:
            detected_sale_date = re.sub(
                r'[年|月|日]', '/', s_m.group(1)).replace("-", "/").replace(".", "/").strip()
            detected_sale_time = s_m.group(2).replace("：", ":")

            # 修正：檢查抓到的啟售日期是否等於活動日期？
            # 如果相等，且網頁上有購票按鈕，則高機率是誤抓，應設為已開賣
            if detected_sale_date == event_data["event_date"] and is_selling:
                event_data["sale_date"] = "已開賣"
                event_data["sale_time_only"] = "-"
            else:
                event_data["sale_date"] = detected_sale_date
                event_data["sale_time_only"] = detected_sale_time

        # C. 補底：若完全沒抓到日期但有購票按鈕
        elif is_selling:
            event_data["sale_date"] = "販售中"
            event_data["sale_time_only"] = "-"

        # 5. 地點與地址 (JSON-LD + 物理截斷)
        if isinstance(json_ld, dict):
            loc_obj = json_ld.get("location", {})
            if isinstance(loc_obj, dict):
                event_data["location"] = loc_obj.get("name", "未取得")
                addr_obj = loc_obj.get("address", {})
                event_data["address"] = addr_obj.get("streetAddress", "未取得") if isinstance(
                    addr_obj, dict) else str(addr_obj)
            st = json_ld.get("startDate", "")
            if st:
                event_data["event_date"] = st.split("T")[0].replace("-", "/")
                event_data["event_time_only"] = st.split(
                    "T")[1][:5] if "T" in st else "未取得"

        for key in ["location", "address"]:
            if event_data[key] != "未取得":
                for sym in [")", "）", "】", "※", "📍", "💡", "🏠", "票券", "注意"]:
                    event_data[key] = event_data[key].split(sym)[0].strip()

        # 6.  票價與票種 (三階段救援邏輯)
        found_tickets = {}
        year_blacklist = [str(x) for x in range(2024, 2028)]
        bad_keywords = ["日期", "時間", "地點", "地址", "202",
                        "手續費", "退票", "0800", "尚未", "結束", "剩餘", "數量"]

        #  階段 A: 標準表格掃描 (精確度最高)
        rows = soup.find_all("tr")
        for row in rows:
            cells = [c.get_text(strip=True)
                     for c in row.find_all(["td", "th"])]
            if len(cells) >= 2:
                for i, cell in enumerate(cells):
                    p_m = re.search(r'(?:NT\$|TWD|\$)?\s?([0-9,]{3,5})', cell)
                    if p_m:
                        p_raw = p_m.group(1).replace(",", "")
                        p_val = int(p_raw)
                        # 過濾掉年份、門牌或剩餘張數 (倍數過濾)
                        if 300 <= p_val <= 30000 and p_raw not in year_blacklist and p_val % 10 == 0:
                            n_cand = cells[i-1] if i > 0 else cells[i+1]
                            n_cl = re.sub(
                                r'202[4-6][/\-\.][0-9]{4}.*?\+0800', '', n_cand)
                            n_cl = re.sub(
                                r'[\s:：｜$・\-〈〉「」『』]+|TWD|Price|NT|票價|金額', '', n_cl)
                            if 1 < len(n_cl) < 20 and not n_cl.isdigit() and not any(k in n_cl for k in bad_keywords):
                                if p_val not in found_tickets or len(n_cl) > len(found_tickets[p_val]):
                                    found_tickets[p_val] = n_cl

        #  階段 B: 鄰近語意掃描 (補底救援)
        if not found_tickets:
            matches = re.findall(
                r'([^ \s\n\r]{2,10})[\s:：｜]*?(?:NT\$|TWD|\$)\s?([0-9,]{3,5})', clean_text)
            for n_raw, p_raw in matches:
                p = int(p_raw.replace(",", ""))
                if 400 <= p <= 20000 and p % 10 == 0 and str(p) not in year_blacklist:
                    n_cl = re.sub(r'[\s:：｜$・\-]+|TWD|Price|NT', '', n_raw)
                    if 1 < len(n_cl) < 10 and not n_cl.isdigit() and not any(k in n_cl for k in bad_keywords):
                        found_tickets[p] = n_cl

        #  階段 C: 錯誤排除 (末兩位為 0 且排除日期的純數字)
        if not found_tickets:
            potential_prices = re.findall(
                r'(?<![0-9/])(?:NT\$|TWD|\$)?\s?([4-9]00|[1-9][0-9]00)(?![0-9/])', clean_text)
            for p_str in potential_prices:
                p = int(p_str.replace(",", ""))
                if p not in [1200, 1900, 2024, 2025, 2026] and 400 <= p <= 15000:
                    if p not in found_tickets:
                        found_tickets[p] = "一般票"

        # 整理結果
        for p, n in sorted(found_tickets.items(), reverse=True):
            event_data["tickets"].append({"ticket_type": n, "price": p})

        return event_data
    except Exception as e:
        print(f" 解析錯誤: {e}")
        return None
