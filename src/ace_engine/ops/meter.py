"""The spend cap. Google Cloud budgets only send alerts, and the organisation that hosts ace.korext.com refuses to let
a budget publish to Pub/Sub, so ACE meters its own spending and stops itself before the cap.

Every ten minutes Cloud Scheduler calls the spend guard at /meter. The meter reads month to date usage from Cloud
Monitoring (Cloud Run time and requests, load balancer requests and bytes, Gemini calls, Firestore operations), prices
it with the list prices below, adds the fixed charges for every hour of the month so far, and asks one question: if
traffic stopped now, could the month still end above the cap? The answer picks a level, and the guard sets the
project to it:

    0  normal
    1  the language model is off; ACE answers by extraction
    2  the site and MCP are paused, and ace-web keeps no warm instance
    3  Cloud Armor turns every request away at the edge, so nothing reaches Cloud Run
    4  the load balancer's forwarding rules are removed, which ends every per request and per hour network charge

Each level is chosen only when spending so far, plus the fixed charges that level still incurs for the rest of the
month, plus a margin for what the next ten minutes could add at that level, stays under the cap. Spending only grows
within a month, so the level only rises; when a new month starts it falls back to 0 and the guard restores
everything, forwarding rules included.

Prices are list prices in USD checked on 27 November 2026, with no free tier counted and the higher of any two
prices taken, so the estimate errs high. ACE's own region, africa-south1, is a Tier 1 Cloud Run region. Gemini is
priced from the tokens ace-web counts for each call (stores.ModelUsage); a call it did not count is priced at the
most one call can cost.

    python -m ace_engine.ops.meter            the estimate and the level, changing nothing (ACE_GUARD_* set)
"""
from __future__ import annotations

import calendar
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

MONITORING = "https://monitoring.googleapis.com/v3"
BILLING_TZ = ZoneInfo("America/Los_Angeles")  # Cloud Billing months follow Pacific time

PRICE = {
    # Cloud Run, request based billing, Tier 1 (cloud.google.com/run/pricing)
    "run_cpu_s": 0.000024, "run_mem_gib_s": 0.0000025, "run_request": 0.40 / 1e6,
    "run_idle_cpu_s": 0.0000025, "run_idle_mem_gib_s": 0.0000025,
    # Load balancing (cloud.google.com/load-balancing/pricing): the first five global forwarding rules, and data
    # processed in each direction
    "lb_rules_hour": 0.025, "lb_gib": 0.008,
    # Internet data transfer, Premium Tier, the highest first band price of any destination
    # (cloud.google.com/vpc/network-pricing)
    "egress_gib": 0.23,
    # Cloud Armor Standard (cloud.google.com/armor/pricing)
    "armor_policy_month": 5.0, "armor_rule_month": 1.0, "armor_request": 0.75 / 1e6,
    # A reserved address is free while forwarding rules hold it, and charged once they are removed
    "address_hour": 0.01,
    # Gemini Flash at or above the highest published Flash list price, because gemini-flash-latest can move to any
    # Flash model (ai.google.dev/gemini-api/docs/pricing, cloud.google.com/vertex-ai/generative-ai/pricing)
    "llm_input_token": 1.65 / 1e6, "llm_output_token": 9.90 / 1e6,
    # Firestore, Cloud Storage and Cloud Scheduler, at or above their highest regional prices
    "firestore_read": 0.06 / 1e5, "firestore_write": 0.18 / 1e5, "firestore_delete": 0.02 / 1e5,
    "storage_op": 0.01 / 1e3, "scheduler_job_month": 0.10,
    # The scheduled refresh runs (about two hours of one vCPU a day), and Artifact Registry, bucket and Firestore
    # storage, secrets, logs and builds: monthly allowances
    "jobs_month": 3.0, "other_month": 2.0,
}
LLM_INPUT_TOKENS = 3000   # the most a call carries: instructions, five facts and a 1,000 character question
LLM_OUTPUT_TOKENS = 1024  # ACE_LLM_MAX_TOKENS, reasoning included
VARIABLE_MARGIN = 1.15
HEADROOM = (6.0, 3.0, 1.5, 0.75, 0.0)  # what each level allows the next ten minutes to add


