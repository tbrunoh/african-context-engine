"""The load balancer's edge, for the spend cap: a Cloud Armor rule that turns every request away, and the forwarding
rules that put the site on the internet. Compute Engine API (v1), with the default credentials of whatever runs it;
give that account the aceGuard role that setup.sh creates."""
from __future__ import annotations

from typing import Any

API = "https://compute.googleapis.com/compute/v1"
CLOSE_PRIORITY = 10
CLOSE_NOTE = "ace-guard: the monthly spend cap is reached"


def _ok(resp: Any) -> Any:
    resp.raise_for_status()
    return resp.json() if getattr(resp, "content", b"") else {}


def armor_closed(http: Any, project: str, policy: str) -> bool:
    body = _ok(http.get(f"{API}/projects/{project}/global/securityPolicies/{policy}", timeout=30))
    return any(int(r.get("priority", -1)) == CLOSE_PRIORITY for r in body.get("rules", []))


def set_armor(http: Any, project: str, policy: str, closed: bool) -> bool:
    """Add or remove the rule that denies every request. Returns True when it changed."""
    if armor_closed(http, project, policy) == closed:
        return False
    url = f"{API}/projects/{project}/global/securityPolicies/{policy}"
    if closed:
        rule = {"priority": CLOSE_PRIORITY, "description": CLOSE_NOTE, "action": "deny(403)",
                "match": {"versionedExpr": "SRC_IPS_V1", "config": {"srcIpRanges": ["*"]}}}
        _ok(http.post(f"{url}/addRule", json=rule, timeout=60))
    else:
        _ok(http.post(f"{url}/removeRule", params={"priority": CLOSE_PRIORITY}, timeout=60))
    return True


def parse_rules(spec: str) -> list[tuple[str, str, str, str]]:
    """ace-https-rule=https:ace-https:443,ace-http-rule=http:ace-http:80 → (name, kind, proxy, port) each."""
    out = []
    for item in filter(None, spec.split(",")):
        name, rest = item.split("=", 1)
        kind, proxy, port = rest.split(":")
        if kind not in ("http", "https"):
            raise ValueError(f"forwarding rule {name}: kind must be http or https")
        out.append((name, kind, proxy, port))
    return out


def rule_exists(http: Any, project: str, name: str) -> bool:
    resp = http.get(f"{API}/projects/{project}/global/forwardingRules/{name}", timeout=30)
    if getattr(resp, "status_code", 200) == 404:
        return False
    resp.raise_for_status()
    return True


def set_rules(http: Any, project: str, spec: str, address: str, present: bool) -> list[str]:
    """Create or delete the forwarding rules. Returns the names it changed."""
    changed = []
    base = f"{API}/projects/{project}/global"
    for name, kind, proxy, port in parse_rules(spec):
        if rule_exists(http, project, name) == present:
            continue
        if present:
            target = f"{base}/{'targetHttpsProxies' if kind == 'https' else 'targetHttpProxies'}/{proxy}"
            rule = {"name": name, "IPAddress": f"{base}/addresses/{address}", "IPProtocol": "TCP", "portRange": port,
                    "target": target, "loadBalancingScheme": "EXTERNAL_MANAGED", "networkTier": "PREMIUM"}
            _ok(http.post(f"{base}/forwardingRules", json=rule, timeout=60))
        else:
            _ok(http.delete(f"{base}/forwardingRules/{name}", timeout=60))
        changed.append(name)
    return changed
