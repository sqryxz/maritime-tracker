"""Scraper service layer for business logic encapsulation."""

from datetime import datetime
from typing import Any, Optional
import logging

from scrapers import FBXScraper, UNCTADScraper
from processing import DataCleaner, AnomalyDetector

logger = logging.getLogger(__name__)


class ScraperService:
    """Service class encapsulating scraper business logic."""

    def __init__(self):
        """Initialize the scraper service."""
        self._cleaner = DataCleaner()
        self._anomaly_detector = AnomalyDetector(
            z_score_threshold=2.5,
            pct_change_threshold=0.20,
            lookback_days=30,
        )

    def get_freight_rates(self) -> dict[str, Any]:
        """Fetch current freight rates (FBX routes).

        Returns:
            Dictionary containing freight rate data
        """
        logger.info("Fetching freight rates...")

        scraper = FBXScraper()
        result = scraper.fetch()

        if result.error:
            result = scraper.get_fallback_data()

        return {
            "source": "fbx",
            "timestamp": result.timestamp.isoformat() + "Z",
            "data": result.data,
            "status": "fallback" if result.error else "success",
        }

    def get_maritime_stats(self) -> dict[str, Any]:
        """Fetch UNCTAD maritime statistics.

        Returns:
            Dictionary containing maritime statistics
        """
        logger.info("Fetching maritime statistics...")

        scraper = UNCTADScraper()
        result = scraper.fetch()

        if result.error:
            result = scraper.get_fallback_data()

        return {
            "source": "unctad",
            "timestamp": result.timestamp.isoformat() + "Z",
            "data": result.data,
            "status": "fallback" if result.error else "success",
        }

    def get_anomalies(
        self,
        source: Optional[str] = None,
        min_severity: Optional[str] = None,
    ) -> dict[str, Any]:
        """Detect shipping anomalies.

        Args:
            source: Optional filter by source (fbx, unctad)
            min_severity: Optional filter by severity (low, medium, high)

        Returns:
            Dictionary containing anomaly detection results
        """
        logger.info(f"Detecting anomalies (source={source}, min_severity={min_severity})")

        # Run scrapers
        fbx_scraper = FBXScraper()
        fbx_result = fbx_scraper.fetch()
        if fbx_result.error:
            fbx_result = fbx_scraper.get_fallback_data()

        unctad_scraper = UNCTADScraper()
        unctad_result = unctad_scraper.fetch()
        if unctad_result.error:
            unctad_result = unctad_scraper.get_fallback_data()

        # Convert to dict format
        data_dicts = [
            {
                "source": fbx_result.source,
                "timestamp": fbx_result.timestamp,
                "data": fbx_result.data,
            },
            {
                "source": unctad_result.source,
                "timestamp": unctad_result.timestamp,
                "data": unctad_result.data,
            },
        ]

        # Clean and merge
        cleaned_results = [self._cleaner.clean_scraped_data(d) for d in data_dicts]
        merged = self._cleaner.merge_scraped_data(cleaned_results)

        # Detect anomalies
        anomalies = self._anomaly_detector.detect_anomalies(merged)

        # Apply filters
        filtered_anomalies = anomalies["anomalies"]

        if source:
            filtered_anomalies = [
                a for a in filtered_anomalies
                if a.get("source") == source or
                (source == "fbx" and "route" in a.get("metric", "").lower()) or
                (source == "unctad" and "indicator" in a.get("metric", "").lower())
            ]

        if min_severity:
            severity_order = {"low": 0, "medium": 1, "high": 2}
            min_level = severity_order.get(min_severity.lower(), 0)
            filtered_anomalies = [
                a for a in filtered_anomalies
                if severity_order.get(a.get("severity", "low"), 0) >= min_level
            ]

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "count": len(filtered_anomalies),
            "anomalies": filtered_anomalies,
            "summary": anomalies["summary"],
        }

    def get_full_report(self) -> dict[str, Any]:
        """Get complete data with anomalies.

        Returns:
            Dictionary containing full maritime data report
        """
        logger.info("Generating full report...")

        # Fetch freight rates
        freight_data = self.get_freight_rates()

        # Fetch maritime stats
        maritime_data = self.get_maritime_stats()

        # Run anomaly detection on combined data
        data_dicts = [
            {
                "source": freight_data["data"].get("index_name", "FBX"),
                "timestamp": freight_data["timestamp"],
                "data": {"routes": freight_data["data"].get("routes", [])},
            },
            {
                "source": maritime_data["data"].get("source", "UNCTAD"),
                "timestamp": maritime_data["timestamp"],
                "data": {"indicators": maritime_data["data"].get("indicators", [])},
            },
        ]

        cleaned_results = [self._cleaner.clean_scraped_data(d) for d in data_dicts]
        merged = self._cleaner.merge_scraped_data(cleaned_results)
        anomalies = self._anomaly_detector.detect_anomalies(merged)

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "freight_rates": freight_data,
            "maritime_stats": maritime_data,
            "anomalies": anomalies["anomalies"],
            "anomaly_summary": anomalies["summary"],
        }


# Singleton instance for use across API requests
_service: Optional[ScraperService] = None


def get_service() -> ScraperService:
    """Get or create the scraper service singleton.

    Returns:
        ScraperService instance
    """
    global _service
    if _service is None:
        _service = ScraperService()
    return _service