@dataclass
class Config:
    project: str
    cap: float = 60.0
    warm: dict[str, int] = field(default_factory=lambda: {"ace-web": 1})  # warm instances by service at level 0
    warm_gib: float = 1.0
    armor_rules: int = 2     # the throttle and the default rule; the guard adds one at level 3
    jobs: int = 6            # scheduler jobs
    headroom: tuple[float, ...] = HEADROOM

    @classmethod
    def from_env(cls, env: dict[str, str]) -> Config:
        warm = {k: int(v) for k, v in (i.split("=", 1) for i in env.get("ACE_GUARD_MIN_INSTANCES", "ace-web=1").split(",")
                                       if "=" in i)}
        heads = tuple(float(x) for x in env["ACE_CAP_HEADROOM"].split(",")) if env.get("ACE_CAP_HEADROOM") else HEADROOM
        return cls(project=env["ACE_GUARD_PROJECT"], cap=float(env.get("ACE_CAP_USD") or 60), warm=warm,
                   headroom=(*heads, *HEADROOM[len(heads):])[:5])


def month_start(now: datetime) -> datetime:
    local = now.astimezone(BILLING_TZ)
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def month_end(now: datetime) -> datetime:
    start = month_start(now)
    days = calendar.monthrange(start.year, start.month)[1]
    return start + timedelta(days=days)


def hourly_fixed(cfg: Config, level: int) -> float:
    """What the project costs an hour at a level when no one uses it."""
    rules = cfg.armor_rules + (1 if level >= 3 else 0)
    cost = (PRICE["armor_policy_month"] + PRICE["armor_rule_month"] * rules) / 730
    cost += (PRICE["scheduler_job_month"] * cfg.jobs + PRICE["jobs_month"] + PRICE["other_month"]) / 730
    cost += PRICE["lb_rules_hour"] if level < 4 else PRICE["address_hour"]
    if level < 2:
        cost += sum(cfg.warm.values()) * (PRICE["run_idle_cpu_s"] + PRICE["run_idle_mem_gib_s"] * cfg.warm_gib) * 3600
    return cost


def llm_request_cost() -> float:
    return LLM_INPUT_TOKENS * PRICE["llm_input_token"] + LLM_OUTPUT_TOKENS * PRICE["llm_output_token"]


def variable_cost(usage: dict[str, float]) -> dict[str, float]:
    """Price month to date usage, each line on its own so the log shows where the money went."""
    gib = 1024 ** 3
    lines = {
        "cloud_run": usage.get("run_cpu_s", 0) * PRICE["run_cpu_s"] + usage.get("run_mem_gib_s", 0) * PRICE["run_mem_gib_s"]
        + usage.get("run_requests", 0) * PRICE["run_request"],
        "load_balancer": (usage.get("lb_in_bytes", 0) + usage.get("lb_out_bytes", 0)) / gib * PRICE["lb_gib"],
        "egress": usage.get("lb_out_bytes", 0) / gib * PRICE["egress_gib"],
        "cloud_armor": usage.get("lb_requests", 0) * PRICE["armor_request"],
        # Counted tokens at their price, and any call ACE did not count (the weekly model check, a lost write) at the
        # ceiling of one call
        "gemini": usage.get("llm_input_tokens", 0) * PRICE["llm_input_token"]
        + usage.get("llm_output_tokens", 0) * PRICE["llm_output_token"]
        + max(usage.get("llm_requests", 0) - usage.get("llm_counted", 0), 0) * llm_request_cost(),
        "firestore": usage.get("fs_reads", 0) * PRICE["firestore_read"] + usage.get("fs_writes", 0) * PRICE["firestore_write"]
        + usage.get("fs_deletes", 0) * PRICE["firestore_delete"],
        "storage": usage.get("gcs_ops", 0) * PRICE["storage_op"],
    }
    return {k: round(v * VARIABLE_MARGIN, 4) for k, v in lines.items()}


def estimate(cfg: Config, usage: dict[str, float], now: datetime, floor: float = 0.0) -> dict[str, Any]:
    """Spending so far, and the level that keeps the month under the cap."""
    start, end = month_start(now), month_end(now)
    elapsed = max((now - start).total_seconds() / 3600, 0)
    left = max((end - now).total_seconds() / 3600, 0)
    lines = variable_cost(usage)
    fixed_so_far = hourly_fixed(cfg, 0) * elapsed
    spent = max(fixed_so_far + sum(lines.values()), floor)
    level = 4
    for candidate in range(5):
        if spent + hourly_fixed(cfg, candidate) * left + cfg.headroom[candidate] <= cfg.cap:
            level = candidate
            break
    return {"cap": cfg.cap, "spent": round(spent, 2), "fixed_so_far": round(fixed_so_far, 2), "lines": lines,
            "month_end_at_level": round(spent + hourly_fixed(cfg, level) * left, 2), "level": level,
            "hours_left": round(left, 1)}


