"""Expose ACE context to any AI assistant through the Model Context Protocol.

Run:  ace-mcp --pack context_packs/examples/kenya-maize-demo.yaml
Then add it to an MCP client (Claude, Gemini, ChatGPT, Copilot or any other
host) as a stdio server.
"""
from __future__ import annotations

import argparse
from typing import Any

from .context import ContextQuery, ContextStore, load_pack
from .models import GeoPoint

try:  # MCP Python SDK 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # pragma: no cover  (SDK 1.x)
    from mcp.server.fastmcp import FastMCP as _Server


def build_server(store: ContextStore, include_verified: bool = False) -> Any:
    server = _Server(
        name="ace-context",
        instructions=("Hyperlocal context for Africa from the African Context Engine. "
                      "Call query_context before answering questions about farming, health, "
                      "markets or land in a specific African place. Cite fact ids and sources."),
    )

    @server.tool()
    def query_context(lat: float | None = None, lon: float | None = None,
                      altitude_m: float | None = None, country: str | None = None,
                      admin_area: str | None = None, vertical: str | None = None,
                      topic: str | None = None, subject: str | None = None,
                      month: int | None = None, language: str | None = None,
                      limit: int = 5) -> list[dict[str, Any]]:
        """Return the context facts that apply to a place, season and subject, best first."""
        location = GeoPoint(lat, lon, altitude_m) if lat is not None and lon is not None else None
        results = store.query(ContextQuery(
            vertical=vertical, topic=topic, subject=subject, location=location,
            country=country, admin_area=admin_area, month=month, language=language,
            include_verified=include_verified, limit=max(1, min(limit, 20)),
        ))
        return [{
            "id": r.fact.id, "claim": r.fact.claim, "source": r.fact.source,
            "review_status": r.fact.review_status.value, "tier": r.fact.tier.value,
            "safety_critical": r.fact.safety_critical, "score": round(r.score, 2),
        } for r in results]

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="ACE context MCP server")
    parser.add_argument("--pack", action="append", required=True, help="Path to a context pack")
    args = parser.parse_args()
    store = ContextStore()
    for path in args.pack:
        store.extend(list(load_pack(path).facts))
    build_server(store).run()


if __name__ == "__main__":  # pragma: no cover
    main()
