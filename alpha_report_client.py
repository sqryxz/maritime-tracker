"""Alpha Alert Client - Synthesize maritime data into Alpha Reports via MCP.

This script demonstrates AI agents consuming maritime data through MCP.
It queries the MCP server for maritime data and uses OpenAI to synthesize
an Alpha Alert report in markdown format.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI


# Configuration
OUTPUT_DIR = Path(__file__).parent / "output"
MCP_SERVER_PATH = Path(__file__).parent / "mcp_server.py"
ALERT_TIMESTAMP = datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def get_openai_client() -> Optional[OpenAI]:
    """Initialize OpenAI client from environment variable."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("WARNING: OPENAI_API_KEY not set. Using template-based report generation.")
        return None
    return OpenAI(api_key=api_key)


async def run_mcp_query(tool_name: str, arguments: dict = None) -> dict[str, Any]:
    """Run a query against the MCP server using stdio transport.

    Args:
        tool_name: Name of the MCP tool to call
        arguments: Optional arguments for the tool

    Returns:
        Response from MCP server as dictionary
    """
    # MCP JSON-RPC requests
    request_id = 1

    # Initialize request (required by MCP protocol)
    initialize_request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "alpha-report-client",
                "version": "1.0.0"
            }
        }
    }

    # Call the tool
    call_tool_request = {
        "jsonrpc": "2.0",
        "id": request_id + 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {}
        }
    }

    # Use the MCP CLI or direct Python execution
    # Since MCP uses stdio, we'll use subprocess
    import subprocess

    # Run MCP server and communicate via stdin/stdout
    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(MCP_SERVER_PATH.parent)
    )

    # Send initialize request first
    init_json = json.dumps(initialize_request) + "\n"
    tool_json = json.dumps(call_tool_request) + "\n"

    # Send both requests
    stdout, stderr = proc.communicate(input=init_json + tool_json, timeout=30)

    if stderr and "WARNING" not in stderr:
        print(f"MCP Server stderr: {stderr}")

    proc.wait()

    # Parse response - look for tool call result
    try:
        # The response should be JSON-RPC messages (possibly multiple lines)
        for line in stdout.strip().split("\n"):
            if line.strip():
                try:
                    response = json.loads(line)
                    if "result" in response:
                        result_data = response["result"]
                        # Check if this is a tool call result (has content)
                        if isinstance(result_data, dict) and "content" in result_data:
                            # Extract text from content array
                            for content in result_data["content"]:
                                if content.get("type") == "text":
                                    return json.loads(content["text"])
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return {"error": "Failed to parse MCP response", "raw": stdout}


async def fetch_maritime_data() -> dict[str, Any]:
    """Fetch all maritime data via MCP."""
    print("Fetching maritime data via MCP...")

    # Get full report which includes everything
    full_report = await run_mcp_query("get_full_report")

    return full_report


