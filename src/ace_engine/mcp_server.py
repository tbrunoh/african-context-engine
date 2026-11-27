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
import json
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


def http_app(engine: Engine, allowed_hosts: list[str] | None = None, path: str = "/mcp",
             paused: bool = False) -> Any:
    """An ASGI app serving MCP over Streamable HTTP: stateless, JSON responses, a /healthz route, and host checks.

    Stateless means no session is held between calls, so any instance can answer any request and nothing about a
    caller outlives their request. When paused (the spend guard sets ACE_PAUSED), every MCP call gets 503."""
    if paused:
        return _paused_app
    from mcp.server.transport_security import TransportSecuritySettings

    server = build_server(engine)
    hosts = [h for h in (allowed_hosts or []) if h]
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=bool(hosts),
        allowed_hosts=[*hosts, *(f"{h}:*" for h in hosts)],
        allowed_origins=[f"https://{h}" for h in hosts])

    import os

    from starlette.requests import Request
    from starlette.responses import JSONResponse

    from . import __version__

    commit = (os.environ.get("ACE_COMMIT") or "")[:12]

    async def healthz(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": __version__, "commit": commit, "tools": len(build_tools(engine))})

    # /healthz for Cloud Run, and /mcp/healthz so the release check can reach this service through the load balancer
    server.custom_route("/healthz", methods=["GET"])(healthz)
    server.custom_route(path.rstrip("/") + "/healthz", methods=["GET"])(healthz)

    try:  # SDK 2.x takes the transport settings here
        return server.streamable_http_app(streamable_http_path=path, stateless_http=True, json_response=True,
                                          transport_security=security)
    except TypeError:  # SDK 1.x reads them from the server's settings
        server.settings.streamable_http_path = path
        server.settings.stateless_http = True
        server.settings.json_response = True
        server.settings.transport_security = security
        return server.streamable_http_app()


async def _paused_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    """The MCP endpoint while the demo is paused: health still answers, every call gets 503 and a reason."""
    if scope["type"] != "http":
        return
    from . import __version__

    if scope.get("path") in ("/healthz", "/mcp/healthz"):
        status, body = 200, {"status": "paused", "version": __version__}
    else:
        status, body = 503, {"error": "This demonstration has reached its spending limit for the month and is paused "
                                       "until the 1st."}
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"retry-after", b"86400")]})
    await send({"type": "http.response.body", "body": json.dumps(body).encode()})


def tips_allowed(env: Any) -> bool:
    """TIP stays off on a public deployment (ACE_PUBLIC=1) or when ACE_TIPS=off, as on the site: a public server
    keeps nothing a caller sends."""
    from .app import _off, _on

    return not (_off(env, "ACE_TIPS") or _on(env, "ACE_PUBLIC"))


def main() -> None:
    import os

    parser = argparse.ArgumentParser(description="ACE context MCP server")
    parser.add_argument("--packs", action="append", help="pack file or folder (repeatable)")
    parser.add_argument("--country", default=None, help="pin one country (default: callers choose per call)")
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio",
                        help="stdio for a local assistant (default), or http for Streamable HTTP at /mcp")
    parser.add_argument("--host", default="0.0.0.0", help="address to listen on with --transport http")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")),
                        help="port for --transport http (default: $PORT or 8080)")
    parser.add_argument("--allowed-host", action="append", dest="allowed_hosts",
                        help="Host header to accept with --transport http (repeatable; also ACE_MCP_ALLOWED_HOSTS)")
    args = parser.parse_args()
    from .cli import _pack_roots

    roots = _pack_roots(args.packs)
    engine = Engine.from_packs(*roots, config=EngineConfig(country=args.country, tips=tips_allowed(os.environ)))
    if args.transport == "stdio":
        build_server(engine).run()
        return
    import threading

    import uvicorn

    if engine.services is not None:  # the same snapshot sets and facility index as the site
        from .services import facility

        if os.environ.get("ACE_SNAPSHOT_BASE"):
            from .snapshots.manifest import SnapshotWatcher

            # The published set is loaded before the server starts, so no call is answered from the bundled set
            watcher = SnapshotWatcher(engine, os.environ["ACE_SNAPSHOT_BASE"],
                                      float(os.environ.get("ACE_SNAPSHOT_INTERVAL") or 300))
            watcher.check_once()
            watcher.on_swap = lambda hub: facility.warm(hub.ctx)
            watcher.start()
        threading.Thread(target=lambda: facility.warm(engine.services.ctx), daemon=True).start()
    hosts = args.allowed_hosts or [h.strip() for h in os.environ.get("ACE_MCP_ALLOWED_HOSTS", "").split(",")]
    paused = bool(os.environ.get("ACE_PAUSED"))
    uvicorn.run(http_app(engine, hosts, paused=paused), host=args.host, port=args.port, log_level="warning",
                proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":  # pragma: no cover
    main()
