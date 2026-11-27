"""The public site: the /try phone, coverage, developer guide, status and about pages, and the data behind them.

Pages are plain HTML files in ace_engine/web/site, filled with a few values at serve time. The phone on /try talks
to POST /try/ussd and POST /try/message. Each browser gets a random session in a cookie, scoped to /try, and its
sender is web:<country>:<token>: no phone number is ever asked for, and no session can match a real subscriber.
"""
from __future__ import annotations

import html
import json
import os
import secrets
from datetime import datetime, timezone
from functools import cache
from importlib import resources
from typing import Any

from . import __version__, encoding, i18n, speech
from .countries import COUNTRIES
from .identity import web_sender
from .models import Channel, Message, ReplyKind
from .text import SUPPORTED_LANGUAGES

SESSION_COOKIE = "ace_try"
SESSION_AGE = 24 * 3600
PAGES = {
    "/": ("home.html", "ACE, the African Context Engine",
          "Checked, local, citable answers for Africa on any phone, with a safety rail that runs first. Try it in "
          "34 countries and 32 languages."),
    "/try": ("try.html", "Try ACE on a simulated phone",
             "Try ACE the way people reach it: USSD, SMS, voice, WhatsApp or RCS, in 34 countries and 32 languages."),
    "/coverage": ("coverage.html", "Coverage: countries, services and languages",
                  "Which of ACE's six services works in each of 34 countries, why where it does not, and the "
                  "languages offered in each."),
    "/developers": ("developers.html", "Build with ACE: API and MCP",
                    "Call ACE over a JSON API or connect an AI assistant over MCP. Every answer cites its source."),
    "/status": ("status.html", "Status", "The version ACE runs, and how fresh each dataset is in each country."),
    "/about": ("about.html", "About ACE and privacy",
               "ACE is open source under Apache 2.0. What this demonstration keeps, and for how long."),
}
SITE_ORIGIN = "https://ace.korext.com"


def commit() -> str:
    return os.environ.get("ACE_COMMIT", "")[:12]


@cache
def _asset(name: str) -> str:
    return resources.files("ace_engine").joinpath(f"web/site/{name}").read_text(encoding="utf-8")


def asset_bytes(name: str) -> bytes | None:
    """A static file from web/site/static, or None. Only plain names: no folders, no dots at the start."""
    if not name or "/" in name or name.startswith(".") or ".." in name:
        return None
    ref = resources.files("ace_engine").joinpath(f"web/site/static/{name}")
    return ref.read_bytes() if ref.is_file() else None


CONTENT_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                 ".svg": "image/svg+xml", ".woff2": "font/woff2", ".png": "image/png", ".ico": "image/x-icon",
                 ".txt": "text/plain; charset=utf-8", ".xml": "application/xml; charset=utf-8"}


def page(path: str, extra: dict[str, str] | None = None) -> bytes | None:
    """A rendered page, or None when the path is not a page."""
    if path not in PAGES:
        return None
    body_file, title, description = PAGES[path]
    values = {
        "TITLE": html.escape(title if path != "/" else title),
        "DESCRIPTION": html.escape(description),
        "CANONICAL": SITE_ORIGIN + (path if path != "/" else "/"),
        "PAGE": path.strip("/") or "home",
        "VERSION": __version__,
        "COMMIT": html.escape(commit() or "local build"),
        "YEAR": str(datetime.now(timezone.utc).year),
        **(extra or {}),
    }
    out = _asset("layout.html").replace("{{CONTENT}}", _asset(body_file))
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    return out.encode("utf-8")


# ---------------------------------------------------------------- data for the pages


def voice_line(code: str) -> str:
    """How the voice line speaks a language: say (a standard voice), play (generated audio) or none."""
    if speech.speakable(code):
        return "say"
    if speech.play_voice(code):
        return "play"
    return "none"


def language_info(code: str) -> dict[str, Any]:
    loc = i18n.locales().get(code)
    return {"code": code, "name": i18n.english_name(code), "native": i18n.native_name(code),
            "preview": code != "en", "reviewed": bool(loc and loc.reviewed),
            "ucs2": i18n.is_ucs2(code), "rtl": bool(loc and loc.direction == "rtl"), "voice": voice_line(code)}


