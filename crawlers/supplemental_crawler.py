import json
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

DATA_PATH = "data/concerts.json"
BACKUP_PATH = "data/concerts_backup_supplemental.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}

def extract_by_regex(text, patterns):
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0).strip()
    return None

def parse_generic(text):
    # 演出時間
    time_patterns = [r"\d{4}年\s*\d{1,2}月\s*\d{1,2}日[\(（]?.{0,30}[\)）]?",
                     r"\d{1,2}/\d{1,2}/\d{4}",
                     r"\d{1,2}月\s*\d{1,2}日"]

    # 地點
    place_patterns = [r"(地點|場地|地址|Venue)[:：\s\-–]{0,5}.{1,80}", r"場館[:：\s\-–].{1,80}"]

    # 票價
    price_patterns = [r"票價[:：\s\-–].{1,80}", r"NT\$?\s?\d{3,6}", r"\d{3,6}元"]

    t = extract_by_regex(text, time_patterns)
    p = extract_by_regex(text, place_patterns)
    r = extract_by_regex(text, price_patterns)
    return t, p, r


def parse_indievox(soup, text):
    # Attempt to extract from common Indievox detail containers
    candidates = []
    sel = soup.select_one('#activity-detail, .activity-detail, .activity-content, .activity-info')
    if sel:
        candidates.append(sel.get_text(separator='\n'))

    # Fallback: find list items or paragraphs mentioning keywords
    for tag in soup.find_all(['p', 'li', 'div', 'span']):
        if tag.string and re.search(r'地點|場地|地址|票價|時間|日期', tag.string):
            candidates.append(tag.get_text())

    # also try meta description
    md = soup.find('meta', attrs={'name': 'description'})
    if md and md.get('content'):
        candidates.append(md.get('content'))

    for c in candidates:
        t, p, r = parse_generic(c)
        if p or r or t:
            return t, p, r

    # last resort: search full page text
    return parse_generic(text)


def parse_ticketcom(soup, text):
    # TicketCom often uses labeled rows or strong labels
    # Search for label nodes
    labels = ['演出時間', '演出地點', '場地', '地點', '票價', '價格']
    snippets = []
    for lab in labels:
        node = soup.find(text=re.compile(lab))
        if node:
            parent = node.parent
            # aggregate nearby siblings
            snippet = parent.get_text(separator='\n')
            snippets.append(snippet)
            # also include parent's parent
            if parent.parent:
                snippets.append(parent.parent.get_text(separator='\n'))

    # try table rows
    for tr in soup.find_all('tr'):
        txt = tr.get_text(separator='\n')
        if re.search(r'演出時間|日期|地點|票價', txt):
            snippets.append(txt)

    for s in snippets:
        t, p, r = parse_generic(s)
        if p or r or t:
            return t, p, r

    # try meta og:description
    og = soup.find('meta', attrs={'property': 'og:description'})
    if og and og.get('content'):
        return parse_generic(og.get('content'))

    return parse_generic(text)


def find_ticketcom_application_url(soup, base_url):
    # find links pointing to application pages (product detail)
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'application/UTK' in href or 'PRODUCT_ID=' in href or '/application/' in href:
            if href.startswith('http'):
                return href
            if href.startswith('/'):
                return 'https://ticket.com.tw' + href
            return base_url.rstrip('/') + '/' + href.lstrip('/')
    return None

def fetch(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception:
        return None


_DRIVER = None

def _get_driver():
    global _DRIVER
    if _DRIVER is None:
        try:
            from seleniumbase import Driver
            _DRIVER = Driver(uc=True, headless=True)
        except Exception:
            _DRIVER = None
    return _DRIVER

def fetch_with_browser(url):
    driver = _get_driver()
    if not driver:
        return None
    try:
        driver.get(url)
        time.sleep(2)
        return driver.page_source
    except Exception:
        return None


def collect_ticketcom_application_links(url):
    driver = _get_driver()
    if not driver:
        return []
    try:
        driver.get(url)
        time.sleep(2)
        # scroll a bit
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/application/' in href or 'UTK02' in href or 'PRODUCT_ID=' in href:
                if href.startswith('http'):
                    links.append(href)
                elif href.startswith('/'):
                    links.append('https://ticket.com.tw' + href)
                else:
                    links.append(url.rstrip('/') + '/' + href.lstrip('/'))
        return list(dict.fromkeys(links))
    except Exception:
        return []

def process_entry(item):
    url = item.get("網址")
    if not url:
        return {}
    # Try browser fetch for sites that require JS
    html = None
    parsed = urlparse(url)
    hostname = parsed.hostname or ''
    if 'indievox.com' in hostname or 'ticket.com.tw' in hostname or 'ticket.com' in hostname:
        html = fetch_with_browser(url)
    if not html:
        html = fetch(url)
    if not html:
        return {}
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator='\n')

    # site-specific parse first
    t = place = price = None
    if 'indievox.com' in hostname:
        t, place, price = parse_indievox(soup, text)
    elif 'ticket.com.tw' in hostname or 'ticket.com' in hostname:
        t, place, price = parse_ticketcom(soup, text)

        # If parsing failed, try to find an application/detail page and follow it
        if not (t or place or price):
            # try direct links first
            app_url = find_ticketcom_application_url(soup, url)
            if app_url:
                inner_html = fetch_with_browser(app_url) or fetch(app_url)
                if inner_html:
                    inner_soup = BeautifulSoup(inner_html, 'lxml')
                    t2, place2, price2 = parse_ticketcom(inner_soup, inner_soup.get_text('\n'))
                    t = t or t2
                    place = place or place2
                    price = price or price2
            # if still nothing, try collecting application links via browser navigation
            if not (t or place or price):
                app_links = collect_ticketcom_application_links(url)
                for aurl in app_links[:3]:
                    inner_html = fetch_with_browser(aurl) or fetch(aurl)
                    if not inner_html:
                        continue
                    inner_soup = BeautifulSoup(inner_html, 'lxml')
                    t2, place2, price2 = parse_ticketcom(inner_soup, inner_soup.get_text('\n'))
                    t = t or t2
                    place = place or place2
                    price = price or price2
                    if t or place or price:
                        break

    # fallback to generic
    if not (t or place or price):
        t, place, price = parse_generic(text)

    results = {}
    if (not item.get("演出時間") or item.get("演出時間") in ("", "未公布")) and t:
        results["演出時間"] = t
    if (not item.get("演出地點") or item.get("演出地點") in ("", "未公布")) and place:
        # cleanup
        results["演出地點"] = re.sub(r"^(地點[:：\s\-–]+|場地[:：\s\-–]+)", "", place)
    if (not item.get("票價") or item.get("票價") in ("", "未公布")) and price:
        results["票價"] = price

    return results

def main():
    with open(DATA_PATH, encoding='utf-8') as f:
        data = json.load(f)

    updated = 0
    inspected = 0
    # backup
    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    for item in data:
        src = item.get("來源網站", "").strip()
        # focus on Indievox and TicketCom
        if src not in ("Indievox", "TicketCom"):
            continue
        # if both 演出地點 and 票價 are present, skip
        if item.get("演出地點") and item.get("演出地點") not in ("", "未公布") and item.get("票價") and item.get("票價") not in ("", "未公布"):
            continue
        inspected += 1
        res = process_entry(item)
        if res:
            item.update(res)
            updated += 1
        time.sleep(0.5)

    if updated:
        with open(DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"檢查筆數: {inspected}, 更新筆數: {updated}")

if __name__ == '__main__':
    main()
