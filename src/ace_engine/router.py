"""Model agnostic routing. ACE never depends on one model provider.

A provider is anything that can turn a grounded prompt into text. The router
picks one per task (reasoning, translation, on-device) and always passes the
retrieved context facts, so answers stay grounded and cite their sources.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .context.schema import ContextFact

SYSTEM_PROMPT = (
    "You are ACE, a hyperlocal expert assistant. Answer only from the CONTEXT facts provided. "
    "If the facts do not answer the question, say so plainly and offer to connect the person "
    "to a human expert. Keep answers short and practical, in the person's language. "
    "Cite fact ids in square brackets."
)


class ModelProvider(Protocol):
    name: str

    def generate(self, system: str, prompt: str, language: str | None = None) -> str: ...


@dataclass
class GroundedPrompt:
    system: str
    prompt: str
    fact_ids: list[str]


def build_prompt(question: str, facts: list[ContextFact], language: str | None,
                 history: list[str] | None = None) -> GroundedPrompt:
    lines = [f"[{f.id}] ({f.review_status.value}; source: {f.source}) {f.claim}" for f in facts]
    context = "\n".join(lines) if lines else "(no matching facts)"
    convo = "\n".join(history or [])
    prompt = (f"CONTEXT:\n{context}\n\nRECENT CONVERSATION:\n{convo or '(none)'}\n\n"
              f"LANGUAGE: {language or 'match the question'}\n\nQUESTION: {question}")
    return GroundedPrompt(SYSTEM_PROMPT, prompt, [f.id for f in facts])


class ExtractiveProvider:
    """A deterministic offline provider for tests, demos and no-connectivity fallback.
    It answers with the top facts verbatim and never invents content."""

    name = "extractive"

    def generate(self, system: str, prompt: str, language: str | None = None) -> str:
        context = prompt.split("CONTEXT:\n", 1)[1].split("\n\nRECENT CONVERSATION:", 1)[0]
        if context.strip() == "(no matching facts)":
            return ("I do not have verified local guidance for that yet. "
                    "I can connect you to a human expert.")
        picks = []
        for line in context.splitlines()[:2]:
            fid = line[1:line.index("]")]
            claim = line.split(") ", 1)[1]
            picks.append(f"{claim.rstrip().rstrip('.')} [{fid}].")
        return " ".join(picks)


class Router:
    def __init__(self, providers: dict[str, ModelProvider] | None = None,
                 default_task: str = "reasoning") -> None:
        self.providers = providers or {"reasoning": ExtractiveProvider()}
        self.default_task = default_task

    def generate(self, grounded: GroundedPrompt, language: str | None, task: str | None = None) -> str:
        provider = self.providers.get(task or self.default_task) or self.providers[self.default_task]
        return provider.generate(grounded.system, grounded.prompt, language)
