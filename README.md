# Maritime Alternative Data Scraper

Python module for scraping public maritime shipping data, detecting anomalies, and outputting standardized JSON payloads. Feeds into the Post Fiat Alpha Registry for macro supply chain hypothesis testing.

## Features

- **Multiple Data Sources**: Freightos Baltic Index (FBX), UNCTAD Maritime Statistics
- **Anomaly Detection**: Z-score, percentage change, and cross-route analysis
- **Fallback Handling**: Produces valid output even on network failure
- **Type Safety**: Full type hints on all functions
- **Logging**: Standard library logging

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

Output will be saved to `output/maritime_data_{timestamp}.json`

## Configuration

Edit `config.yaml` to:
- Enable/disable specific scrapers
- Adjust anomaly detection thresholds
- Configure output format

## Testing

```bash
python -m pytest tests/ -v
```

## Project Structure

```
maritime_scraper/
├── scrapers/          # Data source scrapers
├── processing/       # Data cleaning & anomaly detection
├── output/           # JSON output files
├── tests/            # Unit tests
├── config.yaml       # Configuration
└── main.py           # Entry point
```

## Requirements

- Python 3.11+
- No selenium/playwright - pure HTTP + parsing
- All timestamps UTC ISO 8601
