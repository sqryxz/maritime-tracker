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

## REST API

A FastAPI server is available for programmatic access to maritime data.

### Running the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn api:app --reload

# Server runs on http://localhost:8000
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/freight-rates` | GET | Current freight rates (FBX routes) |
| `/anomalies` | GET | Detected shipping anomalies |
| `/maritime-stats` | GET | UNCTAD maritime statistics |
| `/full-report` | GET | Complete data with anomalies |

### Query Parameters

The `/anomalies` endpoint supports:

| Parameter | Type | Description |
|-----------|------|-------------|
| `source` | string | Filter by source (fbx, unctad) |
| `min_severity` | string | Filter by minimum severity (low, medium, high) |

### Example Usage

```bash
# Get freight rates
curl http://localhost:8000/freight-rates

# Get anomalies with minimum severity
curl "http://localhost:8000/anomalies?min_severity=medium"

# Get full report
curl http://localhost:8000/full-report

# Access Swagger docs
# http://localhost:8000/docs
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Requirements

- Python 3.11+
- No selenium/playwright - pure HTTP + parsing
- All timestamps UTC ISO 8601
