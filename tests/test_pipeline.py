"""Unit tests for the maritime scraper pipeline."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from scrapers.base import BaseScraper, ScrapedData
from scrapers.fbx_scraper import FBXScraper
from scrapers.unctad_scraper import UNCTADScraper
from scrapers.ais_scraper import AISScraper
from processing.cleaner import DataCleaner
from processing.anomaly import AnomalyDetector


class TestBaseScraper:
    """Tests for the BaseScraper class."""

    def test_scraper_initialization(self):
        """Test scraper initializes correctly."""
        scraper = FBXScraper(
            name="Test Scraper",
            source_url="https://example.com",
        )
        assert scraper.name == "Test Scraper"
        assert scraper.source_url == "https://example.com"
        assert scraper.timeout == 30

    def test_fallback_data_generation(self):
        """Test fallback data is generated correctly."""
        scraper = FBXScraper(
            name="Test",
            source_url="https://example.com",
        )
        fallback = scraper.get_fallback_data()
        assert fallback.source == "Test"
        assert fallback.timestamp is not None
        assert "status" in fallback.data
        assert fallback.data["status"] == "fallback"


class TestFBXScraper:
    """Tests for the FBX scraper."""

    def test_fbx_scraper_initialization(self):
        """Test FBX scraper initializes with correct defaults."""
        scraper = FBXScraper()
        assert scraper.name == "Freightos Baltic Index"
        assert "freightos" in scraper.source_url.lower()

    def test_fbx_sample_routes(self):
        """Test sample routes are generated."""
        scraper = FBXScraper()
        routes = scraper._get_sample_routes()
        assert len(routes) > 0
        assert all("route" in r and "value" in r for r in routes)

    def test_fbx_fallback_data(self):
        """Test fallback data structure."""
        scraper = FBXScraper()
        fallback = scraper.get_fallback_data()
        assert "routes" in fallback.data
        assert fallback.data["status"] == "fallback"


class TestUNCTADScraper:
    """Tests for the UNCTAD scraper."""

    def test_unctad_scraper_initialization(self):
        """Test UNCTAD scraper initializes correctly."""
        scraper = UNCTADScraper()
        assert scraper.name == "UNCTAD Maritime Statistics"

    def test_unctad_sample_indicators(self):
        """Test sample indicators are generated."""
        scraper = UNCTADScraper()
        indicators = scraper._get_sample_indicators()
        assert len(indicators) > 0
        assert all("name" in i and "value" in i for i in indicators)


class TestAISScraper:
    """Tests for the AIS scraper."""

    def test_ais_scraper_is_placeholder(self):
        """Test AIS scraper is a placeholder."""
        scraper = AISScraper()
        fallback = scraper.get_fallback_data()
        assert fallback.data["status"] == "fallback"
        assert "placeholder" in fallback.data["message"].lower()


class TestDataCleaner:
    """Tests for the DataCleaner class."""

    def test_clean_routes(self):
        """Test route cleaning."""
        routes = [
            {"route": "Route A", "value": "1000", "unit": "USD"},
            {"route": "Route B", "value": 2000, "unit": "USD"},
        ]
        cleaned = DataCleaner._clean_routes(routes)
        assert len(cleaned) == 2
        assert cleaned[0]["value"] == 1000.0
        assert cleaned[1]["value"] == 2000.0

    def test_clean_indicators(self):
        """Test indicator cleaning."""
        indicators = [
            {"name": "Indicator 1", "value": "500"},
            {"name": "Indicator 2", "value": 600, "unit": "million"},
        ]
        cleaned = DataCleaner._clean_indicators(indicators)
        assert len(cleaned) == 2
        assert cleaned[0]["value"] == 500.0
        assert cleaned[1]["value"] == 600.0

    def test_to_float_conversion(self):
        """Test float conversion."""
        assert DataCleaner._to_float("1,000") == 1000.0
        assert DataCleaner._to_float("$500") == 500.0
        assert DataCleaner._to_float(42) == 42.0
        assert DataCleaner._to_float(None) is None
        assert DataCleaner._to_float("invalid") is None

    def test_merge_scraped_data(self):
        """Test merging multiple data sources."""
        results = [
            {
                "source": "FBX",
                "data": {"routes": [{"route": "R1", "value": 100}]},
            },
            {
                "source": "UNCTAD",
                "data": {"indicators": [{"name": "I1", "value": 50}]},
            },
        ]
        merged = DataCleaner.merge_scraped_data(results)
        assert merged["summary"]["total_sources"] == 2
        assert len(merged["data"]["routes"]) == 1
        assert len(merged["data"]["indicators"]) == 1


class TestAnomalyDetector:
    """Tests for the AnomalyDetector class."""

    def test_detector_initialization(self):
        """Test detector initializes with correct defaults."""
        detector = AnomalyDetector()
        assert detector.z_score_threshold == 2.5
        assert detector.pct_change_threshold == 0.20
        assert detector.lookback_days == 30

    def test_z_score_detection(self):
        """Test z-score anomaly detection."""
        detector = AnomalyDetector(z_score_threshold=1.4)  # Lower threshold for test
        route_values = {
            "Route A": 100.0,
            "Route B": 100.0,
            "Route C": 500.0,  # Should be flagged as anomaly
        }
        anomalies = detector._z_score_detection(route_values)
        assert len(anomalies) > 0
        assert anomalies[0]["type"] == "z_score"

    def test_z_score_no_anomaly(self):
        """Test z-score detection with normal data."""
        detector = AnomalyDetector(z_score_threshold=2.0)
        route_values = {
            "Route A": 100.0,
            "Route B": 102.0,
            "Route C": 98.0,
        }
        anomalies = detector._z_score_detection(route_values)
        assert len(anomalies) == 0

    def test_cross_route_detection(self):
        """Test cross-route anomaly detection."""
        detector = AnomalyDetector()
        routes = [
            {"route": "China to US", "value": 1000.0},
            {"route": "China to EU", "value": 5000.0},  # High spread
        ]
        anomalies = detector._cross_route_detection(routes)
        # Should detect high spread anomaly
        assert len(anomalies) > 0

    def test_detect_anomalies_empty_data(self):
        """Test anomaly detection with empty data."""
        detector = AnomalyDetector()
        result = detector.detect_anomalies({"data": {}})
        assert result["summary"]["total_anomalies"] == 0

    def test_detect_anomalies_with_routes(self):
        """Test anomaly detection with route data."""
        detector = AnomalyDetector()
        data = {
            "data": {
                "routes": [
                    {"route": "China to US", "value": 1000.0},
                    {"route": "China to EU", "value": 1500.0},
                    {"route": "China to UK", "value": 5000.0},  # Anomaly
                ]
            }
        }
        result = detector.detect_anomalies(data)
        assert "anomalies" in result
        assert "summary" in result


class TestPipeline:
    """Integration tests for the full pipeline."""

    def test_full_pipeline_with_mock(self):
        """Test the full pipeline with mocked responses."""
        # Create scrapers
        fbx_scraper = FBXScraper()
        unctad_scraper = UNCTADScraper()

        # Get fallback data (since we can't actually fetch)
        fbx_data = fbx_scraper.get_fallback_data()
        unctad_data = unctad_scraper.get_fallback_data()

        # Clean the data
        cleaner = DataCleaner()
        fbx_cleaned = cleaner.clean_scraped_data(fbx_data.data)
        unctad_cleaned = cleaner.clean_scraped_data(unctad_data.data)

        # Merge data
        merged = cleaner.merge_scraped_data([fbx_cleaned, unctad_cleaned])

        # Detect anomalies
        detector = AnomalyDetector()
        anomalies = detector.detect_anomalies(merged)

        # Verify output structure
        assert "collection_timestamp" in merged
        assert "data" in merged
        assert "detection_timestamp" in anomalies
        assert "summary" in anomalies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
