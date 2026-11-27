"""One factory for every deployment: build ACE's engine, stores and senders from the environment.

    gunicorn --workers 1 --threads 8 "ace_engine.app:create_app()"

create_app() reads these settings, and refuses to start in production with anything unsafe:

    ACE_ENV=production        production checks: a real ACE_PSEUDONYM_SALT, and every sender's webhook secret
    ACE_PSEUDONYM_SALT        the secret behind every profile key (required in production, never the development salt)
    ACE_PUBLIC=1              a public demonstration: the /try phone, no phone numbers trusted from the API, TIP off
    ACE_PROFILE_STORE         memory (default) or firestore
    ACE_HANDOFFS              memory (default) or count: escalations counted by queue, country and channel, no text
    ACE_SNAPSHOT_BASE         a folder of published snapshot sets (see ace_engine.snapshots.manifest); checked every
                              ACE_SNAPSHOT_INTERVAL seconds (default 300). Without it, the bundled snapshots serve
    ACE_TIPS=off              switch TIP off
    ACE_LLM_BASE_URL, ACE_LLM_MODEL, ACE_LLM_API_KEY, ACE_LLM_REASONING_EFFORT, ACE_LLM_TIMEOUT
                              a language model that may only rephrase cited facts; never used for USSD or voice
    ACE_LLM_DISABLED=1        switch the model off without removing its settings (the spend guard sets this)
    ACE_LLM_HELD=1            the model check found no model that passes: the model stays off until one does
    ACE_PAUSED=1              answer every page with a short notice that the demo is paused (the spend guard sets this)
    AT_USERNAME, AT_API_KEY   send SMS through Africa's Talking (needs ACE_WEBHOOK_SECRET in production)
    WHATSAPP_TOKEN            send WhatsApp replies (needs WHATSAPP_APP_SECRET in production)
    RBM_AGENT_ID              send RCS replies (needs RBM_CLIENT_TOKEN in production)
"""
from __future__ import annotations

import logging
import os
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .engine import Engine, EngineConfig
from .identity import DEV_SALT

log = logging.getLogger("ace.app")


class UnsafeConfig(RuntimeError):
    """A setting that must not reach production."""


