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

## Sample API Responses

### Freight Rates Endpoint (`/freight-rates`)

```json
{
  "source": "fbx",
  "timestamp": "2026-03-04T12:00:00Z",
  "data": {
    "index_name": "Freightos Baltic Index (FBX)",
    "routes": [
      {"route": "China to US West Coast", "value": 2500.0, "unit": "USD/FEU"},
      {"route": "China to US East Coast", "value": 3500.0, "unit": "USD/FEU"},
      {"route": "China to Rotterdam", "value": 1800.0, "unit": "USD/FEU"}
    ]
  },
  "status": "success"
}
```

### Anomalies Endpoint (`/anomalies`)

```json
{
  "timestamp": "2026-03-04T12:00:00Z",
  "count": 2,
  "anomalies": [
    {
      "type": "z_score",
      "metric": "Shanghai to New York",
      "value": 3600.0,
      "z_score": 2.61,
      "severity": "medium",
      "threshold": 2.5,
      "details": {"mean": 2960.0, "std": 245.36}
    },
    {
      "type": "pct_change",
      "metric": "China to Rotterdam",
      "value": 2200.0,
      "pct_change": 22.2,
      "severity": "medium",
      "threshold": 20.0,
      "details": {"previous_value": 1800.0, "change": 400.0}
    }
  ],
  "summary": {
    "total_anomalies": 2,
    "z_score_anomalies": 1,
    "pct_change_anomalies": 1,
    "cross_route_anomalies": 0
  }
}
```

### Full Report Endpoint (`/full-report`)

```json
{
  "timestamp": "2026-03-04T12:00:00Z",
  "freight_rates": {
    "source": "fbx",
    "timestamp": "2026-03-04T12:00:00Z",
    "data": {"routes": [...]},
    "status": "success"
  },
  "maritime_stats": {
    "source": "unctad",
    "timestamp": "2026-03-04T12:00:00Z",
    "data": {
      "indicators": [
        {"name": "World Fleet tonnage (million GT)", "value": 2200.0},
        {"name": "Container port throughput", "value": 900.0, "unit": "million TEU"}
      ]
    },
    "status": "success"
  },
  "anomalies": [...],
  "anomaly_summary": {"total_anomalies": 1, ...}
}
```

See `sample_output.json` for a complete example with all fields.

## Requirements

- Python 3.11+
- No selenium/playwright - pure HTTP + parsing
- All timestamps UTC ISO 8601
