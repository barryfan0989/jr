"""
Tier 1 爬蟲 - 主流核心流量售票網站
"""
from crawlers.base_crawler import BaseTicketCrawler


class TicketComCrawler(BaseTicketCrawler):
    """年代售票"""
    
    def get_target_url(self) -> str:
        return 'https://ticket.com.tw/dm.html'
