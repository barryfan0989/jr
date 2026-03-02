"""
基礎爬蟲抽象類別
所有票務網站爬蟲的父類別
"""
import os
import json
from abc import ABC, abstractmethod
from typing import List, Dict
import google.generativeai as genai


class BaseTicketCrawler(ABC):
    """票務網站爬蟲基礎類別"""
    
    def __init__(self):
        self.site_name = self.__class__.__name__.replace('Crawler', '')
        self.gemini_model = None
        self._init_gemini()
    
    def _init_gemini(self):
        """初始化 Gemini API"""
        api_key = os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            print(f"⚠️  {self.site_name}: 未設定 GEMINI_API_KEY")
            return
        
        try:
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
            print(f"✓ {self.site_name}: Gemini API 初始化成功")
        except Exception as e:
            print(f"✗ {self.site_name}: Gemini 初始化失敗 - {e}")
    
    def fetch_html(self, url: str) -> str:
        """
        使用 curl_cffi 繞過 Cloudflare 取得 HTML
        
        Args:
            url: 目標網址
            
        Returns:
            HTML 內容
        """
        try:
            from curl_cffi import requests
            
            print(f"📡 {self.site_name}: 正在訪問 {url}")
            
            response = requests.get(
                url,
                impersonate='chrome110',
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✓ {self.site_name}: 成功取得 HTML ({len(response.text)} 字元)")
                return response.text
            else:
                print(f"✗ {self.site_name}: HTTP {response.status_code}")
                return ""
                
        except ImportError:
            print(f"⚠️  {self.site_name}: curl_cffi 未安裝，改用 requests")
            import requests
            response = requests.get(url, timeout=30)
            return response.text if response.status_code == 200 else ""
            
        except Exception as e:
            print(f"✗ {self.site_name}: 抓取失敗 - {e}")
            return ""
    
    def parse_data(self, html: str) -> List[Dict]:
        """
        使用 Gemini API 解析 HTML 為 JSON
        
        Args:
            html: HTML 內容
            
        Returns:
            活動列表 [{"title": "...", "date": "...", "url": "..."}]
        """
        if not html or not self.gemini_model:
            return []
        
        try:
            # 使用更多的 HTML 內容以獲得更好的解析結果
            html_truncated = html[:50000]
            
            prompt = f"""你是一個專業的音樂活動資訊提取器。請從以下 HTML 代碼中提取所有的演唱會、音樂表演和相關活動的完整資訊。

【重要】返回格式必須是一個 JSON 陣列，整個回應只包含 JSON 陣列，不要有任何其他文字、說明或 markdown 標記。

每個活動的 JSON 對象必須包含以下欄位（使用這些準確的鍵名）：
- "title": 活動的完整標題或藝人名稱（必須）
- "date": 活動日期或演出日期。如果頁面上沒有找到具體日期，請使用 "未公布"（必須）
- "url": 該活動的直接連結網址。必須是完整的 URL，以 https:// 或 http:// 開頭（必須）

提取規則：
1. 提取所有與音樂相關的活動：演唱會、音樂節、LiveHouse 表演、展覽等音樂現場
2. 忽略非音樂相關內容（體育、講座、購物等）
3. 如果網頁中沒有找到任何活動，返回空陣列 [] 
4. URL 必須是該活動的直接連結，如果找不到，就留空字符串 ""
5. 日期應該盡量保留原始格式（例如 2026/03/15, 3月15日, 15 Mar等）

【範例輸出格式】：
[
  {{"title": "藝人名稱 演唱會", "date": "2026/03/15", "url": "https://example.com/event/123"}},
  {{"title": "音樂節名稱", "date": "未公布", "url": "https://example.com/festival/456"}}
]

【重要提醒】：
- 只輸出 JSON 陣列，不要有任何額外的說明、代碼塊標記或 markdown
- 如果無法解析，返回空陣列 []

HTML 內容：
{html_truncated}
"""
            
            print(f"🤖 {self.site_name}: 正在使用 Gemini 解析...")
            
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()
            
            # 清理 markdown 格式
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.split('```')[0].strip()
            
            # 解析 JSON
            events = json.loads(response_text)
            
            if isinstance(events, list):
                print(f"✓ {self.site_name}: 解析成功，找到 {len(events)} 個活動")
                return events
            else:
                print(f"⚠️  {self.site_name}: 回應格式不正確")
                return []
                
        except json.JSONDecodeError as e:
            print(f"✗ {self.site_name}: JSON 解析失敗 - {e}")
            print(f"   原始回應: {response_text[:200]}...")
            return []
            
        except Exception as e:
            print(f"✗ {self.site_name}: Gemini 解析失敗 - {e}")
            return []
    
    @abstractmethod
    def get_target_url(self) -> str:
        """子類別必須實作：返回目標網址"""
        pass
    
    def run(self) -> List[Dict]:
        """
        執行爬蟲流程
        
        Returns:
            活動列表
        """
        print(f"\n{'='*60}")
        print(f"🎯 開始爬取：{self.site_name}")
        print(f"{'='*60}")
        
        url = self.get_target_url()
        html = self.fetch_html(url)
        
        if not html:
            print(f"✗ {self.site_name}: 無法取得 HTML，跳過")
            return []
        
        events = self.parse_data(html)
        
        # 標記來源
        for event in events:
            event['source'] = self.site_name
        
        print(f"{'='*60}\n")
        return events
