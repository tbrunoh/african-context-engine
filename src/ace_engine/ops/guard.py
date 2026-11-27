"""The spend guard: it keeps the project under its monthly cap ($60 for ace.korext.com).

Cloud Scheduler calls POST /meter every ten minutes. The meter (meter.py) estimates month to date spending from Cloud
Monitoring and picks a level from 0 to 4; the guard then sets every service and the load balancer to that level:

    level 1+  ace-web: ACE_LLM_DISABLED=1, so ACE answers by extraction
    level 2+  ace-web and ace-mcp: ACE_PAUSED=1, every page and the MCP endpoint say the demo is paused until the 1st,
              and no service keeps a warm instance
    level 3+  Cloud Armor denies every request at the edge
    level 4   the forwarding rules are removed

Below a level, its change is undone, so a new month restores the warm instance from ACE_GUARD_MIN_INSTANCES (for
example ace-web=1), the Armor rule and the forwarding rules. The highest level set in a month is kept in
Firestore (spend/guard-YYYY-MM), so a later estimate never lowers it within the month. A budget notification, if
Pub/Sub is ever allowed to carry one, arrives at POST / and runs the meter at once, with the billed amount in US
dollars as a floor under the estimate. ACE_GUARD_ENFORCE=0 measures and logs without changing anything.

    gunicorn "ace_engine.ops.guard:app"     with ACE_GUARD_PROJECT, ACE_GUARD_REGION, ACE_GUARD_SERVICES,
                                            ACE_GUARD_ARMOR, ACE_GUARD_RULES, ACE_GUARD_ADDRESS and ACE_CAP_USD set
"""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from typing import Any

from . import cloudrun, edge, meter


def service_env(level: int, service: str) -> dict[str, str | None]:
    """What a service's environment should be at a level. Only the site uses the model."""
    wanted: dict[str, str | None] = {"ACE_PAUSED": "1" if level >= 2 else None}
    if service == "ace-web":
        wanted["ACE_LLM_DISABLED"] = "1" if level >= 1 else None
    return wanted


def apply(level: int, http: Any, env: dict[str, str]) -> dict[str, Any]:
    """Set the project to a level. Every step checks what is there first, so running it again changes nothing."""
    project, region = env["ACE_GUARD_PROJECT"], env.get("ACE_GUARD_REGION", "africa-south1")
    services = [s for s in env.get("ACE_GUARD_SERVICES", "ace-web,ace-mcp").split(",") if s]
    warm = dict(item.split("=", 1) for item in env.get("ACE_GUARD_MIN_INSTANCES", "").split(",") if "=" in item)
    address = env.get("ACE_GUARD_ADDRESS", "ace-ip")
    changed: dict[str, Any] = {}
    # Opening up runs from the edge inward and closing down from the inside out, so no step exposes a service the
    # level means to keep shut.
    if level < 4 and env.get("ACE_GUARD_RULES"):
        changed["forwarding_rules"] = edge.set_rules(http, project, env["ACE_GUARD_RULES"], address, present=True)
    if level >= 3 and env.get("ACE_GUARD_ARMOR"):
        changed["armor"] = edge.set_armor(http, project, env["ACE_GUARD_ARMOR"], closed=True)
    for service in services:
        floor = 0 if level >= 2 else int(warm.get(service, 0))
        changed[service] = cloudrun.set_env(http, cloudrun.service_name(project, region, service),
                                            service_env(level, service), min_instances=floor)
    if level < 3 and env.get("ACE_GUARD_ARMOR"):
        changed["armor"] = edge.set_armor(http, project, env["ACE_GUARD_ARMOR"], closed=False)
    if level >= 4 and env.get("ACE_GUARD_RULES"):
        changed["forwarding_rules"] = edge.set_rules(http, project, env["ACE_GUARD_RULES"], address, present=False)
    return changed


def run(http: Any = None, env: dict[str, str] | None = None, now: datetime | None = None,
        floor: float = 0.0) -> dict[str, Any]:
    env = env if env is not None else dict(os.environ)
    http = http or cloudrun.session()
    now = now or datetime.now(timezone.utc)
    result = meter.measure(http, env, now=now, floor=floor)
    # The level only rises within a month: the highest one set is kept in Firestore, and a new month starts at 0
    held = meter.read_level(http, env["ACE_GUARD_PROJECT"], now)
    result["estimated_level"], result["level"] = result["level"], max(result["level"], held)
    if env.get("ACE_GUARD_ENFORCE", "1") != "0":
        if result["level"] > held:
            meter.write_level(http, env["ACE_GUARD_PROJECT"], now, result["level"])
        result["changed"] = apply(result["level"], http, env)
    print(json.dumps({"severity": "NOTICE" if result["level"] else "INFO", "message": "spend guard", **result}),
          flush=True)
    return result


def app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
    """POST /meter from Cloud Scheduler, or POST / with a Pub/Sub budget notification. Cloud Run lets only the
    scheduler's and the push subscription's accounts invoke it."""
    try:
        if environ.get("REQUEST_METHOD") != "POST":
            raise ValueError("POST only")
        floor = 0.0
        if environ.get("PATH_INFO", "/") != "/meter":
            length = int(environ.get("CONTENT_LENGTH") or 0)
            envelope = json.loads(environ["wsgi.input"].read(length) or b"{}")
            data = json.loads(base64.b64decode(envelope["message"]["data"]))
            # The billed amount comes in the billing account's currency; only US dollars can floor a cap in dollars
            floor = float(data.get("costAmount", 0)) if data.get("currencyCode", "USD") == "USD" else 0.0
        status, body = "200 OK", json.dumps(run(floor=floor))
    except (KeyError, ValueError) as exc:
        status, body = "400 Bad Request", json.dumps({"error": str(exc)})
    except Exception as exc:  # noqa: BLE001  a failed read or change is logged and retried on the next call
        print(json.dumps({"severity": "ERROR", "message": "spend guard failed", "error": str(exc)}), flush=True)
        status, body = "500 Internal Server Error", json.dumps({"error": "spend guard failed"})
    start_response(status, [("Content-Type", "application/json")])
    return [body.encode()]
