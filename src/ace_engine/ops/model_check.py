"""The weekly model check. ACE_LLM_MODEL follows Google's gemini-flash-latest alias, which moves to each new Flash
release, so once a week this job asks which model answers, runs ACE's grounding checks through it, and pins ace-web
to the last model that passed if the new one fails. When the alias passes again, it unpins.

    python -m ace_engine.ops.model_check     with ACE_LLM_BASE_URL, ACE_LLM_API_KEY, ACE_GUARD_PROJECT set

A model passes when every answer to a fixed set of questions cites only the facts it was given, stays within the
reply budget, and is in the language asked for: the same check ACE applies to every answer it serves.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from . import cloudrun

ALIAS = "gemini-flash-latest"
QUESTIONS = (("how do I store maize", "en", "+254711000001"), ("Nihifadhi vipi mahindi baada ya mavuno?", "sw", "+254711000001"),
             ("what are pregnancy danger signs", "en", "+233241000001"),
             ("Comment lutter contre la chenille légionnaire ?", "fr", "+221771000001"),
             ("how do I report a scam message", "en", "+254711000001"))


def run_checks(model: str, env: dict[str, str]) -> list[str]:
    """Problems found with one model; empty when it passes."""
    from ..context.store import ContextQuery
    from ..engine import Engine
    from ..router import SYSTEM_PROMPT, Budget, OpenAICompatibleProvider, build_prompt, check_grounded

    provider = OpenAICompatibleProvider(env["ACE_LLM_BASE_URL"], model, env.get("ACE_LLM_API_KEY"),
                                        env.get("ACE_LLM_REASONING_EFFORT") or None)
    engine = Engine.from_packs(Path(__file__).resolve().parents[1] / "context_packs")
    problems = []
    for question, lang, phone in QUESTIONS:
        facts = [s.fact for s in engine.store.query(ContextQuery(text=question, country=engine.country_for(phone),
                                                                 language=lang, limit=3))]
        budget = Budget(max_chars=480, short=False, max_facts=3)
        try:
            raw = provider.generate(SYSTEM_PROMPT, build_prompt(question, facts, lang, budget.max_chars), 10.0)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{question!r}: no answer ({type(exc).__name__})")
            continue
        ok, text, _ = check_grounded(raw, facts, lang)
        if not ok:
            problems.append(f"{question!r}: not grounded in its facts")
        elif len(text) > budget.max_chars * 1.1:
            problems.append(f"{question!r}: {len(text)} characters, over the budget")
    return problems


def resolve(env: dict[str, str]) -> str:
    """The concrete model behind the alias, from the model field of a one word reply; the alias if unknown."""
    import urllib.request

    body = json.dumps({"model": ALIAS, "messages": [{"role": "user", "content": "Reply with: ok"}]}).encode()
    req = urllib.request.Request(env["ACE_LLM_BASE_URL"].rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {env.get('ACE_LLM_API_KEY', '')}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310  operator configured URL
            model = str(json.loads(resp.read()).get("model") or "")
    except Exception:  # noqa: BLE001
        return ALIAS
    return model.removeprefix("models/") or ALIAS


def main(env: dict[str, str] | None = None, http: Any = None) -> int:
    env = env if env is not None else dict(os.environ)
    name = cloudrun.service_name(env["ACE_GUARD_PROJECT"], env.get("ACE_GUARD_REGION", "africa-south1"), "ace-web")
    http = http or cloudrun.session()
    current = cloudrun.get_env(http, name)
    last_good = current.get("ACE_LLM_LAST_GOOD", "")
    problems = run_checks(ALIAS, env)
    if not problems:
        changed = cloudrun.set_env(http, name, {"ACE_LLM_MODEL": ALIAS, "ACE_LLM_LAST_GOOD": resolve(env),
                                                "ACE_LLM_HELD": None})
        outcome = {"model": ALIAS, "passed": True, "changed": changed}
    elif last_good and last_good != ALIAS:
        changed = cloudrun.set_env(http, name, {"ACE_LLM_MODEL": last_good, "ACE_LLM_HELD": None})
        outcome = {"model": ALIAS, "passed": False, "problems": problems, "pinned": last_good, "changed": changed}
    else:  # nothing earlier to pin: switch the model off rather than serve answers that failed the checks
        changed = cloudrun.set_env(http, name, {"ACE_LLM_HELD": "1"})  # the spend guard owns ACE_LLM_DISABLED
        outcome = {"model": ALIAS, "passed": False, "problems": problems, "disabled": True, "changed": changed}
    print(json.dumps({"severity": "NOTICE" if outcome["passed"] else "WARNING", "message": "model check", **outcome}),
          flush=True)
    return 0 if outcome["passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
