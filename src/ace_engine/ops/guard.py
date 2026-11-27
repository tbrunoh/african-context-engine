"""The spend guard. A Google Cloud budget only sends alerts, so this small service acts on them.

The $60 budget publishes to a Pub/Sub topic, which pushes each notification here. At 90% of the budget the guard
turns the language model off on ace-web (ACE_LLM_DISABLED=1), and ACE answers by extraction for the rest of the
month. At 100% it pauses ace-web and ace-mcp (ACE_PAUSED=1): every page and the MCP endpoint say that the demo is
paused until the 1st, and the guard sets each service's minimum instances to zero, so both scale to zero when idle.
When a new month starts and spending falls back under 90%, it undoes both and restores the minimums in
ACE_GUARD_MIN_INSTANCES (for example ace-web=1).

    gunicorn "ace_engine.ops.guard:app"     with ACE_GUARD_PROJECT, ACE_GUARD_REGION and ACE_GUARD_SERVICES set
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any

from . import cloudrun


def decide(cost: float, budget: float) -> dict[str, str | None]:
    """What each service's environment should be for this share of the budget."""
    share = cost / budget if budget else 0.0
    return {"ACE_LLM_DISABLED": "1" if share >= 0.9 else None, "ACE_PAUSED": "1" if share >= 1.0 else None}


def handle(notification: dict[str, Any], http: Any = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    env = env if env is not None else dict(os.environ)
    project, region = env["ACE_GUARD_PROJECT"], env.get("ACE_GUARD_REGION", "africa-south1")
    services = [s for s in env.get("ACE_GUARD_SERVICES", "ace-web,ace-mcp").split(",") if s]
    changes = decide(float(notification.get("costAmount", 0)), float(notification.get("budgetAmount", 0)))
    http = http or cloudrun.session()
    minimums = dict(item.split("=", 1) for item in env.get("ACE_GUARD_MIN_INSTANCES", "").split(",") if "=" in item)
    changed = {}
    for service in services:
        wanted = dict(changes)
        if service != "ace-web":
            wanted.pop("ACE_LLM_DISABLED")  # only the site uses the model
        floor = 0 if changes["ACE_PAUSED"] else int(minimums.get(service, 0))
        changed[service] = cloudrun.set_env(http, cloudrun.service_name(project, region, service), wanted,
                                            min_instances=floor)
    print(json.dumps({"severity": "NOTICE", "message": "spend guard", "cost": notification.get("costAmount"),
                      "budget": notification.get("budgetAmount"), "changes": changes, "changed": changed}), flush=True)
    return {"changes": changes, "changed": changed}


def app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
    """Pub/Sub push endpoint. Cloud Run only lets the push subscription's account invoke it."""
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        envelope = json.loads(environ["wsgi.input"].read(length) or b"{}")
        data = json.loads(base64.b64decode(envelope["message"]["data"]))
        result = handle(data)
        status, body = "200 OK", json.dumps(result)
    except (KeyError, ValueError) as exc:
        status, body = "400 Bad Request", json.dumps({"error": str(exc)})
    start_response(status, [("Content-Type", "application/json")])
    return [body.encode()]
