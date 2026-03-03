"""UNCTAD Maritime Statistics scraper."""

from datetime import datetime
from typing import Any
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScrapedData


class UNCTADScraper(BaseScraper):
    """Scraper for UNCTAD Maritime Statistics."""

    def __init__(
        self,
        name: str = "UNCTAD Maritime Statistics",
        source_url: str = "https://unctad.org/webflyer/review-maritime-transport-2024",
    ) -> None:
        super().__init__(name=name, source_url=source_url)

    def parse(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Parse the UNCTAD maritime statistics page.

        Args:
            soup: BeautifulSoup object of the UNCTAD page

        Returns:
            Dictionary with maritime statistics
        """
        data: dict[str, Any] = {
            "source": "UNCTAD Maritime Statistics",
            "indicators": [],
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        # Extract tables with maritime data
        tables = soup.find_all("table")
        for table in tables:
            headers = table.find_all("th")
            header_texts = [h.get_text(strip=True) for h in headers]

            # Look for relevant maritime indicators
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    indicator = cells[0].get_text(strip=True)
                    try:
                        # Try to extract numeric value
                        value_text = cells[1].get_text(strip=True).replace(",", "")
                        value = float(value_text)
                        data["indicators"].append({
                            "name": indicator,
                            "value": value,
                        })
                    except ValueError:
                        # Skip non-numeric rows
                        continue

        # Extract any key statistics from the page
        stats_cards = soup.find_all(["div", "span"], class_=lambda x: x and ("stat" in x.lower() or "number" in x.lower()) if x else False)

        for card in stats_cards[:5]:
            text = card.get_text(strip=True)
            import re
            # Look for numbers with units
            numbers = re.findall(r"([\d,]+(?:\.\d+)?)\s*(million|billion|thousand|%)?", text, re.IGNORECASE)
            for num_match in numbers:
                try:
                    num_str = num_match[0].replace(",", "")
                    value = float(num_str)
                    unit = num_match[1] if len(num_match) > 1 else ""
                    data["indicators"].append({
                        "name": "Extracted statistic",
                        "value": value,
                        "unit": unit,
                    })
                except ValueError:
                    continue

        # If no structured data found, return sample data
        if not data["indicators"]:
            data["indicators"] = self._get_sample_indicators()
            data["note"] = "Using sample data - source page structure may have changed"

        return data

    def _get_sample_indicators(self) -> list[dict[str, Any]]:
        """Return sample maritime indicators for fallback.

        Returns:
            List of sample indicator dictionaries
        """
        return [
            {"name": "World Fleet tonnage (million GT)", "value": 2200.0, "unit": "million GT"},
            {"name": "Maritime trade volume", "value": 24000.0, "unit": "million tons"},
            {"name": "Container port throughput", "value": 900.0, "unit": "million TEU"},
            {"name": "Merchant fleet registrations", "value": 150.0, "unit": "countries"},
            {"name": "Shipping share of world trade", "value": 80.0, "unit": "percent"},
        ]

    def _generate_fallback(self) -> dict[str, Any]:
        """Generate fallback UNCTAD data.

        Returns:
            Dictionary with fallback maritime statistics
        """
        return {
            "status": "fallback",
            "source": "UNCTAD Maritime Statistics",
            "indicators": self._get_sample_indicators(),
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "message": "Network fetch failed, using placeholder data",
        }
