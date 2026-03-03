"""AIS (Automatic Identification System) data scraper - placeholder."""

from datetime import datetime
from typing import Any
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScrapedData


class AISScraper(BaseScraper):
    """Scraper for AIS vessel tracking data.

    Note: This is a placeholder implementation. Real AIS data typically
    requires API access or specialized receivers. This scraper simulates
    the data structure for testing purposes.
    """

    def __init__(
        self,
        name: str = "AIS Data",
        source_url: str = "",
    ) -> None:
        super().__init__(name=name, source_url=source_url)

    def parse(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Parse AIS data (placeholder).

        Args:
            soup: BeautifulSoup object (not used for placeholder)

        Returns:
            Dictionary with placeholder AIS data structure
        """
        data: dict[str, Any] = {
            "source": "AIS Data",
            "status": "placeholder",
            "message": "AIS scraper is disabled by default - requires API access",
            "vessels": [],
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        # This is a placeholder - real implementation would need:
        # - MarineTraffic API or similar
        # - VesselFinder API
        # - Custom AIS receiver

        return data

    def _generate_fallback(self) -> dict[str, Any]:
        """Generate placeholder AIS data.

        Returns:
            Dictionary with placeholder AIS structure
        """
        return {
            "status": "fallback",
            "source": "AIS Data",
            "message": "AIS scraper is disabled - using placeholder",
            "vessels": [],
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }
