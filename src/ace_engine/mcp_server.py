"""Give any AI assistant checked African context through the Model Context Protocol.

Run:   ace-mcp --packs context_packs
Then add it to any MCP client as a stdio server. Tools:

    ask_ace             a grounded answer for a person's question, with sources
    search_context      the raw facts that apply to a place, season and question
    check_message       Scam Shield verdict on a suspicious mobile money message
    emergency_contacts  verified numbers for a kind of emergency in a country
    list_packs          what knowledge is loaded, with review status

V2 decision services (preview), each answering with dated, cited data:

    rain_this_week      chance of rain each day for an area
    official_warnings   warnings in force from the national alerting authority
    nearest_facility    nearest public health facilities
    market_prices       WFP market prices near a place
    pregnancy_companion when the next antenatal check is due, and when to go now
    pest_check          the likely crop problem and the first step
    service_coverage    which service works in which country, and why not where it does not
"""
from __future__ import annotations

import argparse
import secrets
from typing import Any

from .context import ContextQuery
from .countries import COUNTRIES
from .engine import Engine, EngineConfig
from .models import Channel, GeoPoint, Message
from .safety import contacts_for
from .scam import analyse

INSTRUCTIONS = (
    "Checked, local context for Africa from the African Context Engine (ACE). Before answering questions "
    "about farming, pregnancy danger signs, mobile money fraud or emergency numbers for a place in Africa, "
    "call search_context or ask_ace and cite the sources returned. If a person describes an emergency, call "
    "emergency_contacts and give the numbers first. Never present facts with review_status draft as checked. "
    "The V2 services (rain_this_week, official_warnings, nearest_facility, market_prices, pregnancy_companion, "
    "pest_check) are a preview: pass on their date and source, and call service_coverage to see gaps by country."
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

    def _country(country: str | None) -> str:
        code = (country or engine.config.country or "").upper()
        if code not in COUNTRIES:
            raise ValueError("country is required, one of " + ", ".join(COUNTRIES))
        return code

    def ask_ace(question: str, country: str | None = None, language: str | None = None, lat: float | None = None,
                lon: float | None = None) -> dict[str, Any]:
        """Answer a person's question from checked context packs for the country they are in (ISO code such as
        KE, NG or SN; pass it whenever it is known). Returns text, kind and citations. Emergencies get that
        country's numbers. With no country, ACE answers as for a caller outside its 34 countries: no country's
        facts or numbers, and an emergency is told to call the local emergency number."""
        location = GeoPoint(lat, lon) if lat is not None and lon is not None else None
        code = _country(country) if (country or engine.config.country) else None
        # A fresh number for each question, so agents never share a session, a language choice or a pending question
        sender = (f"+{COUNTRIES[code].dial}7{secrets.randbelow(10**8):08d}" if code
                  else f"+888{secrets.randbelow(10**9):09d}")
        reply = engine.handle(Message(channel=Channel.AGENT, sender=sender, text=question,
                                      language=language, location=location))
        engine.profiles.forget(sender)  # one question, one profile: nothing builds up in a long running server
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

    def check_message(text: str, sender: str | None = None, language: str = "en",
                      country: str | None = None) -> dict[str, Any]:
        """Scam Shield: check a suspicious mobile money message (en, sw or fr). Never declares a message safe.
        Operator guidance is cited only for the country it belongs to, so pass the country when it is known."""
        report = analyse(text, sender)
        code = _country(country) if (country or engine.config.country) else None
        reply = engine.scam_reply(report, language, engine.config.budgets[Channel.AGENT], code)
        return {**reply.to_dict(), "verdict": report.verdict.value, "score": report.score,
                "signals": [s.id for s in report.signals]}

    def emergency_contacts(country: str, queue: str = "emergency") -> list[dict[str, Any]]:
        """Verified numbers in one country (ISO code such as KE, ZA or CI) for a queue: emergency,
        health_urgent, maternal, poisoning, gbv, violence, child_protection, self_harm, counselling."""
        return [c.__dict__ for c in contacts_for(queue, list(engine.store), _country(country))]

    def list_packs() -> list[dict[str, Any]]:
        """Loaded packs with versions, fact counts and review status."""
        out = []
        for p in engine.packs:
            statuses: dict[str, int] = {}
            for f in p.facts:
                statuses[f.review_status.value] = statuses.get(f.review_status.value, 0) + 1
            out.append({"id": p.id, "title": p.title, "version": p.version, "country": p.country,
                        "countries": sorted({c for f in p.facts for c in f.scope.countries}),
                        "license": p.license, "facts": len(p.facts), "review_status": statuses})
        return out

    tools = [ask_ace, search_context, check_message, emergency_contacts, list_packs]
    hub = engine.services
    if hub is not None:
        def rain_this_week(country: str, place: str | None = None, lat: float | None = None, lon: float | None = None,
                           language: str = "en") -> dict[str, Any]:
            """Chance of rain each day this week for an area of a covered country (ISO code such as KE, NG, SN),
            from the ECMWF ensemble. Give the area name (county, state, region or district) or lat and lon."""
            return hub.call("rain_this_week", country, place, lat, lon, language)

        def official_warnings(country: str, place: str | None = None, lat: float | None = None,
                              lon: float | None = None, language: str = "en") -> dict[str, Any]:
            """Official CAP warnings in force from the national alerting authority for an area. Says when the
            authority publishes no feed or when the feed could not be checked recently."""
            return hub.call("official_warnings", country, place, lat, lon, language)

        def nearest_facility(country: str, place: str | None = None, lat: float | None = None,
                             lon: float | None = None, language: str = "en") -> dict[str, Any]:
            """Nearest public health facilities (2019 list, no phone numbers) and the country's emergency number."""
            return hub.call("nearest_facility", country, place, lat, lon, language)

        def market_prices(country: str, place: str | None = None, food: str | None = None, lat: float | None = None,
                          lon: float | None = None, language: str = "en") -> dict[str, Any]:
            """Latest WFP market prices near a place, optionally for one food such as maize, beans or rice.
            Refuses prices older than about four months."""
            return hub.call("market_prices", country, place, lat, lon, language, text=food or "",
                            params={"food": food} if food else None)

        def pregnancy_companion(country: str, weeks: int | None = None, language: str = "en") -> dict[str, Any]:
            """When the next antenatal check is due (WHO 2016 schedule), with the danger signs and the country's
            numbers. If the person describes a danger sign, call ask_ace or emergency_contacts first."""
            return hub.call("pregnancy_companion", country, None, None, None, language,
                            params={"weeks": weeks} if weeks else None)

        def pest_check(crop: str, symptoms: str = "", country: str | None = None,
                       language: str = "en") -> dict[str, Any]:
            """The likely problem for maize, cassava, banana or tomato from what the farmer sees, the first step,
            and a referral to an extension officer before spraying. The country (ISO code such as KE, NG or SN)
            is required."""
            return hub.call("pest_check", _country(country), None, None, None, language,
                            text=f"{crop} {symptoms}".strip())

        def service_coverage() -> dict[str, Any]:
            """Which V2 service is available in which covered country, and the reason where it is not."""
            return hub.coverage()

        tools += [rain_this_week, official_warnings, nearest_facility, market_prices, pregnancy_companion, pest_check,
                  service_coverage]
    return {f.__name__: f for f in tools}


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
    parser.add_argument("--country", default=None, help="pin one country (default: callers choose per call)")
    args = parser.parse_args()
    from .cli import _pack_roots

    roots = _pack_roots(args.packs)
    engine = Engine.from_packs(*roots, config=EngineConfig(country=args.country))
    build_server(engine).run()


if __name__ == "__main__":  # pragma: no cover
    main()
