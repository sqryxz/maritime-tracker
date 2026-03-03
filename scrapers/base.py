"""Abstract base scraper class."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import logging
import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


@dataclass
class ScrapedData:
    """Container for scraped data."""

    source: str
    timestamp: datetime
    data: dict[str, Any]
    raw_html: str | None = None
    error: str | None = None


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    def __init__(
        self,
        name: str,
        source_url: str,
        timeout: int = 30,
        user_agent: str = "MaritimeScraper/1.0",
    ) -> None:
        """Initialize the scraper.

        Args:
            name: Human-readable name of the data source
            source_url: URL to fetch data from
            timeout: Request timeout in seconds
            user_agent: User agent string for requests
        """
        self.name = name
        self.source_url = source_url
        self.timeout = timeout
        self.user_agent = user_agent
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent})

    def fetch(self) -> ScrapedData:
        """Fetch data from the source.

        Returns:
            ScrapedData object containing the results
        """
        try:
            logger.info(f"Fetching data from {self.name}")
            response = self._session.get(self.source_url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            data = self.parse(soup)
            logger.info(f"Successfully scraped {len(data)} items from {self.name}")
            return ScrapedData(
                source=self.name,
                timestamp=datetime.utcnow(),
                data=data,
                raw_html=response.text[:1000] if len(response.text) > 0 else None,
            )
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.warning(error_msg)
            return ScrapedData(
                source=self.name,
                timestamp=datetime.utcnow(),
                data={},
                error=error_msg,
            )
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return ScrapedData(
                source=self.name,
                timestamp=datetime.utcnow(),
                data={},
                error=error_msg,
            )

    @abstractmethod
    def parse(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Parse the BeautifulSoup object to extract data.

        Args:
            soup: BeautifulSoup object of the fetched page

        Returns:
            Dictionary of parsed data
        """
        ...

    def get_fallback_data(self) -> ScrapedData:
        """Get fallback data when network fetch fails.

        Returns:
            ScrapedData object with fallback values
        """
        logger.info(f"Using fallback data for {self.name}")
        return ScrapedData(
            source=self.name,
            timestamp=datetime.utcnow(),
            data=self._generate_fallback(),
        )

    def _generate_fallback(self) -> dict[str, Any]:
        """Generate fallback data structure.

        Returns:
            Dictionary with fallback values
        """
        return {
            "status": "fallback",
            "message": "Network fetch failed, using placeholder data",
            "values": {},
        }
