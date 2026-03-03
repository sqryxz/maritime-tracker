"""Anomaly detection for maritime shipping data."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
import logging
import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Container for anomaly detection results."""

    metric: str
    value: float
    anomaly_type: str
    severity: str
    details: dict[str, Any]


class AnomalyDetector:
    """Detects anomalies in maritime shipping data."""

    def __init__(
        self,
        z_score_threshold: float = 2.5,
        pct_change_threshold: float = 0.20,
        lookback_days: int = 30,
    ) -> None:
        """Initialize the anomaly detector.

        Args:
            z_score_threshold: Z-score threshold for outlier detection
            pct_change_threshold: Percentage change threshold for spike detection
            lookback_days: Number of days for historical comparison
        """
        self.z_score_threshold = z_score_threshold
        self.pct_change_threshold = pct_change_threshold
        self.lookback_days = lookback_days

        # In-memory storage for historical data (in production, use a database)
        self._history: dict[str, list[tuple[datetime, float]]] = {}

    def detect_anomalies(self, data: dict[str, Any]) -> dict[str, Any]:
        """Detect anomalies in the scraped data.

        Args:
            data: Cleaned and merged data dictionary

        Returns:
            Dictionary with anomaly detection results
        """
        result: dict[str, Any] = {
            "detection_timestamp": datetime.utcnow().isoformat() + "Z",
            "anomalies": [],
            "summary": {
                "total_anomalies": 0,
                "z_score_anomalies": 0,
                "pct_change_anomalies": 0,
                "cross_route_anomalies": 0,
            },
        }

        # Detect anomalies in routes (FBX data)
        routes = data.get("data", {}).get("routes", [])
        if routes:
            route_anomalies = self._detect_route_anomalies(routes)
            result["anomalies"].extend(route_anomalies)
            result["summary"]["z_score_anomalies"] = len([a for a in route_anomalies if a["type"] == "z_score"])
            result["summary"]["pct_change_anomalies"] = len([a for a in route_anomalies if a["type"] == "pct_change"])
            result["summary"]["cross_route_anomalies"] = len([a for a in route_anomalies if a["type"] == "cross_route"])

        # Detect anomalies in indicators (UNCTAD data)
        indicators = data.get("data", {}).get("indicators", [])
        if indicators:
            indicator_anomalies = self._detect_indicator_anomalies(indicators)
            result["anomalies"].extend(indicator_anomalies)

        result["summary"]["total_anomalies"] = len(result["anomalies"])

        logger.info(f"Detected {result['summary']['total_anomalies']} anomalies")
        return result

    def _detect_route_anomalies(self, routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect anomalies in route data.

        Args:
            routes: List of route dictionaries

        Returns:
            List of detected anomalies
        """
        anomalies = []

        if not routes or len(routes) < 2:
            return anomalies

        # Extract values for analysis
        route_values = {r["route"]: r["value"] for r in routes if "value" in r}
        values = list(route_values.values())

        # Z-score anomaly detection
        z_score_anomalies = self._z_score_detection(route_values)
        anomalies.extend(z_score_anomalies)

        # Percentage change detection (vs historical)
        pct_anomalies = self._pct_change_detection(route_values)
        anomalies.extend(pct_anomalies)

        # Cross-route anomaly detection
        cross_anomalies = self._cross_route_detection(routes)
        anomalies.extend(cross_anomalies)

        return anomalies

    def _z_score_detection(self, route_values: dict[str, float]) -> list[dict[str, Any]]:
        """Detect anomalies using z-score method.

        Args:
            route_values: Dictionary of route names to values

        Returns:
            List of z-score anomalies
        """
        anomalies = []
        values = list(route_values.values())

        if len(values) < 3:
            return anomalies

        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return anomalies

        for route, value in route_values.items():
            z_score = (value - mean) / std

            if abs(z_score) > self.z_score_threshold:
                severity = "high" if abs(z_score) > 3.0 else "medium"
                anomalies.append({
                    "type": "z_score",
                    "metric": route,
                    "value": value,
                    "z_score": round(z_score, 2),
                    "severity": severity,
                    "threshold": self.z_score_threshold,
                    "details": {
                        "mean": round(mean, 2),
                        "std": round(std, 2),
                    },
                })

        return anomalies

    def _pct_change_detection(self, route_values: dict[str, float]) -> list[dict[str, Any]]:
        """Detect anomalies using percentage change from historical data.

        Args:
            route_values: Dictionary of route names to values

        Returns:
            List of percentage change anomalies
        """
        anomalies = []
        now = datetime.utcnow()

        for route, value in route_values.items():
            history_key = f"route_{route}"

            # Get historical values for this route
            history = self._history.get(history_key, [])

            if history:
                # Compare against most recent historical value
                last_value = history[-1][1]
                if last_value > 0:
                    pct_change = (value - last_value) / last_value

                    if abs(pct_change) > self.pct_change_threshold:
                        severity = "high" if abs(pct_change) > 0.5 else "medium"
                        anomalies.append({
                            "type": "pct_change",
                            "metric": route,
                            "value": value,
                            "pct_change": round(pct_change * 100, 2),
                            "severity": severity,
                            "threshold": self.pct_change_threshold * 100,
                            "details": {
                                "previous_value": last_value,
                                "change": round(value - last_value, 2),
                            },
                        })

            # Update history
            if history_key not in self._history:
                self._history[history_key] = []
            self._history[history_key].append((now, value))

            # Keep only recent history
            cutoff = now - timedelta(days=self.lookback_days)
            self._history[history_key] = [
                (t, v) for t, v in self._history[history_key]
                if t > cutoff
            ]

        return anomalies

    def _cross_route_detection(self, routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect anomalies by comparing related routes.

        Args:
            routes: List of route dictionaries

        Returns:
            List of cross-route anomalies
        """
        anomalies = []

        if len(routes) < 2:
            return anomalies

        # Group routes by common origin/destination
        route_groups: dict[str, list[dict[str, Any]]] = {}

        for route in routes:
            route_name = route.get("route", "")
            # Simple heuristic: group by first word (e.g., "China", "Europe")
            parts = route_name.split(" to ")
            if len(parts) == 2:
                origin = parts[0].strip()
                if origin not in route_groups:
                    route_groups[origin] = []
                route_groups[origin].append(route)

        # Check for anomalies within groups
        for origin, group_routes in route_groups.items():
            if len(group_routes) < 2:
                continue

            values = [r["value"] for r in group_routes if "value" in r]
            if len(values) < 2:
                continue

            mean = np.mean(values)
            max_val = max(values)
            min_val = min(values)

            if mean > 0:
                spread_ratio = (max_val - min_val) / mean

                # If spread is very high relative to mean, flag it
                if spread_ratio > 1.0:
                    for route in group_routes:
                        if route["value"] == max_val:
                            anomalies.append({
                                "type": "cross_route",
                                "metric": route["route"],
                                "value": route["value"],
                                "severity": "medium",
                                "details": {
                                    "origin": origin,
                                    "min_value": min_val,
                                    "max_value": max_val,
                                    "spread_ratio": round(spread_ratio, 2),
                                    "note": "High spread within route group",
                                },
                            })

        return anomalies

    def _detect_indicator_anomalies(self, indicators: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect anomalies in indicator data.

        Args:
            indicators: List of indicator dictionaries

        Returns:
            List of detected anomalies
        """
        # For now, use simplified z-score detection for indicators
        return self._z_score_detection({ind["name"]: ind["value"] for ind in indicators if "value" in ind})

    def get_history(self) -> dict[str, list[tuple[datetime, float]]]:
        """Get the historical data stored in the detector.

        Returns:
            Dictionary of historical values
        """
        return self._history.copy()
