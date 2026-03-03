#!/usr/bin/env python3
"""
Maritime Alternative Data Scraper

Scrapes public maritime shipping data, detects anomalies,
and outputs standardized JSON payloads.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from scrapers import FBXScraper, UNCTADScraper, AISScraper
from processing import DataCleaner, AnomalyDetector


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    config_file = Path(__file__).parent / config_path
    if config_file.exists():
        with open(config_file, "r") as f:
            return yaml.safe_load(f)
    return {}


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration.

    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def run_scrapers(config: dict) -> list:
    """Run enabled scrapers based on configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of scraped data results
    """
    logger = logging.getLogger(__name__)
    results = []

    scraper_configs = config.get("scrapers", {})

    # FBX Scraper
    if scraper_configs.get("fbx", {}).get("enabled", True):
        logger.info("Running FBX scraper...")
        scraper = FBXScraper()
        result = scraper.fetch()
        if result.error:
            if config.get("fallback", {}).get("use_fallback_on_failure", True):
                result = scraper.get_fallback_data()
            else:
                logger.warning(f"FBX scraper error: {result.error}")
        results.append(result)

    # UNCTAD Scraper
    if scraper_configs.get("unctad", {}).get("enabled", True):
        logger.info("Running UNCTAD scraper...")
        scraper = UNCTADScraper()
        result = scraper.fetch()
        if result.error:
            if config.get("fallback", {}).get("use_fallback_on_failure", True):
                result = scraper.get_fallback_data()
            else:
                logger.warning(f"UNCTAD scraper error: {result.error}")
        results.append(result)

    # AIS Scraper (disabled by default)
    if scraper_configs.get("ais", {}).get("enabled", False):
        logger.info("Running AIS scraper...")
        scraper = AISScraper()
        result = scraper.fetch()
        if result.error:
            if config.get("fallback", {}).get("use_fallback_on_failure", True):
                result = scraper.get_fallback_data()
        results.append(result)

    return results


def process_data(scraped_results: list, config: dict) -> dict:
    """Process scraped data through cleaning and anomaly detection.

    Args:
        scraped_results: List of scraped data
        config: Configuration dictionary

    Returns:
        Processed data dictionary
    """
    logger = logging.getLogger(__name__)
    logger.info("Processing scraped data...")

    # Convert ScrapedData to dict format
    data_dicts = []
    for result in scraped_results:
        data_dict = {
            "source": result.source,
            "timestamp": result.timestamp,
            "data": result.data,
        }
        if result.error:
            data_dict["error"] = result.error
        data_dicts.append(data_dict)

    # Clean the data
    cleaner = DataCleaner()
    cleaned_results = [cleaner.clean_scraped_data(d) for d in data_dicts]

    # Merge data
    merged = cleaner.merge_scraped_data(cleaned_results)

    # Detect anomalies
    anomaly_config = config.get("anomaly_detection", {})
    detector = AnomalyDetector(
        z_score_threshold=anomaly_config.get("z_score_threshold", 2.5),
        pct_change_threshold=anomaly_config.get("pct_change_threshold", 0.20),
        lookback_days=anomaly_config.get("lookback_days", 30),
    )
    anomalies = detector.detect_anomalies(merged)

    # Add anomalies to final output
    merged["anomalies"] = anomalies["anomalies"]
    merged["anomaly_summary"] = anomalies["summary"]

    logger.info(f"Processing complete. Found {anomalies['summary']['total_anomalies']} anomalies")
    return merged


def save_output(data: dict, config: dict) -> Path:
    """Save processed data to JSON file.

    Args:
        data: Processed data dictionary
        config: Configuration dictionary

    Returns:
        Path to output file
    """
    logger = logging.getLogger(__name__)

    output_config = config.get("output", {})
    output_dir = Path(__file__).parent / output_config.get("directory", "output")
    output_dir.mkdir(exist_ok=True)

    # Generate filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    pattern = output_config.get("filename_pattern", "maritime_data_{timestamp}.json")
    filename = pattern.format(timestamp=timestamp)
    output_path = output_dir / filename

    # Write file
    pretty_print = output_config.get("pretty_print", True)
    with open(output_path, "w") as f:
        if pretty_print:
            json.dump(data, f, indent=2)
        else:
            json.dump(data, f)

    logger.info(f"Output saved to {output_path}")
    return output_path


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Load configuration
    config = load_config()

    # Setup logging
    log_level = config.get("logging", {}).get("level", "INFO")
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    logger.info("Starting Maritime Alternative Data Scraper")

    try:
        # Run scrapers
        scraped_results = run_scrapers(config)

        if not scraped_results:
            logger.error("No data scraped")
            return 1

        # Process data
        processed_data = process_data(scraped_results, config)

        # Save output
        output_path = save_output(processed_data, config)

        logger.info(f"Pipeline complete. Output: {output_path}")
        return 0

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
