"""
Tier 1 爬蟲 - 主流核心流量售票網站
"""
import time
import re
import unicodedata
import asyncio
import sys
from typing import List, Dict
from bs4 import BeautifulSoup
from crawlers.base_crawler import BaseTicketCrawler


class TicketComCrawler(BaseTicketCrawler):
    """年代售票 - SeleniumBase 瀏覽器自動化爬蟲"""
    
    def __init__(self):
        super().__init__()
        self.driver = None
    
    def get_target_url(self) -> str:
        return 'https://ticket.com.tw/dm.html'
    
    def _get_driver(self):
        """取得或創建瀏覽器驅動"""
        if self.driver is None:
            try:
                from seleniumbase import Driver
                print(f"[設定] {self.site_name}: 初始化瀏覽器驅動...")
                self.driver = Driver(uc=True, headless=True)
            except ImportError:
                print(f"[失敗] {self.site_name}: seleniumbase 未安裝")
                return None
        return self.driver
    
    def _close_driver(self):
        """關閉瀏覽器驅動"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except:
                pass
    
    def _extract_event_urls_with_browser(self) -> List[str]:
        """使用瀏覽器提取所有活動 URL"""
        driver = self._get_driver()
        if not driver:
            return []
        
        all_urls = set()
        
        try:
            print(f"[掃蕩] {self.site_name}: 使用瀏覽器加載列表...")
            driver.get(self.get_target_url())
            time.sleep(3)
            
            # 多次滾動加載更多內容
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # 尋找所有活動連結 - 更寬鬆的條件
            for a in soup.find_all('a', href=True):
                href = a.get('href', '').strip()
                if not href:
                    continue
                
                # TicketCom 活動 URL 特徵
                if 'utk' in href.lower() or '/dm/' in href:
                    if href.startswith('http'):
                        full_url = href
                    elif href.startswith('/'):
                        full_url = 'https://ticket.com.tw' + href
                    elif href.startswith('../'):
                        full_url = 'https://ticket.com.tw/dm/' + href.replace('../', '')
                    else:
                        full_url = 'https://ticket.com.tw/' + href
                    
                    # 驗證並添加
                    if 'ticket.com.tw' in full_url and full_url.startswith('http'):
                        all_urls.add(full_url)
            
            valid_urls = list(all_urls)
            print(f"[掃蕩] {self.site_name}: 找到 {len(valid_urls)} 個活動連結")
            return valid_urls
            
        except Exception as e:
            print(f"[警告] 提取 URL 失敗: {e}")
            return []
    
    def _scrape_event_detail(self, url: str) -> Dict:
        """使用瀏覽器抓取單一活動詳細資訊"""
        driver = self._get_driver()
        if not driver:
            return None
        
        try:
            print(f"[抓取] {url[:50]}...")
            driver.get(url)
            time.sleep(2)
            
            raw_source = driver.page_source
            norm_source = unicodedata.normalize('NFKC', raw_source)
            soup = BeautifulSoup(norm_source, "html.parser")
            
            # 提取標題 - 多種策略
            title = '未知'
            
            # 策略1: 找標題標籤
            for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                text = header.text.strip()
                if text and 3 < len(text) < 100:
                    title = text
                    break
            
            # 策略2: 找 class 包含 title 的元素
            if title == '未知':
                for elem in soup.find_all(class_=re.compile(r'title|name|event', re.I)):
                    text = elem.text.strip()
                    if text and 3 < len(text) < 100:
                        title = text
                        break
            
            # 策略3: 從 <title> 標籤提取
            if title == '未知' and soup.title:
                page_title = soup.title.text.strip()
                # 移除網站名稱等後綴
                title = re.split(r'[-－|｜]', page_title)[0].strip()
                if len(title) <= 3 or len(title) > 100:
                    title = '未知'
            
            # 提取日期
            date_text = '未公布'
            full_text = soup.get_text()
            
            date_patterns = [
                r'(202[0-9]年[0-9]{1,2}月[0-9]{1,2}日)',
                r'(202[0-9]/[0-9]{1,2}/[0-9]{1,2})',
                r'(\d{1,2}/\d{1,2})',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, full_text)
                if match:
                    date_text = match.group(1)
                    break
            
            # 提取地點
            location = '未公布'
            for text in soup.stripped_strings:
                if any(keyword in text for keyword in ['Hall', '舞台', '座', '廳', '館']):
                    location = text.strip()[:30]
                    break
            
            # 提取藝人
            artist = '未知'
            clean_title = re.sub(r'^【.*?】|\[.*?\]|\(.*?\)', '', title).strip()
            artist_match = re.search(r'^([^－\-—：:\s（]+)', clean_title)
            if artist_match:
                potential_artist = artist_match.group(1).strip()
                if 2 < len(potential_artist) < 50:
                    artist = potential_artist
            
            return {
                'title': title,
                'date': date_text,
                'location': location,
                'artist': artist,
                'url': url,
                'source': self.site_name
            }
            
        except Exception as e:
            print(f"[警告] 解析失敗: {e}")
            return None
    
    def run(self) -> List[Dict]:
        """執行爬蟲 - 使用瀏覽器自動化"""
        print(f"\n{'='*60}")
        print(f"{self.site_name} 爬蟲啟動 (瀏覽器自動化)")
        print(f"{'='*60}")
        
        try:
            # 使用瀏覽器提取活動 URL
            event_urls = self._extract_event_urls_with_browser()
            
            if not event_urls:
                print(f"[失敗] {self.site_name}: 找不到活動 URL")
                return []
            
            # 過濾真正的活動頁面 URL（只排除明顯的系統頁面）
            filtered_urls = []
            exclude_keywords = ['login', 'member', 'logout', 'register', 'search', 'sitemap']
            # 必須包含活動ID特徵
            for url in event_urls:
                # 排除系統頁面
                if any(keyword in url.lower() for keyword in exclude_keywords):
                    continue
                # 必須是活動頁面（包含 utk 或特定路徑）
                if 'utk' in url.lower() or '/show/' in url or '/dm/' in url:
                    filtered_urls.append(url)
            
            # 增加爬取數量到 50
            max_events = 50
            filtered_urls = filtered_urls[:max_events]
            
            print(f"[掃蕩] {self.site_name}: 開始爬取前 {len(filtered_urls)} 個活動...\n")
            
            all_events = []
            success_count = 0
            
            for i, event_url in enumerate(filtered_urls, 1):
                try:
                    event = self._scrape_event_detail(event_url)
                    if event and event['title'] != '未知' and len(event['title']) > 3:
                        all_events.append(event)
                        success_count += 1
                        print(f"[成功] [{i}/{len(filtered_urls)}] {event['title'][:40]}")
                    else:
                        print(f"[略過] [{i}/{len(filtered_urls)}] 無效標題: {event.get('title', 'None') if event else 'None'}")
                except Exception as e:
                    print(f"[錯誤] [{i}/{len(filtered_urls)}] {str(e)[:50]}")
            
            print(f"\n[成功] {self.site_name}: 共找到 {success_count} 場活動")
            return all_events
            
        except Exception as e:
            print(f"[失敗] {e}")
            return []
        
        finally:
            self._close_driver()


class KKTIXCrawler(BaseTicketCrawler):
    """KKTIX 票務平台爬蟲"""
    
    def __init__(self):
        super().__init__()
        self.driver = None
        self.base_url = "https://kktix.com/events?utf8=%E2%9C%93&search=&max_price=&min_price=&start_at=&end_at=&event_tag_ids_in=1%2C7"
    
    def get_target_url(self) -> str:
        return self.base_url
    
    def _get_driver(self):
        """取得或創建瀏覽器驅動"""
        if self.driver is None:
            try:
                from seleniumbase import Driver
                print(f"[設定] {self.site_name}: 初始化浏覽器驅動...")
                self.driver = Driver(uc=True, headless=True)
            except ImportError:
                print(f"[失敗] {self.site_name}: seleniumbase 未安裝")
                return None
        return self.driver
    
    def _close_driver(self):
        """關閉瀏覽器驅動"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except:
                pass
    
    def _get_global_events(self) -> List[str]:
        """自動翻頁巡航：抓取所有音樂類標籤下的活動網址"""
        driver = self._get_driver()
        if not driver:
            return []
        
        all_urls = set()
        page = 1
        max_pages = 15
        
        while page <= max_pages:
            paged_url = f"{self.base_url}&page={page}"
            print(f"[掃蕩] 正在掃蕩第 {page} 頁...")
            
            try:
                driver.get(paged_url)
                time.sleep(3)
                
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                soup = BeautifulSoup(driver.page_source, "html.parser")
                current_page_urls = set()
                
                for a in soup.select('a[href*="/events/"]'):
                    href = a.get("href", "")
                    if ".kktix.cc/events/" in href and "dashboard" not in href:
                        full_url = "https:" + href if href.startswith("//") else href
                        current_page_urls.add(full_url)
                
                new_urls = current_page_urls - all_urls
                if not new_urls:
                    break
                
                all_urls.update(new_urls)
                page += 1
            except Exception as e:
                print(f"[警告] 第 {page} 頁掃蕩出錯 - {e}")
                break
        
        return list(all_urls)
    
    def _scrape_event_detail(self, url: str) -> Dict:
        """抓取單一活動詳細資訊"""
        driver = self._get_driver()
        if not driver:
            return None
        
        try:
            driver.get(url)
            time.sleep(3)
            
            raw_source = driver.page_source
            norm_source = unicodedata.normalize('NFKC', raw_source)
            soup = BeautifulSoup(norm_source, "html.parser")
            
            h1 = soup.find("h1")
            if not h1:
                return None
            
            name = h1.text.strip()
            
            event_data = {
                "title": name,
                "date": "未公布",
                "url": url,
                "artist": "無",
                "location": "未取得",
                "event_date": "未取得",
                "sale_date": "未取得",
                "source": self.site_name
            }
            
            full_text = soup.get_text(separator=" ")
            condensed = re.sub(r'\s+', '', full_text)
            
            # 提取藝人
            clean_name = re.sub(
                r'^(?:【.*?】|\[.*?\]|\(.*?\)|\d+/\d+|RE:|[0-9]{4}年?|\s*)+', '', name).strip()
            artist_match = re.search(r'^([^－\-—：:\s（]+)', clean_name)
            if artist_match:
                detected = artist_match.group(1).strip()
                if 1 < len(detected) < 15:
                    event_data["artist"] = detected
            
            # 提取活動日期
            d_match = re.search(
                r'(202[4-6][/年\-\.][0-9]{1,2}[/月\-\.][0-9]{1,2})', full_text)
            if d_match:
                date_str = d_match.group(1).replace("年", "/").replace("月", "/").replace("日", "").strip()
                event_data["event_date"] = date_str
                event_data["date"] = date_str
            
            # 提取啟售時間
            sale_match = re.search(
                r'(?:啟售|開賣|售票時間)[\s:：｜]*([0-9]{4}[/年\-\.][0-9]{1,2}[/月\-\.][0-9]{1,2}).*?([0-9]{1,2}[:：][0-9]{2})', full_text)
            if sale_match:
                event_data["sale_date"] = sale_match.group(1).replace("年", "/").replace("月", "/").replace("日", "").strip()
            
            # 提取活動地點
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
                    event_data["location"] = l_match.group(1).strip().split("地址")[0].strip()
            
            return event_data
            
        except Exception as e:
            print(f"[錯誤] {self.site_name}: 解析 {url} 失敗 - {e}")
            return None
    
    def run(self) -> List[Dict]:
        """執行 KKTIX 爬蟲"""
        print(f"\n{'='*60}")
        print(f"KKTIX 爬蟲啟動")
        print(f"{'='*60}")
        
        try:
            # 取得所有活動網址
            event_urls = self._get_global_events()
            
            if not event_urls:
                print(f"[失敗] {self.site_name}: 找不到活動網址")
                return []
            
            print(f"🎯 {self.site_name}: 偵測到 {len(event_urls)} 個活動，開始深度解析...\n")
            
            all_events = []
            success_count = 0
            
            for i, url in enumerate(event_urls, 1):
                try:
                    event_data = self._scrape_event_detail(url)
                    if event_data:
                        all_events.append(event_data)
                        success_count += 1
                        print(f"[成功] [{i}/{len(event_urls)}] {event_data['title'][:30]}")
                except Exception as e:
                    print(f"[錯誤] [{i}/{len(event_urls)}] 錯誤: {e}")
            
            print(f"\n[成功] {self.site_name}: 共成功抳取 {success_count} 場活動")
            return all_events
            
        finally:
            self._close_driver()


