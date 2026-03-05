#!/usr/bin/env python3
"""Automated Alpha Report Generator using MiniMax LLM + Maritime MCP.

This script demonstrates AI agents consuming maritime data through MCP
and synthesizing it into an Alpha Alert report using MiniMax LLM.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Configuration
SCRIPT_DIR = Path(__file__).parent
MCP_SERVER_PATH = SCRIPT_DIR / "mcp_server.py"
OUTPUT_DIR = SCRIPT_DIR / "output"
ALERT_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def get_minimax_client():
    """Initialize MiniMax client (OpenAI-compatible API)."""
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        print("WARNING: MINIMAX_API_KEY not set. Using template-based report generation.")
        return None

    # MiniMax uses OpenAI-compatible API
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.minimax.chat/v1"
        )
        return client
    except Exception as e:
        print(f"Failed to initialize MiniMax client: {e}")
        return None


def run_mcp_query(tool_name: str, arguments: dict = None) -> dict[str, Any]:
    """Run a query against the MCP server using stdio transport.

    Args:
        tool_name: Name of the MCP tool to call
        arguments: Optional arguments for the tool

    Returns:
        Response from MCP server as dictionary
    """
    import subprocess

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
                "name": "auto-alpha-report",
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

    # Run MCP server and communicate via stdin/stdout
    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(MCP_SERVER_PATH.parent)
    )

    # Send initialize request first, then tool call
    init_json = json.dumps(initialize_request) + "\n"
    tool_json = json.dumps(call_tool_request) + "\n"

    stdout, stderr = proc.communicate(input=init_json + tool_json, timeout=30)

    if stderr and "WARNING" not in stderr:
        print(f"MCP Server stderr: {stderr}")

    proc.wait()

    # Parse response - look for tool call result
    try:
        for line in stdout.strip().split("\n"):
            if line.strip():
                try:
                    response = json.loads(line)
                    if "result" in response:
                        result_data = response["result"]
                        if isinstance(result_data, dict) and "content" in result_data:
                            for content in result_data["content"]:
                                if content.get("type") == "text":
                                    return json.loads(content["text"])
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return {"error": "Failed to parse MCP response", "raw": stdout}


def fetch_maritime_data() -> dict[str, Any]:
    """Fetch all maritime data via MCP."""
    print("Fetching maritime data via MCP...")

    # Get full report which includes everything
    full_report = run_mcp_query("get_full_report")

    return full_report


def synthesize_with_minimax(client, data: dict[str, Any]) -> str:
    """Use MiniMax to synthesize data into an Alpha Alert report.

    Args:
        client: MiniMax (OpenAI-compatible) client
        data: Maritime data from MCP

    Returns:
        Alpha Alert report as markdown string
    """
    data_summary = json.dumps(data, indent=2)[:10000]

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
        model="abab6.5s-chat",
        messages=[
            {"role": "system", "content": "You are a maritime shipping analyst. Create concise, actionable Alpha Alert reports."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )

    return response.choices[0].message.content


def generate_template_report(data: dict[str, Any]) -> str:
    """Generate a template-based Alpha Alert report when LLM is unavailable."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    anomalies = data.get("anomalies", [])
    freight_rates = data.get("freight_rates", {})
    maritime_stats = data.get("maritime_stats", {})

    report = f"""# Alpha Alert: Maritime Market Intelligence

**Generated:** {timestamp}
**Source:** MiniMax MCP Integration

---

## Executive Summary

Maritime shipping markets show active anomaly detection with {len(anomalies)} flagged events.
Freight rates from FBX and UNCTAD statistics provide current market context for shipping analytics.

---

## Freight Rate Analysis

**Source:** FBX (Freightos Baltic Index)
**Status:** {freight_rates.get("status", "unknown")}

"""

    routes = freight_rates.get("data", {}).get("routes", [])
    if routes:
        report += "### Key Route Rates\n\n"
        for route in routes[:5]:
            route_name = route.get("route", route.get("name", "Unknown"))
            rate = route.get("rate", route.get("price", "N/A"))
            report += f"- **{route_name}:** ${rate}\n"
    else:
        report += "No route data available.\n"

    report += "\n## Anomaly Watch\n\n"

    if anomalies:
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
            report += f"### Low Severity ({len(low_severity)})\n\n"
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

    report += """
---

## Market Implications

Current analysis indicates stable market conditions. Monitor anomaly feed for updates.

---

## Alpha Signal

No high-priority alpha signals detected. Monitor anomaly feed for updates.

---

*Report generated by Maritime MCP + MiniMax Alpha Reporter*
*Data sources: FBX Freight Rates, UNCTAD Maritime Statistics*
"""

    return report