# The usage the meter reads: (key, metric type, extra filter). Each is summed over every series since the month began.
METRICS = (
    ("run_cpu_s", "run.googleapis.com/container/cpu/allocation_time", ""),
    ("run_mem_gib_s", "run.googleapis.com/container/memory/allocation_time", ""),
    ("run_requests", "run.googleapis.com/request_count", ""),
    ("lb_requests", "loadbalancing.googleapis.com/https/request_count", ""),
    ("lb_in_bytes", "loadbalancing.googleapis.com/https/request_bytes_count", ""),
    ("lb_out_bytes", "loadbalancing.googleapis.com/https/response_bytes_count", ""),
    ("llm_requests", "serviceruntime.googleapis.com/api/request_count",
     ' AND resource.type="consumed_api" AND resource.labels.service="generativelanguage.googleapis.com"'),
    ("fs_reads", "firestore.googleapis.com/document/read_ops_count", ""),
    ("fs_writes", "firestore.googleapis.com/document/write_ops_count", ""),
    ("fs_deletes", "firestore.googleapis.com/document/delete_ops_count", ""),
    ("gcs_ops", "storage.googleapis.com/api/request_count", ""),
)
def read_usage(http: Any, project: str, start: datetime, end: datetime) -> dict[str, float]:
    """Month to date totals from Cloud Monitoring. Any metric that cannot be read is an error: the run changes
    nothing, and the next one, ten minutes later, reads again. A guess in either direction could set a level the month
    then keeps."""
    usage: dict[str, float] = {}
    seconds = max(int((end - start).total_seconds()), 60)
    for key, metric, extra in METRICS:
        params = {
            "filter": f'metric.type="{metric}"{extra}',
            "interval.startTime": start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "interval.endTime": end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "aggregation.alignmentPeriod": f"{seconds}s",
            "aggregation.perSeriesAligner": "ALIGN_SUM",
            "aggregation.crossSeriesReducer": "REDUCE_SUM",
        }
        total, token = 0.0, None
        try:
            while True:
                if token:
                    params["pageToken"] = token
                resp = http.get(f"{MONITORING}/projects/{project}/timeSeries", params=params, timeout=30)
                resp.raise_for_status()
                body = resp.json()
                for series in body.get("timeSeries", []):
                    for point in series.get("points", []):
                        value = point.get("value", {})
                        total += float(value.get("doubleValue", value.get("int64Value", 0)) or 0)
                token = body.get("nextPageToken")
                if not token:
                    break
        except Exception as exc:  # noqa: BLE001  any failed read is reported, never read as zero
            raise RuntimeError(f"could not read {metric}: {exc}") from exc
        usage[key] = total
    return usage


def read_tokens(http: Any, project: str, now: datetime) -> dict[str, float]:
    """The month's Gemini tokens as ace-web counted them (stores.ModelUsage). No document yet means none counted,
    which prices every call at its ceiling. A failed read raises: pricing every call at its ceiling for one run
    could step the project up a level on a transient error."""
    from ..stores import ModelUsage

    url = (f"https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/spend/"
           f"{ModelUsage.month(now)}")
    resp = http.get(url, timeout=30)
    if getattr(resp, "status_code", 200) == 404:
        return {}
    resp.raise_for_status()
    fields = resp.json().get("fields", {})
    value = lambda name: float(fields.get(name, {}).get("integerValue", 0))  # noqa: E731
    return {"llm_counted": value("calls"), "llm_input_tokens": value("input_tokens"),
            "llm_output_tokens": value("output_tokens")}


def measure(http: Any, env: dict[str, str], now: datetime | None = None, floor: float = 0.0) -> dict[str, Any]:
    cfg = Config.from_env(env)
    now = now or datetime.now(timezone.utc)
    usage = read_usage(http, cfg.project, month_start(now), now)
    usage.update(read_tokens(http, cfg.project, now))
    result = estimate(cfg, usage, now, floor)
    result["usage"] = {k: round(v, 1) for k, v in usage.items()}
    return result


def state_url(project: str, now: datetime) -> str:
    month = now.astimezone(BILLING_TZ).strftime("guard-%Y-%m")
    return f"https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/spend/{month}"


def read_level(http: Any, project: str, now: datetime) -> int:
    """The highest level the guard set this month, so the level never falls within a month. A failed read raises."""
    resp = http.get(state_url(project, now), timeout=30)
    if getattr(resp, "status_code", 200) == 404:
        return 0
    resp.raise_for_status()
    return int(resp.json().get("fields", {}).get("level", {}).get("integerValue", 0))


def write_level(http: Any, project: str, now: datetime, level: int) -> None:
    body = {"fields": {"level": {"integerValue": str(level)},
                       "updated": {"timestampValue": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")}}}
    resp = http.patch(state_url(project, now), json=body, timeout=30)
    resp.raise_for_status()


def main() -> int:
    from . import cloudrun
    print(json.dumps(measure(cloudrun.session(), dict(os.environ)), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
