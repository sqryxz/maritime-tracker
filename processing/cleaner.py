"""Data cleaning and normalization."""

from datetime import datetime
from typing import Any
import logging


logger = logging.getLogger(__name__)


class DataCleaner:
    """Handles data cleaning and normalization."""

    @staticmethod
    def clean_scraped_data(data: dict[str, Any]) -> dict[str, Any]:
        """Clean and normalize scraped data.

        Args:
            data: Raw scraped data dictionary

        Returns:
            Cleaned data dictionary
        """
        cleaned: dict[str, Any] = {
            "source": data.get("source", "unknown"),
            "timestamp": DataCleaner._normalize_timestamp(data.get("timestamp")),
            "data": {},
            "metadata": {
                "cleaned_at": datetime.utcnow().isoformat() + "Z",
                "original_keys": list(data.keys()),
            },
        }

        # Process the nested data based on source
        if "routes" in data:
            cleaned["data"]["routes"] = DataCleaner._clean_routes(data["routes"])
        elif "indicators" in data:
            cleaned["data"]["indicators"] = DataCleaner._clean_indicators(data["indicators"])
        elif "vessels" in data:
            cleaned["data"]["vessels"] = data["vessels"]
        else:
            cleaned["data"] = data.get("data", {})

        # Preserve status information
        if "status" in data:
            cleaned["status"] = data["status"]

        return cleaned

    @staticmethod
    def _clean_routes(routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Clean route data.

        Args:
            routes: List of route dictionaries

        Returns:
            Cleaned list of routes
        """
        cleaned_routes = []
        for route in routes:
            cleaned_route = {
                "route": str(route.get("route", "")).strip(),
                "value": DataCleaner._to_float(route.get("value")),
                "unit": str(route.get("unit", "USD/FEU")).strip(),
            }
            if cleaned_route["value"] is not None:
                cleaned_routes.append(cleaned_route)
        return cleaned_routes

    @staticmethod
    def _clean_indicators(indicators: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Clean indicator data.

        Args:
            indicators: List of indicator dictionaries

        Returns:
            Cleaned list of indicators
        """
        cleaned_indicators = []
        for indicator in indicators:
            cleaned_indicator = {
                "name": str(indicator.get("name", "")).strip(),
                "value": DataCleaner._to_float(indicator.get("value")),
            }
            if "unit" in indicator:
                cleaned_indicator["unit"] = str(indicator.get("unit", "")).strip()
            if cleaned_indicator["value"] is not None:
                cleaned_indicators.append(cleaned_indicator)
        return cleaned_indicators

    @staticmethod
    def _to_float(value: Any) -> float | None:
        """Convert value to float.

        Args:
            value: Value to convert

        Returns:
            Float value or None if conversion fails
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace(",", "").replace("$", "").strip())
            except ValueError:
                return None
        return None

    @staticmethod
    def _normalize_timestamp(timestamp: Any) -> str:
        """Normalize timestamp to ISO 8601 format.

        Args:
            timestamp: Timestamp to normalize

        Returns:
            ISO 8601 formatted timestamp string
        """
        if isinstance(timestamp, datetime):
            return timestamp.isoformat() + "Z"
        if isinstance(timestamp, str):
            return timestamp
        return datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def merge_scraped_data(results: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge multiple scraped data results into a single payload.

        Args:
            results: List of cleaned data dictionaries

        Returns:
            Merged data dictionary
        """
        merged: dict[str, Any] = {
            "collection_timestamp": datetime.utcnow().isoformat() + "Z",
            "sources": [],
            "data": {},
            "summary": {
                "total_sources": len(results),
                "successful": sum(1 for r in results if r.get("status") != "error"),
                "failed": sum(1 for r in results if r.get("status") == "error" or r.get("error")),
            },
        }

        for result in results:
            source_name = result.get("source", "unknown")
            merged["sources"].append(source_name)

            # Merge based on data type
            if "routes" in result.get("data", {}):
                if "routes" not in merged["data"]:
                    merged["data"]["routes"] = []
                merged["data"]["routes"].extend(result["data"]["routes"])

            if "indicators" in result.get("data", {}):
                if "indicators" not in merged["data"]:
                    merged["data"]["indicators"] = []
                merged["data"]["indicators"].extend(result["data"]["indicators"])

            if "vessels" in result.get("data", {}):
                if "vessels" not in merged["data"]:
                    merged["data"]["vessels"] = []
                merged["data"]["vessels"].extend(result["data"]["vessels"])

        logger.info(f"Merged data from {len(results)} sources")
        return merged
