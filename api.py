"""FastAPI REST API for Maritime Data Scraper."""

from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from scraper_service import get_service

app = FastAPI(
    title="Maritime Data Scraper API",
    description="REST API for querying shipping anomalies and freight rates",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "maritime-scraper-api",
    }


@app.get("/freight-rates")
async def get_freight_rates():
    """Get current freight rates (FBX routes).

    Returns:
        Freight rate data
    """
    service = get_service()
    return service.get_freight_rates()


@app.get("/anomalies")
async def get_anomalies(
    source: Optional[str] = Query(
        None,
        description="Filter by source (fbx, unctad)",
    ),
    min_severity: Optional[str] = Query(
        None,
        description="Filter anomalies by severity (low, medium, high)",
    ),
):
    """Get detected shipping anomalies.

    Args:
        source: Optional filter by source
        min_severity: Optional filter by minimum severity

    Returns:
        Anomaly detection results
    """
    service = get_service()
    return service.get_anomalies(source=source, min_severity=min_severity)


@app.get("/maritime-stats")
async def get_maritime_stats():
    """Get UNCTAD maritime statistics.

    Returns:
        Maritime statistics data
    """
    service = get_service()
    return service.get_maritime_stats()


@app.get("/full-report")
async def get_full_report():
    """Get complete data with anomalies.

    Returns:
        Full maritime data report
    """
    service = get_service()
    return service.get_full_report()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
