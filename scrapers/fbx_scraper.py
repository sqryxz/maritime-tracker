"""Freightos Baltic Index (FBX) scraper."""

from datetime import datetime
from typing import Any
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScrapedData


class FBXScraper(BaseScraper):
    """Scraper for Freightos Baltic Index data."""

    def __init__(
        self,
        name: str = "Freightos Baltic Index",
        source_url: str = "https://freightos.com/freight-index/baltic-index",
    ) -> None:
        super().__init__(name=name, source_url=source_url)

    def parse(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Parse the FBX index page.

        Args:
            soup: BeautifulSoup object of the FBX page

        Returns:
            Dictionary with FBX index data
        """
        data: dict[str, Any] = {
            "index_name": "Freightos Baltic Index (FBX)",
            "routes": [],
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        # Try to extract index values from the page
        # FBX is a container index, so we look for various route indices
        index_elements = soup.find_all(["table", "div"], class_=lambda x: x and "index" in x.lower() if x else False)

        # Extract data from tables if present
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    route_name = cells[0].get_text(strip=True)
                    try:
                        value = float(cells[1].get_text(strip=True).replace(",", ""))
                        if route_name and value:
                            data["routes"].append({
                                "route": route_name,
                                "value": value,
                                "unit": "USD/FEU",
                            })
                    except ValueError:
                        continue

        # If no structured data found, try to extract any numeric patterns
        if not data["routes"]:
            page_text = soup.get_text()
            import re
            # Look for patterns like FBX: $X,XXX
            fbx_patterns = re.findall(r"(?:FBX|Freightos Baltic).*?\$?([\d,]+(?:\.\d+)?)", page_text, re.IGNORECASE)
            for i, match in enumerate(fbx_patterns[:10]):
                try:
                    value = float(match.replace(",", ""))
                    data["routes"].append({
                        "route": f"Route_{i+1}",
                        "value": value,
                        "unit": "USD/FEU",
                    })
                except ValueError:
                    continue

        # If still no data, return placeholder
        if not data["routes"]:
            data["routes"] = self._get_sample_routes()
            data["note"] = "Using sample data - source page structure may have changed"

        return data

    def _get_sample_routes(self) -> list[dict[str, Any]]:
        """Return sample route data for fallback when parsing fails.

        Returns:
            List of sample route dictionaries
        """
        return [
            {"route": "China to US West Coast", "value": 2500.0, "unit": "USD/FEU"},
            {"route": "China to US East Coast", "value": 3500.0, "unit": "USD/FEU"},
            {"route": "China to Rotterdam", "value": 1800.0, "unit": "USD/FEU"},
            {"route": "Shanghai to Los Angeles", "value": 2400.0, "unit": "USD/FEU"},
            {"route": "Shanghai to New York", "value": 3600.0, "unit": "USD/FEU"},
        ]

    def _generate_fallback(self) -> dict[str, Any]:
        """Generate fallback FBX data.

        Returns:
            Dictionary with fallback FBX values
        """
        return {
            "status": "fallback",
            "index_name": "Freightos Baltic Index (FBX)",
            "routes": self._get_sample_routes(),
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "message": "Network fetch failed, using placeholder data",
        }
