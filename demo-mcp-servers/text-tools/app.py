
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings


mcp = FastMCP(
    "Text Tools MCP Server",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        allowed_hosts=[
            "text-tools-mcp.urumi.svc.cluster.local:8003",
            "text-tools-mcp.urumi.svc.cluster.local",
            "localhost:8003",
            "127.0.0.1:8003",
        ],
    ),
)


@mcp.tool()
def count_words(text: str) -> str:
    """Count the words, characters, and sentences in text."""
    words = text.split()
    sentences = sum(text.count(mark) for mark in (".", "!", "?"))

    return (
        f"Words: {len(words)}, "
        f"Characters: {len(text)}, "
        f"Sentences: {sentences}"
    )


@mcp.tool()
def convert_case(text: str, case: str) -> str:
    """Convert text to uppercase, lowercase, or title case."""
    conversions = {
        "upper": str.upper,
        "lower": str.lower,
        "title": str.title,
    }

    operation = conversions.get(case.lower())

    if operation is None:
        return "Unsupported case. Use upper, lower, or title."

    return operation(text)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8003"))
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port
    mcp.run(transport="streamable-http")
