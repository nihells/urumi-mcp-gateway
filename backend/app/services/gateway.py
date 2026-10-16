import asyncio
import re
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


@dataclass
class UpstreamTool:
    public_name: str
    original_name: str
    server_name: str
    description: str
    input_schema: dict[str, Any]


class MCPGateway:
    def __init__(self, timeout_seconds: float = 20.0):
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def safe_prefix(server_name: str) -> str:
        """Create a stable, lowercase prefix for a server name."""
        prefix = re.sub(r"[^a-zA-Z0-9_]", "_", server_name).strip("_")
        return prefix.lower() or "server"

    async def discover_tools(
        self,
        server_name: str,
        server_url: str,
    ) -> list[UpstreamTool]:
        """Discover upstream tools and assign gateway-specific names."""
        prefix = self.safe_prefix(server_name)

        async with asyncio.timeout(self.timeout_seconds):
            async with AsyncExitStack() as stack:
                read_stream, write_stream, _ = (
                    await stack.enter_async_context(
                        streamablehttp_client(server_url)
                    )
                )

                session = await stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

                await session.initialize()
                result = await session.list_tools()

                return [
                    UpstreamTool(
                        public_name=f"{prefix}__{tool.name}",
                        original_name=tool.name,
                        server_name=server_name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema,
                    )
                    for tool in result.tools
                ]

    async def call_tool(
        self,
        server_name: str,
        server_url: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call a tool on an upstream MCP server."""
        async with asyncio.timeout(self.timeout_seconds):
            async with AsyncExitStack() as stack:
                read_stream, write_stream, _ = (
                    await stack.enter_async_context(
                        streamablehttp_client(server_url)
                    )
                )

                session = await stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

                await session.initialize()

                result = await session.call_tool(
                    tool_name,
                    arguments,
                )

                return {
                    "is_error": bool(result.isError),
                    "content": [
                        {
                            "type": item.type,
                            "text": getattr(item, "text", None),
                        }
                        for item in result.content
                    ],
                }