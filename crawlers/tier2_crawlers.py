"""
Tier 2 爬蟲 - 次主流與獨立音樂平台
"""
import time
import re
from typing import List, Dict
from bs4 import BeautifulSoup
from crawlers.base_crawler import BaseTicketCrawler


class IndievoxCrawler(BaseTicketCrawler):
    """iNDIEVOX 獨立音樂售票平台 - 使用瀏覽器滾動加載"""
    
    def __init__(self):
        super().__init__()
        self.site_name = "Indievox"
        self.driver = None
    
    def get_target_url(self) -> str:
        return 'https://www.indievox.com/activity/list'
    
    def _get_driver(self):
        """獲取瀏覽器驅動（使用 SeleniumBase）"""
        if self.driver:
            return self.driver
        
        try:
            from seleniumbase import Driver
            self.driver = Driver(uc=True, headless=True)
            return self.driver
        except Exception as e:
            print(f"[錯誤] 無法啟動瀏覽器: {e}")
            return None
    
    def _close_driver(self):
        """關閉瀏覽器"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except:
                pass
    
    def _extract_event_urls_with_scroll(self) -> List[str]:
        """使用瀏覽器滾動加載更多活動"""
        driver = self._get_driver()
        if not driver:
            return []
        
        all_urls = set()
        
        try:
            print(f"[掃蕩] Indievox: 使用瀏覽器加載列表...")
            driver.get(self.get_target_url())
            time.sleep(3)
            
            # 多次滾動加載更多活動
            last_height = 0
            for scroll_count in range(10):  # 滾動10次
                # 滾動到底部
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                
                # 檢查是否還有新內容
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
                # 解析當前頁面的URL
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '').strip()
                    if '/activity/detail/' in href:
                        if href.startswith('http'):
                            all_urls.add(href)
                        else:
                            all_urls.add('https://www.indievox.com' + href)
                
                print(f"[進度] 滾動 {scroll_count + 1} 次，已找到 {len(all_urls)} 個活動")
            
            urls = list(all_urls)
            print(f"[掃蕩] Indievox: 總共找到 {len(urls)} 個活動連結")
            return urls
            
        except Exception as e:
            print(f"[錯誤] 提取 URL 失敗: {e}")
            return []
    
    def _parse_event_detail(self, html: str, url: str) -> Dict:
        """解析詳細活動頁面"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取標題 - 嘗試 h1, h2, 或第一個包含文本的 span/p
            title = '未知'
            h1 = soup.find('h1')
            if h1:
                title = h1.text.strip()
            else:
                h2 = soup.find('h2')
                if h2:
                    title = h2.text.strip()
                else:
                    # 尋找第一個有意義的大標題文本
                    for elem in soup.find_all(['span', 'p', 'div']):
                        text = elem.get_text().strip()
                        if text and 20 < len(text) < 100 and '活動' not in text:
                            title = text
                            break
            
            # 提取日期 - 尋找日期模式
            date_text = '未公布'
            full_text = soup.get_text()
            
            # 尋找中文日期格式 2026年3月8日 或 2026/3/8 等
            date_patterns = [
                r'(202[0-9]年[0-9]{1,2}月[0-9]{1,2}日)',
                r'(202[0-9]/[0-9]{1,2}/[0-9]{1,2})',
                r'(202[0-9]\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日)',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, full_text)
                if match:
                    date_text = match.group(1).replace('年', '/').replace('月', '/').replace('日', '')
                    break
            
            # 提取地點
            location = '未公布'
            for text in soup.stripped_strings:
                if 'Taipei' in text or 'Hall' in text or '舞台' in text:
                    location = text.strip()[:30]
                    break
            
            # 提取藝人
            artist = '未知'
            # 嘗試從標題提取
            clean_title = re.sub(r'^(?:【.*?】|\[.*?\]|\(.*?\)|\d+)', '', title).strip()
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
            print(f"[警告] 解析詳細頁失敗: {e}")
            return None
    
    def run(self) -> List[Dict]:
        """執行爬蟲 - 使用瀏覽器滾動加載"""
        print(f"\n{'='*60}")
        print(f"Indievox 爬蟲啟動 (瀏覽器自動滾動)")
        print(f"{'='*60}")
        
        try:
            # 使用瀏覽器滾動獲取所有活動URL
            event_urls = self._extract_event_urls_with_scroll()
            
            if not event_urls:
                print("[失敗] 找不到活動 URL")
                return []
            
            # 解析每個活動
            all_events = []
            success_count = 0
            
            for i, event_url in enumerate(event_urls, 1):
                try:
                    print(f"[抓取] [{i}/{len(event_urls)}] {event_url.split('/')[-1]}")
                    event_html = self.fetch_html(event_url)
                    time.sleep(0.5)  # 防止過度請求
                    
                    if event_html:
                        event = self._parse_event_detail(event_html, event_url)
                        if event and event['title'] != '未知':
                            all_events.append(event)
                            success_count += 1
                            print(f"[成功] {event['title'][:40]}")
                except Exception as e:
                    print(f"[錯誤] {str(e)[:50]}")
            
            print(f"\n[成功] Indievox: 共找到 {success_count} 場活動")
            return all_events
            
        except Exception as e:
            print(f"[失敗] {e}")
            return []        
        finally:
            self._close_driver()
