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
            # 截取前 30000 字元節省 token
            html_truncated = html[:30000]
            
            prompt = f"""
請從以下 HTML 中提取所有演唱會或音樂會活動資訊。

網站：{self.site_name}

返回格式必須是嚴格的 JSON 陣列，每個活動包含：
{{"title": "活動標題", "date": "日期時間或'未公布'", "url": "完整連結"}}

規則：
1. 只返回有效的 JSON 陣列，不要任何其他文字、解釋或 markdown
2. 如果找不到任何活動，返回空陣列 []
3. url 必須是完整的網址（包含 https://）
4. 只提取音樂相關的活動（演唱會、音樂節、LiveHouse 演出等）

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