class TixCraftCrawler(BaseTicketCrawler):
    """拓元售票（TixCraft）爬蟲 - 使用新的精確字段爬蟲"""
    
    def __init__(self):
        super().__init__()
        self.site_name = "TixCraft"
    
    def get_target_url(self) -> str:
        return 'https://tixcraft.com/activity'
    
    def run(self) -> List[Dict]:
        """執行 TixCraft 爬蟲 - 使用新的精確爬蟲"""
        print(f"\n{'='*60}")
        print(f"TixCraft 爬蟲啟動 (精確字段爬蟲)")
        print(f"{'='*60}")
        
        try:
            # 動態導入新的爬蟲類
            import sys
            import os
            scraper_path = os.path.join(os.path.dirname(__file__), '..', 'tixcraft_scraper')
            if scraper_path not in sys.path:
                sys.path.insert(0, scraper_path)
            
            from tixcraft_precision_field_scraper import TixcraftPrecisionFieldScraper
            
            # 創建並執行新爬蟲
            scraper = TixcraftPrecisionFieldScraper()
            result = scraper.scrape_all_events()
            
            if not result or not result.get('events'):
                print(f"[失敗] {self.site_name}: 未爬取到活動")
                return []
            
            # 轉換為標準格式
            events = result.get('events', [])
            all_events = []
            
            for event in events:
                try:
                    # 從 event_info 中提取日期
                    date_text = '未公布'
                    event_info = event.get('event_info', '')
                    if event_info and event_info != '未找到':
                        date_match = re.search(r'(202[0-9]/[0-9]{1,2}/[0-9]{1,2}|[0-9]{1,2}月[0-9]{1,2}日|[0-9]{1,2}:\d{2})', event_info)
                        if date_match:
                            date_text = date_match.group(1)
                    
                    # 轉換格式
                    converted_event = {
                        'title': event.get('title', '未知'),
                        'date': date_text,
                        'location': event.get('location', '未公布'),
                        'artist': event.get('title', '未知').split('-')[0].strip()[:30],  # 簡化藝人提取
                        'url': event.get('url', ''),
                        'source': self.site_name
                    }
                    
                    if converted_event['title'] != '未知':
                        all_events.append(converted_event)
                        print(f"[成功] {converted_event['title'][:40]}")
                
                except Exception as e:
                    print(f"[轉換失敗] {str(e)[:50]}")
                    continue
            
            print(f"\n[成功] {self.site_name}: 共找到 {len(all_events)} 場活動")
            return all_events
            
        except Exception as e:
            print(f"[失敗] {self.site_name}: {e}")
            return []


