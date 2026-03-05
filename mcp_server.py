"""MCP Server for Maritime Data API.

This module wraps the existing maritime tracker endpoints as MCP tools,
allowing AI agents to query maritime data via the Model Context Protocol.
"""

import json
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


def create_mcp_server():
    """Create and configure the MCP server with maritime data tools."""
    server = Server("maritime-mcp")

    # Import the scraper service
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from scraper_service import get_service

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available MCP tools."""
        return [
            Tool(
                name="get_freight_rates",
                description="Query FBX shipping freight rates. Returns current shipping container rates across major trade routes.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "description": "No parameters required"
                }
            ),
            Tool(
                name="get_maritime_stats",
                description="Query UNCTAD maritime statistics. Returns global shipping industry statistics including fleet size, trade volumes, and port throughput.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "description": "No parameters required"
                }
            ),
            Tool(
                name="get_anomalies",
                description="Query detected shipping anomalies. Identifies unusual patterns in freight rates and maritime data that may indicate market opportunities or risks.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Filter by source (fbx, unctad)",
                            "enum": ["fbx", "unctad"],
                            "nullable": True
                        },
                        "min_severity": {
                            "type": "string",
                            "description": "Filter anomalies by minimum severity level",
                            "enum": ["low", "medium", "high"],
                            "nullable": True
                        }
                    },
                    "description": "Optional filters for anomalies"
                }
            ),
            Tool(
                name="get_full_report",
                description="Get complete maritime data report including freight rates, maritime statistics, and detected anomalies. Use this for comprehensive analysis.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "description": "No parameters required"
                }
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Any) -> list[TextContent]:
        """Handle tool calls."""
        service = get_service()

        try:
            if name == "get_freight_rates":
                result = service.get_freight_rates()
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "get_maritime_stats":
                result = service.get_maritime_stats()
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "get_anomalies":
                source = arguments.get("source") if arguments else None
                min_severity = arguments.get("min_severity") if arguments else None
                result = service.get_anomalies(source=source, min_severity=min_severity)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "get_full_report":
                result = service.get_full_report()
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            else:
                return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    return server


async def main():
    """Run the MCP server."""
    server = create_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
