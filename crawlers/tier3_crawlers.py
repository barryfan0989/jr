"""
Tier 3 爬蟲 - 補充/佔位
"""
from crawlers.base_crawler import BaseTicketCrawler


class BooksTicketCrawler(BaseTicketCrawler):
    """博客來售票網"""
    
    def get_target_url(self) -> str:
        return 'https://tickets.books.com.tw'