def countries_data(engine: Any) -> dict[str, Any]:
    """Everything the phone and the coverage page show about each country."""
    from .services.base import EXAMPLE_PLACE

    coverage = engine.services.coverage() if engine.services is not None else {}
    out = []
    for country in sorted(COUNTRIES.values(), key=lambda c: c.name):
        # General emergency lines first, then medical ones: some countries publish only an ambulance or SAMU line.
        found = {c.number: c for q in ("emergency", "health_urgent") for c in engine.numbers_for(q, country.code)}
        numbers = [{"number": c.number, "label": c.label} for c in found.values()][:4]
        out.append({
            "code": country.code, "name": country.name, "dial": country.dial,
            "languages": list(country.languages),
            "example_place": EXAMPLE_PLACE.get(country.code, ""),
            "emergency": numbers,
            "services": {sid: {"available": bool(cov.get(country.code, {}).get("available")),
                               "reason": cov.get(country.code, {}).get("detail", "")}
                         for sid, cov in coverage.items()},
        })
    from .services import SERVICES

    return {"countries": out,
            "languages": {code: language_info(code) for code in SUPPORTED_LANGUAGES},
            "services": {sid: svc.title.get("en", sid) for sid, svc in SERVICES.items()}}


def status_data(engine: Any, watcher: Any = None, model: str | None = None) -> dict[str, Any]:
    from .snapshots.manifest import freshness

    snaps = engine.services.snapshots if engine.services is not None else None
    rows = freshness(snaps) if snaps is not None else []
    return {"version": __version__, "commit": commit() or None,
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "packs": len(engine.packs), "facts": len(engine.store),
            "snapshot_set": watcher.status() if watcher is not None else {"set": "bundled", "checked_at": None,
                                                                            "error": None},
            "model": model, "datasets": rows}


# ---------------------------------------------------------------- the /try phone