def publish_to_gist(content: str, filename: str = "alpha_alert.md") -> Optional[str]:
    """Publish content to GitHub Gist.

    Args:
        content: Markdown content to publish
        filename: Filename for the gist

    Returns:
        Gist URL if successful, None otherwise
    """
    import requests

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("WARNING: GITHUB_TOKEN not set. Skipping Gist publish.")
        return None

    gist_data = {
        "description": "Maritime Alpha Alert Report - Generated via MCP + MiniMax",
        "public": True,
        "files": {
            filename: {"content": content}
        }
    }

    try:
        response = requests.post(
            "https://api.github.com/gists",
            json=gist_data,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        response.raise_for_status()
        gist_url = response.json().get("html_url")
        return gist_url
    except Exception as e:
        print(f"Failed to publish Gist: {e}")
        return None


def main():
    """Main entry point for automated Alpha Alert generation."""
    print("=" * 60)
    print("Maritime Alpha Alert Generator (MiniMax + MCP)")
    print("=" * 60)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Fetch maritime data via MCP
    print("\n[1/4] Fetching maritime data via MCP server...")
    try:
        data = fetch_maritime_data()
        print(f"  ✓ Retrieved data with {len(data.get('anomalies', []))} anomalies")
    except Exception as e:
        print(f"  ✗ Error fetching data: {e}")
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "anomalies": [],
            "freight_rates": {"status": "error", "data": {}},
            "maritime_stats": {"status": "error", "data": {}},
            "anomaly_summary": {}
        }

    # Synthesize report
    print("\n[2/4] Synthesizing Alpha Alert report...")
    client = get_minimax_client()

    if client:
        try:
            report = synthesize_with_minimax(client, data)
            print("  ✓ Generated MiniMax-powered Alpha Alert")
        except Exception as e:
            print(f"  ✗ MiniMax synthesis failed: {e}")
            report = generate_template_report(data)
            print("  ✓ Generated template-based Alpha Alert")
    else:
        report = generate_template_report(data)
        print("  ✓ Generated template-based Alpha Alert (no MiniMax key)")

    # Write output
    print("\n[3/4] Writing output files...")
    output_file = OUTPUT_DIR / f"alpha_alert_{ALERT_TIMESTAMP}.md"
    output_file.write_text(report)
    print(f"  ✓ Saved to {output_file}")

    latest_file = OUTPUT_DIR / "latest_alpha_alert.md"
    latest_file.write_text(report)
    print(f"  ✓ Updated {latest_file}")

    # Publish to GitHub Gist
    print("\n[4/4] Publishing to GitHub Gist...")
    gist_url = publish_to_gist(report, f"alpha_alert_{ALERT_TIMESTAMP}.md")
    if gist_url:
        print(f"  ✓ Published to: {gist_url}")
    else:
        print("  ✗ Skipped Gist publish (no token or error)")

    print("\n" + "=" * 60)
    print("Alpha Alert generation complete!")
    print("=" * 60)

    # Print report preview
    print("\n--- Report Preview ---\n")
    print(report[:1500] + "..." if len(report) > 1500 else report)

    if gist_url:
        print(f"\n📤 Gist URL: {gist_url}")


if __name__ == "__main__":
    main()
