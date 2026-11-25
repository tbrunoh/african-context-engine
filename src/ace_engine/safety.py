"""The safety rail: spot danger first, answer with numbers people can call.

The rail runs before retrieval and before any model. When a message signals
an emergency, ACE does not try to be clever. It replies at once with the
verified numbers for that kind of emergency, taken from the loaded emergency
pack, in the person's language, and raises a handoff for a human.

Triggers are phrase rules, deliberately simple and auditable. A rule fires
when every one of its groups has at least one phrase present, so "pregnant"
plus "bleeding" fires the maternal rule while "bleeding" alone fires the
general urgent rule.

IMPORTANT: the starter rules cover English, Swahili and French in this file and every added language through
its locale file (ace_engine/locales), and were written
from WHO guidance and national helpline guidance. Every deployment must have them reviewed by
clinicians and fluent speakers for each language it serves, and should add a
classifier on top. Keyword rules are a floor, not a ceiling.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

from . import i18n
from .context.schema import Contact, ContextFact
from .text import contains_phrase

# Groups of phrases. A rule is a tuple of groups; all groups must match.
PREGNANCY = ("pregnant", "pregnancy", "expecting", "months pregnant", "mjamzito", "ujauzito", "mimba",
             "nina mimba", "ana mimba", "enceinte", "grossesse")
POSTPARTUM = ("gave birth", "just delivered", "after delivery", "after birth", "amejifungua", "nimejifungua",
              "baada ya kujifungua", "accouche", "vient d accoucher", "apres l accouchement")
MATERNAL_DANGER = ("bleeding", "fits", "convulsion", "convulsions", "seizure", "blurred vision",
                   "severe headache", "baby not moving", "baby stopped moving", "not kicking", "water broke",
                   "damu", "degedege", "kifafa", "kichwa kinauma sana", "maumivu makali", "haoni vizuri",
                   "mtoto hachezi", "hachezi tumboni", "saigne", "saignement", "saignements", "sang",
                   "vision trouble", "maux de tete violents", "mal de tete severe", "le bebe ne bouge plus",
                   "bebe ne bouge pas", "perte des eaux", "poche des eaux")
URGENT = ("not breathing", "cannot breathe", "can't breathe", "difficulty breathing", "unconscious",
          "collapsed", "fainted", "convulsion", "convulsions", "seizure", "having fits", "heavy bleeding",
          "bleeding heavily", "chest pain", "snake bite", "snakebite", "bitten by a snake", "snake bit", "snake has bitten",
          "severe burn",
          "hapumui", "anashindwa kupumua", "amezimia", "amepoteza fahamu", "kupoteza fahamu", "degedege",
          "kutokwa na damu nyingi", "damu nyingi", "maumivu ya kifua", "ameumwa na nyoka", "kuumwa na nyoka",
          "ameng'atwa na nyoka",
          "ne respire plus", "ne respire pas", "respire mal", "inconscient", "inconsciente", "evanoui", "evanouie",
          "convulse", "saigne beaucoup", "hemorragie", "douleur a la poitrine", "douleur thoracique",
          "morsure de serpent", "mordu par un serpent", "mordue par un serpent", "serpent a mordu",
          "brulure grave")
POISON_ACT = ("swallowed", "drank", "ate", "amekunywa", "amemeza", "alikunywa", "alimeza", "amekula",
              "a avale", "avale", "a bu", "a mange")
POISON_WHAT = ("poison", "pesticide", "insecticide", "chemical", "chemicals", "rat poison", "paraffin",
               "kerosene", "bleach", "jik", "sumu", "dawa ya wadudu", "dawa ya panya", "mafuta taa",
               "produit chimique", "mort aux rats", "petrole", "eau de javel", "javel")
POISONED = ("poisoned", "poisoning", "amewekewa sumu", "amekunywa sumu", "amemeza sumu", "sumu ya panya",
            "empoisonne", "empoisonnee", "empoisonnement", "intoxication", "intoxique", "intoxiquee")
GBV = ("raped", "rape", "sexually assaulted", "assaulted me", "beats me", "beating me", "he hit me",
       "my husband beats", "domestic violence", "threatened to kill me", "nimebakwa", "amebakwa", "kubakwa",
       "ananipiga", "amenipiga", "mume wangu ananipiga", "dhuluma za kijinsia", "ukatili wa kijinsia",
       "viol", "violee", "agression sexuelle", "agressee sexuellement", "mon mari me bat", "il me bat",
       "il me frappe", "m a frappee", "violence conjugale", "violences conjugales", "violence domestique",
       "menace de me tuer", "violences basees sur le genre")
CHILD = ("child", "my daughter", "my son", "girl", "boy", "mtoto", "msichana", "mvulana", "binti",
         "enfant", "ma fille", "mon fils", "fillette", "garcon")
CHILD_HARM = ("defiled", "defilement", "abused", "abuse", "molested", "touched", "beaten", "married off",
              "amenajisiwa", "unajisi", "ananyanyaswa", "amenyanyaswa", "anapigwa", "kuolewa kwa lazima",
              "abuse", "abusee", "maltraite", "maltraitee", "agresse", "agressee", "battu", "battue",
              "mariee de force", "mariage force", "attouchements")
SELF_HARM = ("kill myself", "end my life", "suicide", "suicidal", "want to die", "better off dead",
             "hurt myself", "harm myself", "kujiua", "nataka kufa", "kujitoa uhai", "kujiumiza",
             "sitaki kuishi", "me suicider", "je vais me tuer", "je veux mourir", "mettre fin a mes jours",
             "en finir avec la vie", "me faire du mal", "je ne veux plus vivre")

# Every added language widens these groups through its locale file. Widening only adds phrases.
PREGNANCY = i18n.phrases("safety.PREGNANCY", PREGNANCY)
POSTPARTUM = i18n.phrases("safety.POSTPARTUM", POSTPARTUM)
MATERNAL_DANGER = i18n.phrases("safety.MATERNAL_DANGER", MATERNAL_DANGER)
URGENT = i18n.phrases("safety.URGENT", URGENT)
POISON_ACT = i18n.phrases("safety.POISON_ACT", POISON_ACT)
POISON_WHAT = i18n.phrases("safety.POISON_WHAT", POISON_WHAT)
POISONED = i18n.phrases("safety.POISONED", POISONED)
GBV = i18n.phrases("safety.GBV", GBV)
CHILD = i18n.phrases("safety.CHILD", CHILD)
CHILD_HARM = i18n.phrases("safety.CHILD_HARM", CHILD_HARM)
SELF_HARM = i18n.phrases("safety.SELF_HARM", SELF_HARM)

DEFAULT_RULES: dict[str, tuple[tuple[str, ...], ...]] = {
    # Order matters: the first queue whose rule fires wins.
    "self_harm": ((*SELF_HARM,),),
    "maternal": ((*PREGNANCY, *POSTPARTUM), MATERNAL_DANGER),
    "poisoning": ((*POISONED,),),
    "poisoning_act": (POISON_ACT, POISON_WHAT),
    "child_protection": (CHILD, CHILD_HARM),
    "gbv": ((*GBV,),),
    "health_urgent": ((*URGENT,),),
}
_QUEUE_ALIASES = {"poisoning_act": "poisoning"}


@dataclass
class SafetyDecision:
    escalate: bool
    queue: str | None = None
    matched: list[str] = field(default_factory=list)


class EscalationPolicy:
    def __init__(self, rules: dict[str, tuple[tuple[str, ...], ...]] | None = None) -> None:
        self.rules = rules or DEFAULT_RULES

    def check(self, text: str) -> SafetyDecision:
        if not text.strip():
            return SafetyDecision(False)
        for queue, groups in self.rules.items():
            hits: list[str] = []
            for group in groups:
                found = next((p for p in group if contains_phrase(text, p)), None)
                if found is None:
                    break
                hits.append(found)
            else:
                return SafetyDecision(True, _QUEUE_ALIASES.get(queue, queue), hits)
        return SafetyDecision(False)


class HandoffSink(Protocol):
    """Where escalations go: a nurse helpdesk, an extension officer queue, a ticketing system."""

    def raise_handoff(self, queue: str, person_key: str, text: str, channel: str) -> None: ...


@dataclass
class InMemoryHandoffs:
    events: list[dict[str, str]] = field(default_factory=list)

    def raise_handoff(self, queue: str, person_key: str, text: str, channel: str) -> None:
        self.events.append({"queue": queue, "person": person_key, "text": text, "channel": channel})


# What ACE says for each queue. {numbers} is filled from the emergency pack.
OPENERS: dict[str, dict[str, str]] = {
    "self_harm": {
        "en": "I am really sorry you are feeling this way. You deserve support right now. {numbers}",
        "sw": "Pole sana kwa unavyojisikia. Unastahili msaada sasa hivi. {numbers}",
        "fr": "Je suis vraiment désolé que vous vous sentiez ainsi. Vous méritez de l'aide maintenant. {numbers}",
    },
    "maternal": {
        "en": "This could be a pregnancy emergency. Go to the nearest health facility now. {numbers}",
        "sw": "Hii inaweza kuwa dharura ya ujauzito. Nenda kituo cha afya kilicho karibu sasa. {numbers}",
        "fr": "Cela peut être une urgence de grossesse. Allez au centre de santé le plus proche maintenant. {numbers}",
    },
    "poisoning": {
        "en": "This sounds like poisoning. Get medical help now and take the container with you. {numbers}",
        "sw": "Hii inaonekana kuwa sumu. Tafuta msaada wa matibabu sasa na ubebe chombo cha sumu. {numbers}",
        "fr": "Cela ressemble à un empoisonnement. Obtenez une aide médicale maintenant et emportez le produit. {numbers}",
    },
    "child_protection": {
        "en": "A child may be in danger. Please get help now. {numbers}",
        "sw": "Mtoto anaweza kuwa hatarini. Tafadhali tafuta msaada sasa. {numbers}",
        "fr": "Un enfant est peut-être en danger. Obtenez de l'aide maintenant. {numbers}",
    },
    "gbv": {
        "en": "I am sorry this is happening. You can get help now. {numbers}",
        "sw": "Pole kwa yanayokupata. Unaweza kupata msaada sasa. {numbers}",
        "fr": "Je suis désolé que cela vous arrive. Vous pouvez obtenir de l'aide maintenant. {numbers}",
    },
    "health_urgent": {
        "en": "This sounds urgent. Get medical help now. {numbers}",
        "sw": "Hii inaonekana ya dharura. Tafuta msaada wa matibabu sasa. {numbers}",
        "fr": "Cela semble urgent. Obtenez une aide médicale maintenant. {numbers}",
    },
}
# The verb goes where the language puts it: before the numbers here, after them in Amharic.
CALL_WORD = {"en": "Call {numbers}", "sw": "Piga {numbers}", "fr": "Appelez le {numbers}"}
OR_WORD = {"en": "or", "sw": "au", "fr": "ou"}
EMERGENCY_WORD = {"en": "emergency", "sw": "dharura", "fr": "urgence"}
FALLBACK_NUMBERS = {
    "en": "Call your local emergency number or go to the nearest health facility.",
    "sw": "Piga nambari ya dharura ya eneo lako au nenda kituo cha afya kilicho karibu.",
    "fr": "Appelez le numéro d'urgence local ou allez au centre de santé le plus proche.",
}


i18n.localize("safety", globals(), ("OPENERS", "CALL_WORD", "OR_WORD", "EMERGENCY_WORD", "FALLBACK_NUMBERS"))


def contacts_for(queue: str, facts: Iterable[ContextFact], country: str | None = None) -> list[Contact]:
    """Every distinct contact that serves a queue, emergency numbers first."""
    seen: dict[str, Contact] = {}
    for f in facts:
        if country and f.scope.countries and country.upper() not in f.scope.countries:
            continue
        for c in f.contacts:
            if queue in c.queues and c.number not in seen:
                seen[c.number] = c
    return sorted(seen.values(), key=lambda c: (0 if "emergency" in c.queues else 1, len(c.number)))


def format_numbers(contacts: list[Contact], language: str) -> str:
    lang = language if language in CALL_WORD else "en"
    if not contacts:
        return FALLBACK_NUMBERS[lang]
    emergency = [c.number for c in contacts if "emergency" in c.queues]
    others = [c for c in contacts if "emergency" not in c.queues]
    parts = []
    if emergency:
        parts.append(f" {OR_WORD[lang]} ".join(emergency) + f" ({EMERGENCY_WORD[lang]})")
    parts.extend(f"{c.number} ({c.label})" for c in others)
    return call_line(", ".join(parts), lang)


SENTENCE_END = {"am": "።"}


def call_line(numbers: str, language: str) -> str:
    """Call 112, 999. in the person's language, with the verb where that language puts it (Amharic: last)."""
    lang = language if language in CALL_WORD else "en"
    return CALL_WORD[lang].format(numbers=numbers) + SENTENCE_END.get(lang, ".")


def emergency_text(queue: str, contacts: list[Contact], language: str) -> str:
    lang = language if language in CALL_WORD else "en"
    opener = OPENERS.get(queue, OPENERS["health_urgent"])[lang]
    return opener.format(numbers=format_numbers(contacts, lang))