def session_token(environ: dict[str, Any]) -> tuple[str, bool]:
    """The browser's session token from its cookie, or a new one. Returns (token, is_new)."""
    for part in environ.get("HTTP_COOKIE", "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == SESSION_COOKIE and 16 <= len(value) <= 64 and all(c.isalnum() or c in "-_" for c in value):
            return value, False
    return secrets.token_urlsafe(24), True


def session_cookie(token: str, secure: bool) -> str:
    return (f"{SESSION_COOKIE}={token}; Path=/try; Max-Age={SESSION_AGE}; HttpOnly; SameSite=Strict"
            + ("; Secure" if secure else ""))


def _country(data: dict[str, Any]) -> str:
    code = str(data.get("country") or "").upper()
    if code not in COUNTRIES:
        raise ValueError("country is required, one of " + ", ".join(COUNTRIES))
    return code


def _language(data: dict[str, Any]) -> str | None:
    code = str(data.get("language") or "").lower()
    if code in ("", "auto"):
        return None
    if code not in SUPPORTED_LANGUAGES:
        raise ValueError("unknown language " + code)
    return code


def _choose_language(engine: Any, sender: str, language: str | None, picked: Any = None) -> None:
    """A language picked on the phone is the person's choice, as LANG would make it. Picking Automatic again clears
    that choice, so ACE goes back to reading each message's language."""
    if language is None and str(picked or "").lower() != "auto":
        return
    profile = engine.profiles.peek(sender) if language is None else engine.profiles.get_or_create(sender)
    if profile is not None and profile.language != language:
        profile.language = language
        engine.profiles.save(profile)


def log_answer(route: str, channel: str, country: str | None, kind: str, language: str) -> None:
    """One structured log line per answer: what was asked of ACE, never what was said or by whom."""
    if os.environ.get("ACE_ENV") == "production":
        print(json.dumps({"severity": "INFO", "message": "answer", "route": route, "channel": channel,
                          "country": country or "none", "kind": kind, "language": language}), flush=True)


def citations(reply: Any) -> list[dict[str, Any]]:
    return [{"fact_id": c.fact_id, "source": c.source, "source_url": c.source_url, "licence": c.licence,
             "date": c.date, "review_status": c.review_status} for c in reply.citations]


def try_ussd(app: Any, data: dict[str, Any], token: str) -> dict[str, Any]:
    country = _country(data)
    sender = web_sender(country, token)
    _choose_language(app.engine, sender, _language(data), data.get("language"))
    text = str(data.get("text") or "")
    if len(text) > 400:
        raise ValueError("text is too long")
    screen = app.ussd.respond(sender, text, f"try-{token[:8]}")
    lang = app.engine.language_for(sender)
    return {"screen": screen[4:], "end": screen.startswith("END"), "chars": len(screen),
            "limit": encoding.ussd_limit(lang), "language": lang}


def try_message(app: Any, data: dict[str, Any], token: str) -> dict[str, Any]:
    country = _country(data)
    sender = web_sender(country, token)
    language = _language(data)
    channel = {"sms": Channel.SMS, "whatsapp": Channel.WHATSAPP, "rcs": Channel.RCS,
               "voice": Channel.VOICE}.get(str(data.get("channel") or "sms").lower())
    if channel is None:
        raise ValueError("channel must be sms, whatsapp, rcs or voice")
    text = " ".join(str(data.get("text") or "").split())
    if not text:
        raise ValueError("text is required")
    if len(text) > 1000:
        raise ValueError("text is too long")
    _choose_language(app.engine, sender, language, data.get("language"))
    reply = app.engine.handle(Message(channel=channel, sender=sender, text=text, language=language))
    log_answer("/try/message", channel.value, country, reply.kind.value, reply.language)
    out = reply.to_dict()
    out["citations"] = citations(reply)
    out["preview"] = reply.language != "en"
    if channel is Channel.SMS:
        segments = app.sms.render(reply)
        out["segments"] = segments
        out["encoding"] = "GSM-7" if all(encoding.is_gsm7(s) for s in segments) else "UCS-2"
    elif channel is Channel.RCS:
        from .channels import rcs as rcs_channel

        out["chips"] = rcs_channel.chips_for(reply)
    elif channel is Channel.WHATSAPP:
        out["messages"] = app.wa.render(reply)
    else:
        out["voice"] = voice_line(reply.language)
    out["emergency"] = reply.kind is ReplyKind.EMERGENCY
    return out


def try_forget(app: Any, data: dict[str, Any], token: str) -> dict[str, Any]:
    """Delete this browser's session in every country, not only the one on screen."""
    _country(data)
    for code in COUNTRIES:
        app.engine.profiles.forget(web_sender(code, token))
    return {"forgotten": True}


def json_script(value: Any) -> str:
    """JSON safe to place inside a script element."""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def paused_page() -> bytes:
    return page_simple("ACE is paused", "This demonstration has reached its spending limit for the month and is paused "
                       "until the 1st. ACE is open source: you can run your own copy from the repository.")


def page_simple(title: str, text: str) -> bytes:
    body = (f'<section class="band"><div class="wrap narrow"><h1>{html.escape(title)}</h1>'
            f'<p class="lead">{html.escape(text)}</p><p><a class="button" '
            'href="https://github.com/tbrunoh/african-context-engine">ACE on GitHub</a></p></div></section>')
    out = _asset("layout.html").replace("{{CONTENT}}", body)
    for key, value in {"TITLE": html.escape(title), "DESCRIPTION": html.escape(text), "CANONICAL": SITE_ORIGIN + "/",
                       "PAGE": "notice", "VERSION": __version__, "COMMIT": html.escape(commit() or "local build"),
                       "YEAR": str(datetime.now(timezone.utc).year)}.items():
        out = out.replace("{{" + key + "}}", value)
    return out.encode("utf-8")


def robots() -> bytes:
    return f"User-agent: *\nAllow: /\nDisallow: /try/\nSitemap: {SITE_ORIGIN}/sitemap.xml\n".encode()


def sitemap() -> bytes:
    urls = "".join(f"<url><loc>{SITE_ORIGIN}{p}</loc></url>" for p in PAGES)
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>').encode()
