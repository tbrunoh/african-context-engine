#!/usr/bin/env python3
"""Smoke suite for a deployed ACE. Standard library only.

    python3 deploy/gcp/smoke.py https://ace.korext.com [--header "x-ace-candidate: SECRET"]

Checks health and version, every page, the /try phone, an emergency message in every one of ACE's 32 languages from
a country that offers it, the USSD main menu, one call per decision service, MCP's tool list, security headers and
the HTTP redirect. Exits 1 on any failure.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAILURES: list[str] = []


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None


def request(base: str, path: str, headers: dict[str, str], body: dict | None = None,
            extra: dict[str, str] | None = None, follow: bool = True) -> tuple[int, dict[str, str], bytes]:
    data = json.dumps(body).encode() if body is not None else None
    h = {**headers, **(extra or {})}
    if data is not None:
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(base + path, data=data, headers=h, method="POST" if data is not None else "GET")
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=30) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read()


def check(ok: bool, what: str) -> None:
    print(("ok    " if ok else "FAIL  ") + what)
    if not ok:
        FAILURES.append(what)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--header", action="append", default=[], help="extra header, for example the candidate header")
    ap.add_argument("--commit", default=None, help="the commit the release built: the site and MCP must both run it")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    headers = dict(h.split(": ", 1) for h in args.header)
    headers["User-Agent"] = "ace-smoke/1"

    code, _, body = request(base, "/healthz", headers)
    health = json.loads(body) if code == 200 else {}
    check(health.get("status") == "ok" and health.get("facts", 0) > 0, f"/healthz: ACE {health.get('version')}")
    if args.commit is not None:  # an empty commit means the release lost it: fail rather than skip the check
        check(bool(args.commit) and bool(health.get("commit")) and args.commit.startswith(str(health.get("commit"))),
              f"the site runs commit {args.commit[:12]}")

    for path in ("/", "/try", "/coverage", "/developers", "/status", "/about", "/static/ace.css", "/static/site.js",
                 "/robots.txt", "/sitemap.xml", "/v1/countries", "/v1/status", "/v1/services"):
        code, h, body = request(base, path, headers)
        check(code == 200, f"GET {path}")
        if path == "/":
            check("content-security-policy" in h and h.get("x-content-type-options") == "nosniff", "security headers")
            check(str(health.get("version", "?")).encode() in body, "the home page names the running version")

    countries = json.loads(request(base, "/v1/countries", headers)[2])
    offered: dict[str, str] = {}
    for c in countries["countries"]:
        for lang in c["languages"]:
            offered.setdefault(lang, c["code"])
    for lang, text in first_red_team_messages().items():
        country = offered.get(lang) or ("NG" if lang in ("en", "pcm") else None)
        if country is None:
            check(False, f"no country offers {lang}")
            continue
        code, _, body = request(base, "/try/message", headers, {"country": country, "language": lang, "channel": "sms",
                                                                "text": text})
        reply = json.loads(body) if code == 200 else {}
        check(reply.get("kind") == "emergency", f"emergency in {lang} from {country}")

    code, _, body = request(base, "/try/ussd", headers, {"country": "KE", "text": ""})
    screen = json.loads(body).get("screen", "") if code == 200 else ""
    check(code == 200 and screen.startswith("ACE") and "1 " in screen, "USSD main menu")

    calls = {"rain_this_week": {"place": "Embu"}, "official_warnings": {"place": "Embu"},
             "nearest_facility": {"place": "Kisumu"}, "market_prices": {"place": "Embu", "food": "maize"},
             "pregnancy_companion": {"weeks": 20}, "pest_check": {"text": "maize leaves with holes and sawdust"}}
    for sid, extra in calls.items():
        code, _, body = request(base, f"/v1/services/{sid}", headers, {"country": "KE", "language": "en", **extra})
        result = json.loads(body) if code == 200 else {}
        # Services whose data is bundled or refreshed by the deployment must answer; prices may be stale, and there may
        # be no warning in force. A gap here means the deployment lost its pack facts or its snapshots.
        allowed = {"market_prices": ("answer", "stale"), "official_warnings": ("answer", "no_match")}.get(sid, ("answer",))
        check(result.get("outcome") in allowed, f"service {sid}: {result.get('outcome')}")

    mcp_headers = {**headers, "Accept": "application/json, text/event-stream"}
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "1"}}}
    code, _, body = request(base, "/mcp", mcp_headers, init)
    check(code == 200 and b"ace-context" in body, "MCP initialize")
    code, _, body = request(base, "/mcp", mcp_headers, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    check(code == 200 and b"ask_ace" in body, "MCP tools/list")
    if args.commit is not None:
        code, _, body = request(base, "/mcp/healthz", headers)
        mcp = json.loads(body) if code == 200 else {}
        check(bool(args.commit) and bool(mcp.get("commit")) and args.commit.startswith(str(mcp.get("commit"))),
              f"MCP runs commit {args.commit[:12]}")

    if base.startswith("https://") and "x-ace-candidate" not in {k.lower() for k in headers}:
        host = base[len("https://"):].split("/")[0]
        code, h, _ = request("http://" + host, "/try?x=1", headers, follow=False)
        check(code in (301, 308) and h.get("location", "") == f"https://{host}/try?x=1",
              "HTTP redirects to the same page on HTTPS, with no port in the address")
        code, h, _ = request(base, "/", headers)
        check("strict-transport-security" in h, "HSTS from the load balancer")

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


def first_red_team_messages() -> dict[str, str]:
    """The first red team message of each language in benchmark/sets/emergency.yaml, read without PyYAML."""
    out: dict[str, str] = {}
    lang = None
    for line in (ROOT / "benchmark" / "sets" / "emergency.yaml").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith((" ", "#")) and line.endswith(":"):
            lang = line[:-1]
        elif lang and line.strip().startswith("- {text:") and lang not in out:
            out[lang] = json.loads(line.split("text:", 1)[1].rsplit(", queue:", 1)[0].strip())
    return out


if __name__ == "__main__":
    sys.exit(main())
