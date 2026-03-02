"""
Tier 1 爬蟲 - 主流核心流量售票網站
"""
import time
import re
import unicodedata
from typing import List, Dict
from bs4 import BeautifulSoup
from crawlers.base_crawler import BaseTicketCrawler


class TicketComCrawler(BaseTicketCrawler):
    """年代售票"""
    
    def get_target_url(self) -> str:
        return 'https://ticket.com.tw/dm.html'


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
                print(f"🔧 {self.site_name}: 初始化瀏覽器驅動...")
                self.driver = Driver(uc=True, headless=True)
            except ImportError:
                print(f"✗ {self.site_name}: seleniumbase 未安裝")
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
            print(f"📡 {self.site_name}: 正在掃蕩第 {page} 頁...")
            
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
                print(f"⚠️  {self.site_name}: 第 {page} 頁掃蕩出錯 - {e}")
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
            print(f"💥 {self.site_name}: 解析 {url} 失敗 - {e}")
            return None
    
    def run(self) -> List[Dict]:
        """執行 KKTIX 爬蟲"""
        print(f"\n{'='*60}")
        print(f"🎵 {self.site_name} 爬蟲啟動")
        print(f"{'='*60}")
        
        try:
            # 取得所有活動網址
            event_urls = self._get_global_events()
            
            if not event_urls:
                print(f"❌ {self.site_name}: 找不到活動網址")
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
                        print(f"✓ [{i}/{len(event_urls)}] {event_data['title'][:30]}")
                except Exception as e:
                    print(f"✗ [{i}/{len(event_urls)}] 錯誤: {e}")
            
            print(f"\n✓ {self.site_name}: 共成功抓取 {success_count} 場活動")
            return all_events
            
        finally:
            self._close_driver()
