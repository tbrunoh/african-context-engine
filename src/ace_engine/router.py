"""Turn retrieved facts into an answer that fits the channel.

ACE has two answerers and never depends on either one alone:

* ExtractiveComposer (default): deterministic, offline, free. It renders the
  best facts in the person's language and packs them into the channel's
  character budget. It cannot invent anything.
* GroundedGenerator: wraps any language model. The model sees only the
  retrieved facts and must cite them. ACE checks the output: every sentence
  must cite a fact it was given and no new phone numbers may appear. If the
  check fails, the model is slow, or the call errors, ACE falls back to the
  extractive answer. A model can make answers more natural; it can never make
  them less grounded.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from .context.schema import ContextFact
from .text import truncate_words


@dataclass(frozen=True)
class Budget:
    """How much a channel can carry in one reply."""

    max_chars: int
    short: bool          # prefer each fact's short rendering
    max_facts: int = 3


@dataclass
class Composed:
    text: str
    used: list[ContextFact]
    language: str
    generator: str = "extractive"


class ExtractiveComposer:
    name = "extractive"

    def compose(self, facts: list[ContextFact], language: str, budget: Budget) -> Composed:
        parts: list[str] = []
        used: list[ContextFact] = []
        langs: list[str] = []
        for f in facts[: budget.max_facts]:
            text, rendered_in = f.render(language, short=budget.short)
            if parts and len(" ".join([*parts, text])) > budget.max_chars:
                break
            parts.append(text)
            used.append(f)
            langs.append(rendered_in)
        body = truncate_words(" ".join(parts), budget.max_chars)
        return Composed(body, used, langs[0] if langs else language)


class ModelProvider(Protocol):
    name: str

    def generate(self, system: str, prompt: str, timeout_s: float) -> str: ...


SYSTEM_PROMPT = (
    "You are ACE, a local expert service for people in Africa. Answer ONLY from the numbered FACTS. "
    "Write in the requested language, in short plain sentences a farmer or mother can act on. "
    "End every sentence with the number of the fact it comes from in square brackets, like [1]. "
    "Never add advice, numbers, doses, products or phone numbers that are not in the FACTS. "
    "If the FACTS do not answer the question, reply exactly: NO_ANSWER"
)
_CITE = re.compile(r"\[(\d+)\]")
_PHONE_LIKE = re.compile(r"\+?\d[\d ]{2,}\d")


def build_prompt(question: str, facts: list[ContextFact], language: str, max_chars: int) -> str:
    lines = [f"[{i}] {f.render(language)[0]}" for i, f in enumerate(facts, start=1)]
    return ("FACTS:\n" + "\n".join(lines) + f"\n\nLANGUAGE: {language}\nMAXIMUM LENGTH: {max_chars} characters"
            f"\n\nQUESTION: {question}")


def check_grounded(output: str, facts: list[ContextFact], language: str) -> tuple[bool, str, list[int]]:
    """Validate a model answer. Returns (ok, cleaned_text, cited_fact_numbers)."""
    text = output.strip()
    if not text or "NO_ANSWER" in text:
        return False, "", []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?\]])\s+", text) if s.strip()]
    cited: list[int] = []
    for s in sentences:
        nums = [int(n) for n in _CITE.findall(s)]
        if not nums or any(n < 1 or n > len(facts) for n in nums):
            return False, "", []
        cited.extend(n for n in nums if n not in cited)
    allowed = " ".join(f.render(language)[0] + " " + f.claim for f in facts)
    for number in _PHONE_LIKE.findall(_CITE.sub("", text)):
        if number.replace(" ", "") not in allowed.replace(" ", ""):
            return False, "", []
    cleaned = " ".join(_CITE.sub("", text).split()).replace(" .", ".")
    return True, cleaned, cited


class GroundedGenerator:
    """Use a model for fluency, with extractive fallback on any doubt."""

    def __init__(self, provider: ModelProvider, timeout_s: float = 8.0,
                 fallback: ExtractiveComposer | None = None) -> None:
        self.provider = provider
        self.timeout_s = timeout_s
        self.fallback = fallback or ExtractiveComposer()
        self.name = f"grounded:{provider.name}"

    def compose(self, facts: list[ContextFact], language: str, budget: Budget,
                question: str = "") -> Composed:
        chosen = facts[: budget.max_facts]
        try:
            raw = self.provider.generate(SYSTEM_PROMPT, build_prompt(question, chosen, language, budget.max_chars),
                                         self.timeout_s)
        except Exception:  # noqa: BLE001  any provider failure means fall back
            return self.fallback.compose(facts, language, budget)
        ok, text, cited = check_grounded(raw, chosen, language)
        if not ok or len(text) > budget.max_chars * 1.1:
            return self.fallback.compose(facts, language, budget)
        return Composed(text, [chosen[n - 1] for n in cited], language, self.name)


class OpenAICompatibleProvider:
    """Any server that speaks the OpenAI chat completions format: hosted APIs,
    vLLM, Ollama, llama.cpp or a model on a local box. Standard library only.

    Configure with ACE_LLM_BASE_URL, ACE_LLM_MODEL and ACE_LLM_API_KEY.
    """

    def __init__(self, base_url: str | None = None, model: str | None = None,
                 api_key: str | None = None) -> None:
        self.base_url = (base_url or os.environ.get("ACE_LLM_BASE_URL", "")).rstrip("/")
        self.model = model or os.environ.get("ACE_LLM_MODEL", "")
        self.api_key = api_key or os.environ.get("ACE_LLM_API_KEY", "")
        if not self.base_url or not self.model:
            raise ValueError("Set ACE_LLM_BASE_URL and ACE_LLM_MODEL to use a language model")
        self.name = self.model

    def generate(self, system: str, prompt: str, timeout_s: float) -> str:
        body = json.dumps({
            "model": self.model, "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310  operator configured URL
            data = json.loads(resp.read())
        return str(data["choices"][0]["message"]["content"])
