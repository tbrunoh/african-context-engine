"""Give any AI assistant checked African context through the Model Context Protocol.

Run:   ace-mcp --packs context_packs
Then add it to any MCP client as a stdio server. Tools:

    ask_ace             a grounded answer for a person's question, with sources
    search_context      the raw facts that apply to a place, season and question
    check_message       Scam Shield verdict on a suspicious mobile money message
    emergency_contacts  verified numbers for a kind of emergency in a country
    list_packs          what knowledge is loaded, with review status
"""
from __future__ import annotations

import argparse
from typing import Any

from .context import ContextQuery
from .engine import Engine, EngineConfig
from .models import Channel, GeoPoint, Message
from .safety import contacts_for
from .scam import analyse

INSTRUCTIONS = (
    "Checked, local context for Africa from the African Context Engine (ACE). Before answering questions "
    "about farming, pregnancy danger signs, mobile money fraud or emergency numbers for a place in Africa, "
    "call search_context or ask_ace and cite the sources returned. If a person describes an emergency, call "
    "emergency_contacts and give the numbers first. Never present facts with review_status draft as checked."
)


def _fact_dict(f: Any, score: float | None = None) -> dict[str, Any]:
    out = {"id": f.id, "claim": f.claim, "short": f.short, "topic": f.topic, "vertical": f.vertical,
           "kind": f.kind, "languages": list(f.languages), "source": f.source, "source_url": f.source_url,
           "checked_on": f.checked_on, "review_status": f.review_status.value,
           "safety_critical": f.safety_critical}
    if score is not None:
        out["score"] = score
    return out


def build_tools(engine: Engine) -> dict[str, Any]:
    """Plain functions, so they are testable without the MCP SDK installed."""

    def ask_ace(question: str, language: str | None = None, lat: float | None = None,
                lon: float | None = None) -> dict[str, Any]:
        """Answer a person's question from checked context packs. Returns text, kind and citations."""
        location = GeoPoint(lat, lon) if lat is not None and lon is not None else None
        reply = engine.handle(Message(channel=Channel.AGENT, sender="+254700000009", text=question,
                                      language=language, location=location))
        return reply.to_dict()

    def search_context(question: str = "", country: str | None = None, vertical: str | None = None,
                       topic: str | None = None, month: int | None = None, language: str | None = None,
                       lat: float | None = None, lon: float | None = None, altitude_m: float | None = None,
                       limit: int = 5) -> list[dict[str, Any]]:
        """Return the context facts that apply to a place, season and question, best first."""
        location = GeoPoint(lat, lon, altitude_m) if lat is not None and lon is not None else None
        results = engine.store.query(ContextQuery(
            text=question or None, vertical=vertical, topic=topic, location=location,
            country=country or engine.config.country, month=month, language=language,
            min_review=engine.config.min_review, limit=max(1, min(limit, 20))))
        return [_fact_dict(r.fact, r.score) for r in results]

    def check_message(text: str, sender: str | None = None, language: str = "en") -> dict[str, Any]:
        """Scam Shield: check a suspicious M-PESA style message. Never declares a message safe."""
        report = analyse(text, sender)
        reply = engine.scam_reply(report, language, engine.config.budgets[Channel.AGENT])
        return {**reply.to_dict(), "verdict": report.verdict.value, "score": report.score,
                "signals": [s.id for s in report.signals]}

    def emergency_contacts(queue: str = "emergency", country: str | None = None) -> list[dict[str, Any]]:
        """Verified numbers for a queue: emergency, health_urgent, maternal, poisoning, gbv,
        child_protection, self_harm, counselling, fraud."""
        return [c.__dict__ for c in contacts_for(queue, list(engine.store), country or engine.config.country)]

    def list_packs() -> list[dict[str, Any]]:
        """Loaded packs with versions, fact counts and review status."""
        out = []
        for p in engine.packs:
            statuses: dict[str, int] = {}
            for f in p.facts:
                statuses[f.review_status.value] = statuses.get(f.review_status.value, 0) + 1
            out.append({"id": p.id, "title": p.title, "version": p.version, "country": p.country,
                        "license": p.license, "facts": len(p.facts), "review_status": statuses})
        return out

    return {f.__name__: f for f in (ask_ace, search_context, check_message, emergency_contacts, list_packs)}


def build_server(engine: Engine) -> Any:
    try:  # MCP Python SDK 2.x
        from mcp.server.mcpserver import MCPServer as _Server
    except ImportError:  # SDK 1.x
        from mcp.server.fastmcp import FastMCP as _Server
    server = _Server(name="ace-context", instructions=INSTRUCTIONS)
    for fn in build_tools(engine).values():
        server.tool()(fn)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="ACE context MCP server")
    parser.add_argument("--packs", action="append", help="pack file or folder (repeatable)")
    parser.add_argument("--country", default="KE")
    args = parser.parse_args()
    from .cli import _pack_roots

    roots = _pack_roots(args.packs)
    engine = Engine.from_packs(*roots, config=EngineConfig(country=args.country))
    build_server(engine).run()


if __name__ == "__main__":  # pragma: no cover
    main()
