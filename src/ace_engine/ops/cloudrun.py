"""A small client for the Cloud Run Admin API (v2): read a service and change its environment, which rolls out a
new revision. It uses the default credentials of whatever runs it, so give that account roles/run.developer on the
services it changes, and roles/iam.serviceAccountUser on their runtime accounts."""
from __future__ import annotations

from typing import Any

API = "https://run.googleapis.com/v2"


def session() -> Any:
    import google.auth  # type: ignore[import-not-found]
    from google.auth.transport.requests import AuthorizedSession  # type: ignore[import-not-found]

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return AuthorizedSession(creds)


def service_name(project: str, region: str, service: str) -> str:
    return f"projects/{project}/locations/{region}/services/{service}"


def get_env(http: Any, name: str) -> dict[str, str]:
    svc = http.get(f"{API}/{name}", timeout=30)
    svc.raise_for_status()
    container = svc.json()["template"]["containers"][0]
    return {e["name"]: e.get("value", "") for e in container.get("env", []) if "value" in e}


def set_env(http: Any, name: str, changes: dict[str, str | None], min_instances: int | None = None) -> bool:
    """Set (or, with None, remove) plain environment variables on a service, and optionally its minimum instances.

    Returns True when it changed. The update carries the etag it read, so two writers (the spend guard and the model
    check) can never overwrite each other's change: on a conflict it reads the service again and retries."""
    for _ in range(3):
        svc = http.get(f"{API}/{name}", timeout=30)
        svc.raise_for_status()
        body = svc.json()
        template = body["template"]
        container = template["containers"][0]
        env = container.get("env", [])
        before = {e["name"]: e.get("value") for e in env if "value" in e}
        kept = [e for e in env if e["name"] not in changes]
        kept += [{"name": k, "value": v} for k, v in changes.items() if v is not None]
        after = {e["name"]: e.get("value") for e in kept if "value" in e}
        scaling = template.setdefault("scaling", {})
        same_scale = min_instances is None or int(scaling.get("minInstanceCount", 0)) == min_instances
        if after == before and same_scale:
            return False
        container["env"] = kept
        if min_instances is not None:
            scaling["minInstanceCount"] = min_instances
        template.pop("revision", None)
        update: dict[str, Any] = {"template": template}
        if body.get("etag"):
            update["etag"] = body["etag"]
        resp = http.patch(f"{API}/{name}", json=update, params={"updateMask": "template"}, timeout=60)
        if getattr(resp, "status_code", 200) in (409, 412):
            continue  # someone else changed the service since the read: read it again
        resp.raise_for_status()
        return True
    raise RuntimeError(f"{name} kept changing under the update; try again")
