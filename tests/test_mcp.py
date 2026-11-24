import asyncio
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from ace_engine.context import ContextStore, load_pack
from ace_engine.mcp_server import build_server

PACK = Path(__file__).resolve().parents[1] / "context_packs" / "examples" / "kenya-maize-demo.yaml"


def test_mcp_server_exposes_query_context():
    store = ContextStore()
    store.extend(list(load_pack(PACK).facts))
    server = build_server(store)

    async def run():
        names = [t.name for t in await server.list_tools()]
        result = await server.call_tool("query_context", {"lat": -0.42, "lon": 36.95, "altitude_m": 1950,
                                                          "country": "KE", "topic": "pest"})
        return names, str(result)

    names, text = asyncio.run(run())
    assert names == ["query_context"]
    assert "faw-highland-placeholder" in text and "faw-coastal-placeholder" not in text
