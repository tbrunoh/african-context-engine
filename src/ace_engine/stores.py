"""Durable state for a deployment on Google Cloud: profiles in Firestore and escalation counts with no text.

Both classes take a Firestore client, so tests pass a fake one and nothing here imports Google libraries until a
deployment asks for them. Install them with pip install "ace-engine[cloud]".

FirestoreProfileStore
    One document per person in the profiles collection, keyed by the same salted HMAC as the store in memory. Each
    message reads the profile once and writes it once, after the reply. No conversation history is kept. Every
    document carries expires_at, 24 hours after its last write; a Firestore TTL policy on that field deletes it, and
    every read ignores a document past its time, because Firestore deletes expired documents within about a day.
    FORGET deletes the document, and nothing written later in the same message brings it back.

CountingHandoffs
    A public demonstration has no one to hand an emergency to, so it counts escalations by queue, country and
    channel, and keeps no words and no person key.
"""
from __future__ import annotations

import json
import threading
from collections import Counter
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from typing import Any

from .identity import Profile, ProfileStore
from .models import Channel, GeoPoint

PROFILE_TTL = timedelta(hours=24)
_SCALARS = ("language", "last_query", "pending_service", "pending_text", "pending_language", "pending_asked",
            "last_service", "opted_out")


def profile_to_doc(profile: Profile, now: datetime | None = None) -> dict[str, Any]:
    """What a profile document holds: only what improves the next answer, and when it expires."""
    now = now or datetime.now(timezone.utc)
    loc = profile.last_location
    return {
        **{name: getattr(profile, name) for name in _SCALARS},
        "last_location": [loc.lat, loc.lon, loc.altitude_m] if loc else None,
        "last_topic": list(profile.last_topic) if profile.last_topic else None,
        "last_fact_ids": list(profile.last_fact_ids),
        "last_sources": list(profile.last_sources),
        "last_place": list(profile.last_place) if profile.last_place else None,
        "channels": [c.value for c in profile.channels],
        "updated_at": now,
        "expires_at": now + PROFILE_TTL,
    }


def profile_from_doc(key: str, doc: dict[str, Any]) -> Profile:
    known = {f.name for f in fields(Profile)}
    profile = Profile(key=key, **{name: doc.get(name) for name in _SCALARS if name in known and name in doc})
    profile.pending_text = profile.pending_text or ""
    profile.opted_out = bool(profile.opted_out)
    profile.pending_asked = bool(profile.pending_asked)
    if doc.get("last_location"):
        lat, lon, alt = (list(doc["last_location"]) + [None])[:3]
        profile.last_location = GeoPoint(lat, lon, alt)
    if doc.get("last_topic"):
        profile.last_topic = tuple(doc["last_topic"])  # type: ignore[assignment]
    if doc.get("last_place"):
        profile.last_place = tuple(doc["last_place"])  # type: ignore[assignment]
    profile.last_sources = list(doc.get("last_sources") or [])
    profile.last_fact_ids = list(doc.get("last_fact_ids") or [])
    profile.channels = [Channel(c) for c in doc.get("channels") or [] if c in {ch.value for ch in Channel}]
    return profile


class FirestoreProfileStore(ProfileStore):
    """Profiles in Firestore, shared by every instance of the service, with no history and a 24 hour life."""

    def __init__(self, client: Any = None, collection: str = "profiles", salt: str | None = None,
                 default_country_code: str | None = None) -> None:
        super().__init__(salt=salt, default_country_code=default_country_code, keep_history=False)
        if client is None:
            from google.cloud import firestore  # type: ignore[import-not-found]

            client = firestore.Client()
        self.client = client
        self.collection = collection
        self._local = threading.local()

    # Each message reads a profile once: the first read is kept for the rest of that message on this thread.
    def _cache(self) -> dict[str, Profile | None]:
        if not hasattr(self._local, "cache"):
            self._local.cache = {}
        return self._local.cache

    def _forgotten(self) -> set[str]:
        if not hasattr(self._local, "forgotten"):
            self._local.forgotten = set()
        return self._local.forgotten

    def begin_request(self) -> None:
        self._local.cache = {}
        self._local.forgotten = set()

    def _doc(self, key: str) -> Any:
        return self.client.collection(self.collection).document(key)

    def _load(self, key: str) -> Profile | None:
        cache = self._cache()
        if key in cache:
            return cache[key]
        snap = self._doc(key).get()
        profile = None
        if snap.exists:
            data = snap.to_dict() or {}
            expires = data.get("expires_at")
            if not (isinstance(expires, datetime) and expires <= datetime.now(timezone.utc)):
                profile = profile_from_doc(key, data)
        cache[key] = profile
        return profile

    def get_or_create(self, number: str) -> Profile:
        key = self.key_for(number)
        profile = self._load(key)
        if profile is None:
            profile = Profile(key=key)
            self._cache()[key] = profile
        self._forgotten().discard(key)
        return profile

    def peek(self, number: str) -> Profile | None:
        return self._load(self.key_for(number))

    def save(self, profile: Profile) -> None:
        cache, forgotten = self._cache(), self._forgotten()
        try:
            if profile.key in forgotten:  # FORGET in this message: never write the profile back
                return
            self._doc(profile.key).set(profile_to_doc(profile))
        finally:  # the message is over: the next one reads fresh state, which another instance may have changed
            cache.pop(profile.key, None)
            forgotten.discard(profile.key)

    def forget(self, number: str) -> bool:
        key = self.key_for(number)
        existed = self._load(key) is not None
        self._doc(key).delete()
        self._cache()[key] = None
        self._forgotten().add(key)
        return existed


class CountingHandoffs:
    """Escalations counted by queue, country and channel, with no text and no person key.

    With a Firestore client, each count is also added to one document a day in the escalation_counts collection,
    so every instance adds to the same totals."""

    def __init__(self, client: Any = None, collection: str = "escalation_counts") -> None:
        self.counts: Counter[tuple[str, str, str]] = Counter()
        self.client = client
        self.collection = collection
        self._lock = threading.Lock()

    def raise_handoff(self, queue: str, person_key: str, text: str, channel: str,
                      country: str | None = None) -> None:
        cell = (queue, country or "none", channel)
        with self._lock:
            self.counts[cell] += 1
        if self.client is not None:
            from google.cloud import firestore  # type: ignore[import-not-found]

            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.client.collection(self.collection).document(day).set(
                {"__".join(cell): firestore.Increment(1)}, merge=True)


class ModelUsage:
    """Gemini tokens counted for the spend cap: one document a month (Pacific time, as Cloud Billing counts) in the
    spend collection, which the spend guard reads. The write runs beside the reply, so it adds no wait."""

    def __init__(self, client: Any, collection: str = "spend") -> None:
        self.client = client
        self.collection = collection

    @staticmethod
    def month(now: datetime | None = None) -> str:
        from zoneinfo import ZoneInfo
        return (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("America/Los_Angeles")).strftime("llm-%Y-%m")

    def record(self, given: int, made: int) -> None:
        threading.Thread(target=self._write, args=(given, made), daemon=True).start()

    def _write(self, given: int, made: int) -> None:
        try:
            from google.cloud import firestore  # type: ignore[import-not-found]

            self.client.collection(self.collection).document(self.month()).set(
                {"calls": firestore.Increment(1), "input_tokens": firestore.Increment(given),
                 "output_tokens": firestore.Increment(made)}, merge=True)
        except Exception as exc:  # noqa: BLE001  the guard then prices the call at its ceiling instead
            print(json.dumps({"severity": "WARNING", "message": "model usage not counted", "error": str(exc)}),
                  flush=True)
