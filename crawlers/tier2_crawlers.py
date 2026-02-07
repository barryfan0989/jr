"""
Tier 2 爬蟲 - 次主流與獨立音樂平台
"""
from crawlers.base_crawler import BaseTicketCrawler


class IndievoxCrawler(BaseTicketCrawler):
    """iNDIEVOX 獨立音樂售票平台"""
    
    def get_target_url(self) -> str:
        return 'https://www.indievox.com/activity/list'


class AccupassCrawler(BaseTicketCrawler):
    """Accupass 活動通"""
    
    def get_target_url(self) -> str:
        return 'https://www.accupass.com/search?q=演唱會'