def _on(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _off(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "").strip().lower() in ("0", "false", "no", "off")


def check_production(env: Mapping[str, str]) -> list[str]:
    """Every reason a production deployment must not start."""
    problems = []
    salt = env.get("ACE_PSEUDONYM_SALT", "")
    if not salt or salt == DEV_SALT or len(salt) < 32:
        problems.append("ACE_PSEUDONYM_SALT must be a secret of at least 32 characters, not the development salt")
    if env.get("AT_API_KEY") and not env.get("ACE_WEBHOOK_SECRET"):
        problems.append("an SMS sender needs ACE_WEBHOOK_SECRET, so no one else can trigger texts")
    if env.get("WHATSAPP_TOKEN") and not env.get("WHATSAPP_APP_SECRET"):
        problems.append("a WhatsApp sender needs WHATSAPP_APP_SECRET to check Meta's signature")
    if env.get("RBM_AGENT_ID") and not env.get("RBM_CLIENT_TOKEN"):
        problems.append("an RCS sender needs RBM_CLIENT_TOKEN to check Google's signature")
    return problems


def composer_from_env(env: Mapping[str, str], usage: Any = None) -> Any:
    """The grounded model, when one is configured and not switched off; otherwise None (extraction only).
    With usage (stores.ModelUsage), every call's tokens are counted for the spend cap."""
    if (not env.get("ACE_LLM_BASE_URL") or not env.get("ACE_LLM_MODEL") or _on(env, "ACE_LLM_DISABLED")
            or _on(env, "ACE_LLM_HELD")):
        return None
    from .router import GroundedGenerator, OpenAICompatibleProvider

    provider = OpenAICompatibleProvider(env["ACE_LLM_BASE_URL"], env["ACE_LLM_MODEL"], env.get("ACE_LLM_API_KEY"),
                                        env.get("ACE_LLM_REASONING_EFFORT") or None)
    if usage is not None:
        provider.on_usage = usage.record
    return GroundedGenerator(provider, timeout_s=float(env.get("ACE_LLM_TIMEOUT") or 2.0))


def build_engine(env: Mapping[str, str] | None = None, packs: list[Path] | None = None) -> Engine:
    env = os.environ if env is None else env
    from .cli import _pack_roots

    kwargs: dict[str, Any] = {"config": EngineConfig(tips=not (_off(env, "ACE_TIPS") or _on(env, "ACE_PUBLIC")))}
    store = env.get("ACE_PROFILE_STORE", "memory").lower()
    counting = env.get("ACE_HANDOFFS", "").lower() == "count"
    client = None
    if store == "firestore" or (counting and _on(env, "ACE_FIRESTORE_COUNTS")):
        from google.cloud import firestore  # type: ignore[import-not-found]

        client = firestore.Client(database=env.get("ACE_FIRESTORE_DATABASE") or "(default)")
    if store == "firestore":
        from .stores import FirestoreProfileStore

        kwargs["profiles"] = FirestoreProfileStore(client, salt=env.get("ACE_PSEUDONYM_SALT"))
    if counting:
        from .stores import CountingHandoffs

        kwargs["handoffs"] = CountingHandoffs(client)
    usage = None
    if client is not None:
        from .stores import ModelUsage

        usage = ModelUsage(client)
    composer = composer_from_env(env, usage)
    if composer is not None:
        kwargs["composer"] = composer
    return Engine.from_packs(*(packs or _pack_roots(None)), **kwargs)


def create_app(env: Mapping[str, str] | None = None, engine: Engine | None = None, start_threads: bool = True) -> Any:
    """The WSGI application for ace serve, gunicorn or Cloud Run."""
    env = os.environ if env is None else env
    if env.get("ACE_ENV") == "production":
        problems = check_production(env)
        if problems:
            raise UnsafeConfig("refusing to start: " + "; ".join(problems))
    engine = engine or build_engine(env)
    from .server import AceApp

    senders: dict[str, Any] = {}
    if env.get("AT_USERNAME") and env.get("AT_API_KEY"):
        from .channels.sms import AfricasTalkingSms

        senders["sms_sender"] = AfricasTalkingSms()
    if env.get("WHATSAPP_TOKEN"):
        from .channels.whatsapp import WhatsAppCloudSender

        senders["whatsapp_sender"] = WhatsAppCloudSender()
    if env.get("RBM_AGENT_ID"):
        from .channels.rcs import RbmSender

        senders["rcs_sender"] = RbmSender()
    public = _on(env, "ACE_PUBLIC")
    if public or env.get("ACE_TIPS", "").lower() == "off":
        engine.config.tips = False  # an engine passed in, as by ace serve, follows the same rule as build_engine
    app = AceApp(engine, public=public, paused=_on(env, "ACE_PAUSED"), **senders)
    if engine.services is not None and start_threads:
        _start_background(app, engine, env)
    return app


def _start_background(app: Any, engine: Engine, env: Mapping[str, str]) -> None:
    """Warm the facility index, and follow published snapshot sets when the deployment has them."""
    from .services import facility

    def warm(hub: Any) -> None:
        facility.warm(hub.ctx)

    base = env.get("ACE_SNAPSHOT_BASE")
    if base:
        from .snapshots.manifest import SnapshotWatcher

        # Load the published set before the first request, so a new instance never answers from the older set
        # bundled in the image; the facility index then warms off the request path, as for later swaps.
        watcher = SnapshotWatcher(engine, base, float(env.get("ACE_SNAPSHOT_INTERVAL") or 300))
        watcher.check_once()
        watcher.on_swap = warm
        app.watcher = watcher
        watcher.start()
    threading.Thread(target=lambda: warm(engine.services), name="ace-warm", daemon=True).start()