def synthesize_alpha_alert(client: OpenAI, data: dict[str, Any]) -> str:
    """Use OpenAI to synthesize data into an Alpha Alert report.

    Args:
        client: OpenAI client
        data: Maritime data from MCP

    Returns:
        Alpha Alert report as markdown string
    """
    # Convert data to summary for prompt
    data_summary = json.dumps(data, indent=2)[:10000]  # Limit token usage

    prompt = f"""You are a maritime shipping analyst specializing in freight market intelligence.
Analyze the following maritime data and create an "Alpha Alert" report.

The Alpha Alert should be a concise, actionable report that includes:

1. **Executive Summary** - Key findings in 2-3 sentences
2. **Freight Rate Analysis** - Current FBX rates and notable changes
3. **Anomaly Watch** - Any detected anomalies with severity levels
4. **Market Implications** - What this means for shipping markets
5. **Alpha Signal** - A clear, actionable insight or opportunity

Use professional financial/analysis tone. Keep it under 800 words.

Here is the maritime data:

{data_summary}

Generate the Alpha Alert report in markdown format."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a maritime shipping analyst. Create concise, actionable Alpha Alert reports."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )

    return response.choices[0].message.content


def generate_template_report(data: dict[str, Any]) -> str:
    """Generate a template-based Alpha Alert report when OpenAI is unavailable.

    Args:
        data: Maritime data from MCP

    Returns:
        Alpha Alert report as markdown string
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Extract key information
    anomalies = data.get("anomalies", [])
    freight_rates = data.get("freight_rates", {})
    maritime_stats = data.get("maritime_stats", {})
    anomaly_summary = data.get("anomaly_summary", {})

    # Build report
    report = f"""# Alpha Alert: Maritime Market Intelligence

**Generated:** {timestamp}

---

## Executive Summary

Maritime shipping markets show active anomaly detection with {len(anomalies)} flagged events.
Freight rates from FBX and UNCTAD statistics provide current market context for shipping analytics.

---

## Freight Rate Analysis

**Source:** FBX (Freightos Baltic Index)
**Status:** {freight_rates.get("status", "unknown")}

"""

    # Add route data if available
    routes = freight_rates.get("data", {}).get("routes", [])
    if routes:
        report += "### Key Route Rates\n\n"
        for route in routes[:5]:  # Top 5 routes
            route_name = route.get("route", route.get("name", "Unknown"))
            rate = route.get("rate", route.get("price", "N/A"))
            report += f"- **{route_name}:** ${rate}\n"
    else:
        report += "No route data available.\n"

    report += "\n## Anomaly Watch\n\n"

    # Initialize severity lists (used later in Alpha Signal section)
    high_severity = []
    medium_severity = []
    low_severity = []

    if anomalies:
        # Group by severity
        high_severity = [a for a in anomalies if a.get("severity") == "high"]
        medium_severity = [a for a in anomalies if a.get("severity") == "medium"]
        low_severity = [a for a in anomalies if a.get("severity") == "low"]

        if high_severity:
            report += f"### High Severity ({len(high_severity)})\n\n"
            for a in high_severity:
                metric = a.get("metric", "Unknown")
                deviation = a.get("deviation", a.get("z_score", "N/A"))
                report += f"- **{metric}:** {deviation:.2f} deviation\n"
            report += "\n"

        if medium_severity:
            report += f"### Medium Severity ({len(medium_severity)})\n\n"
            for a in medium_severity[:3]:
                metric = a.get("metric", "Unknown")
                deviation = a.get("deviation", a.get("z_score", "N/A"))
                report += f"- **{metric}:** {deviation:.2f} deviation\n"
            report += "\n"

        if low_severity:
            report += f"### Low Severity ({len(low_severity)}) - {', '.join([a.get('metric', '')[:20] for a in low_severity[:3]])}"
            report += "\n\n"
    else:
        report += "No anomalies detected in current data window.\n\n"

    report += f"""## Maritime Statistics Summary

**Source:** UNCTAD
**Status:** {maritime_stats.get("status", "unknown")}

"""

    indicators = maritime_stats.get("data", {}).get("indicators", [])
    if indicators:
        for ind in indicators[:3]:
            name = ind.get("name", ind.get("indicator", "Unknown"))
            value = ind.get("value", "N/A")
            report += f"- **{name}:** {value}\n"
    else:
        report += "No maritime statistics available.\n"

    report += f"""
---

## Market Implications

Current analysis indicates {"active market conditions with detected anomalies" if anomalies else "stable market conditions with no significant anomalies"}.
Monitor high-severity anomalies for potential trading opportunities or risk management considerations.

---

## Alpha Signal

{"EXECUTIVE ALERT: " + "; ".join([a.get("metric", "") for a in high_severity[:2]]) if high_severity else "No high-priority alpha signals detected. Monitor anomaly feed for updates."}

---

*Report generated by Maritime MCP Alpha Reporter*
*Data sources: FBX Freight Rates, UNCTAD Maritime Statistics*
"""

    return report


async def main():
    """Main entry point for Alpha Alert generation."""
    print("=" * 60)
    print("Maritime Alpha Alert Generator")
    print("=" * 60)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Fetch maritime data via MCP
    print("\n[1/3] Fetching maritime data via MCP server...")
    try:
        data = await fetch_maritime_data()
        print(f"  ✓ Retrieved data with {len(data.get('anomalies', []))} anomalies")
    except Exception as e:
        print(f"  ✗ Error fetching data: {e}")
        # Use fallback/sample data
        data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "anomalies": [],
            "freight_rates": {"status": "error", "data": {}},
            "maritime_stats": {"status": "error", "data": {}},
            "anomaly_summary": {}
        }

    # Synthesize report
    print("\n[2/3] Synthesizing Alpha Alert report...")
    client = get_openai_client()

    if client:
        try:
            report = synthesize_alpha_alert(client, data)
            print("  ✓ Generated AI-powered Alpha Alert")
        except Exception as e:
            print(f"  ✗ OpenAI synthesis failed: {e}")
            report = generate_template_report(data)
            print("  ✓ Generated template-based Alpha Alert")
    else:
        report = generate_template_report(data)
        print("  ✓ Generated template-based Alpha Alert (no OpenAI key)")

    # Write output
    print("\n[3/3] Writing output...")
    output_file = OUTPUT_DIR / f"alpha_alert_{ALERT_TIMESTAMP}.md"
    output_file.write_text(report)
    print(f"  ✓ Saved to {output_file}")

    # Also save latest as reference
    latest_file = OUTPUT_DIR / "latest_alpha_alert.md"
    latest_file.write_text(report)
    print(f"  ✓ Updated {latest_file}")

    print("\n" + "=" * 60)
    print("Alpha Alert generation complete!")
    print("=" * 60)

    # Print report preview
    print("\n--- Report Preview ---\n")
    print(report[:1500] + "..." if len(report) > 1500 else report)


if __name__ == "__main__":
    asyncio.run(main())
