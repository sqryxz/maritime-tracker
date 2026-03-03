"""Scrapers package for maritime data sources."""

from scrapers.base import BaseScraper
from scrapers.fbx_scraper import FBXScraper
from scrapers.unctad_scraper import UNCTADScraper
from scrapers.ais_scraper import AISScraper

__all__ = [
    "BaseScraper",
    "FBXScraper",
    "UNCTADScraper",
    "AISScraper",
]
