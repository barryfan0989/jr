"""
Tier 1 爬蟲 - 主流核心流量售票網站
"""
from crawlers.base_crawler import BaseTicketCrawler


class TixCraftCrawler(BaseTicketCrawler):
    """拓元售票 - 台灣最大售票系統"""
    
    def get_target_url(self) -> str:
        return 'https://tixcraft.com/activity/game'


class TicketComCrawler(BaseTicketCrawler):
    """年代售票"""
    
    def get_target_url(self) -> str:
        return 'https://ticket.com.tw/dm.html'


class KKTIXCrawler(BaseTicketCrawler):
    """KKTIX 活動售票平台"""
    
    def get_target_url(self) -> str:
        return 'https://kktix.com/events'
