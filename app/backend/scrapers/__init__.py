# Scrapers package
from .base import BaseScraper
from .rss_scraper import RssScraper
from .web_scraper import WebScraper
from .web3_scraper import Web3Scraper
from .kaggle_scraper import KaggleScraper
from .tech_media_scraper import TechMediaScraper, Kr36Scraper, HuxiuScraper

# New scrapers for source expansion
from .airdrop_scraper import AirdropScraper
from .data_competition_scraper import DataCompetitionScraper
from .hackathon_aggregator_scraper import HackathonAggregatorScraper
from .bounty_scraper import BountyScraper
from .enterprise_scraper import EnterpriseScraper
from .government_scraper import GovernmentScraper
from .design_competition_scraper import DesignCompetitionScraper
from .coding_competition_scraper import CodingCompetitionScraper

# Firecrawl-based scrapers
from .firecrawl_scraper import FirecrawlScraper
from .universal_scraper import UniversalScraper

__all__ = [
    'BaseScraper',
    'RssScraper',
    'WebScraper',
    'Web3Scraper',
    'KaggleScraper',
    'TechMediaScraper',
    'Kr36Scraper',
    'HuxiuScraper',
    # New scrapers
    'AirdropScraper',
    'DataCompetitionScraper',
    'HackathonAggregatorScraper',
    'BountyScraper',
    'EnterpriseScraper',
    'GovernmentScraper',
    'DesignCompetitionScraper',
    'CodingCompetitionScraper',
    # Firecrawl scrapers
    'FirecrawlScraper',
    'UniversalScraper',
]
