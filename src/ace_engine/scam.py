"""Scam Shield: an explained verdict on a suspicious mobile money message or call.

Someone forwards a message they are unsure about. Scam Shield looks for the
warning signs that the operator itself publishes, explains each sign it finds
in plain words, and tells the person what to do, citing the operator's
guidance. It never declares a message safe: the best it says is that it found
no known warning signs.

Each signal maps to a fact id in a mobile money safety pack, so every claim
in the verdict is grounded and citable. Packs for other operators and
countries can reuse the same signal ids.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from .text import contains_phrase, fold


class Verdict(str, Enum):
    LIKELY_SCAM = "likely_scam"
    SUSPICIOUS = "suspicious"
    NO_KNOWN_SIGNS = "no_known_signs"


@dataclass(frozen=True)
class Signal:
    id: str
    weight: int
    fact: str                  # fact id suffix in the mobile money pack
    explain: dict[str, str]    # one line per language


@dataclass
class ScamReport:
    verdict: Verdict
    score: int
    signals: list[Signal] = field(default_factory=list)

    @property
    def fact_ids(self) -> list[str]:
        out: list[str] = []
        for s in self.signals:
            if s.fact not in out:
                out.append(s.fact)
        return out


_PIN = ("pin", "password", "passcode", "secret code", "siri", "nenosiri", "namba ya siri", "nambari ya siri",
        "code secret", "mot de passe", "code pin", "code confidentiel")
_ASK = ("send", "share", "give", "confirm", "enter", "reply with", "tell us", "verify", "tuma", "nitumie",
        "nipe", "tupe", "thibitisha", "weka", "ingiza", "andika", "envoyez", "envoyer", "envoie",
        "donnez", "communiquez", "confirmez", "saisissez", "tapez", "entrez")
_MISTAKE = ("sent by mistake", "sent to you by mistake", "wrong number", "wrongly sent", "send it back",
            "send back", "please refund", "reverse the money", "kimakosa", "nimekosea", "kwa makosa",
            "rudisha", "nirudishie", "nitumie zangu", "par erreur", "renvoyer", "renvoyez", "remboursez",
            "me rembourser")
_DOUBLE = ("registered twice", "double registration", "double registered", "registered two times",
           "imesajiliwa mara mbili", "umesajiliwa mara mbili", "usajili mara mbili")
_PRIZE = ("you have won", "you won", "winner", "congratulations", "lucky draw", "promotion", "bonus",
          "umeshinda", "hongera", "mshindi", "zawadi", "bahati nasibu", "vous avez gagne", "felicitations",
          "gagnant", "tirage au sort", "cadeau")
_URGENT = ("urgent", "immediately", "within 24 hours", "will be blocked", "will be suspended", "deactivated",
           "last warning", "haraka", "sasa hivi", "itafungwa", "itasimamishwa", "itazimwa", "immediatement",
           "sera bloque", "sera bloquee", "sera suspendu", "sera suspendue", "dernier avertissement", "dans 24 heures")
_CLAIMS_OPERATOR = ("safaricom", "m-pesa", "mpesa", "customer care", "customer service", "fuliza", "huduma kwa wateja")
_DIAL = ("dial", "press", "key in", "bonyeza", "piga", "ingiza", "composez", "tapez")
_TLDS = r"com|net|org|info|xyz|ke|co\.ke|za|co\.za|ng|com\.ng|gh|com\.gh|tz|co\.tz|ug|co\.ug|rw|bw|zw|co\.zw|sn|ci|tg"
_LINK = re.compile(rf"(https?://|www\.|bit\.ly|tinyurl|\b[a-z0-9-]+\.({_TLDS})\b)", re.I)
_USSD_CODE = re.compile(r"\*\d{2,4}(\*\d+)*#")
_PHONE = re.compile(r"(?<!\d)(?:\+?254|0)(?:7|1)\d{8}(?!\d)")
_OFFICIAL = {"0722000000", "254722000000", "+254722000000"}
_MPESA_CONFIRMATION = re.compile(r"\bconfirmed\b.*\b(ksh|kes)\s?[\d,]+.*\b(received|sent)\b", re.I | re.S)


SIGNALS: dict[str, Signal] = {s.id: s for s in (
    Signal("asks_for_pin", 3, "never-share-pin", {
        "en": "it asks for your PIN or password",
        "sw": "unaomba PIN au nenosiri lako",
        "fr": "il demande votre code secret ou mot de passe"}),
    Signal("double_registration", 3, "double-registration", {
        "en": "it claims your SIM is registered twice",
        "sw": "unadai SIM yako imesajiliwa mara mbili",
        "fr": "il prétend que votre SIM est enregistrée deux fois"}),
    Signal("refund_request", 3, "sent-by-mistake", {
        "en": "it asks you to send back money sent by mistake",
        "sw": "unakuomba urudishe pesa zilizotumwa kimakosa",
        "fr": "il vous demande de renvoyer de l'argent envoyé par erreur"}),
    Signal("confirmation_from_personal_number", 3, "genuine-sender", {
        "en": "it looks like an M-PESA confirmation but came from a personal number",
        "sw": "unaonekana kama uthibitisho wa M-PESA lakini umetoka nambari ya mtu binafsi",
        "fr": "il ressemble à une confirmation M-PESA mais vient d'un numéro personnel"}),
    Signal("unofficial_operator_number", 2, "official-number", {
        "en": "it claims to be Safaricom but gives a number other than 0722000000",
        "sw": "unadai kuwa Safaricom lakini unatoa nambari tofauti na 0722000000",
        "fr": "il prétend venir de Safaricom mais donne un autre numéro que 0722000000"}),
    Signal("dial_code_instruction", 2, "unknown-callers", {
        "en": "it tells you to dial a code on your phone",
        "sw": "unakuagiza kubonyeza msimbo kwenye simu yako",
        "fr": "il vous demande de composer un code sur votre téléphone"}),
    Signal("prize_or_offer", 2, "prize-messages", {
        "en": "it says you have won something or offers money",
        "sw": "unasema umeshinda au unaahidi pesa",
        "fr": "il dit que vous avez gagné quelque chose ou promet de l'argent"}),
    Signal("link", 1, "fake-links", {
        "en": "it contains a link",
        "sw": "una kiungo cha mtandao",
        "fr": "il contient un lien"}),
    Signal("pressure", 1, "report-333", {
        "en": "it pressures you to act fast",
        "sw": "unakulazimisha kuchukua hatua haraka",
        "fr": "il vous presse d'agir vite"}),
)}


def _any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(contains_phrase(text, p) for p in phrases)


def _is_personal_number(sender: str | None) -> bool:
    if not sender:
        return False
    digits = re.sub(r"[^\d+]", "", sender)
    return bool(_PHONE.fullmatch(digits)) and digits not in _OFFICIAL


def analyse(text: str, sender: str | None = None) -> ScamReport:
    """Score a message. sender is the number or name it came from, when known."""
    found: list[Signal] = []
    folded = fold(text)

    if _any(text, _PIN) and _any(text, _ASK):
        found.append(SIGNALS["asks_for_pin"])
    if _any(text, _DOUBLE):
        found.append(SIGNALS["double_registration"])
    if _any(text, _MISTAKE):
        found.append(SIGNALS["refund_request"])
    if _MPESA_CONFIRMATION.search(text) and _is_personal_number(sender):
        found.append(SIGNALS["confirmation_from_personal_number"])
    numbers = {n for n in (re.sub(r"\D", "", m) for m in _PHONE.findall(folded))}
    numbers = {("0" + n[3:]) if n.startswith("254") else n for n in numbers}
    if _any(text, _CLAIMS_OPERATOR) and (numbers - {"0722000000"} or _is_personal_number(sender)):
        found.append(SIGNALS["unofficial_operator_number"])
    if _USSD_CODE.search(text) and _any(text, _DIAL):
        found.append(SIGNALS["dial_code_instruction"])
    if _any(text, _PRIZE):
        found.append(SIGNALS["prize_or_offer"])
    if _LINK.search(text):
        found.append(SIGNALS["link"])
    if _any(text, _URGENT):
        found.append(SIGNALS["pressure"])

    score = sum(s.weight for s in found)
    if score >= 3:
        verdict = Verdict.LIKELY_SCAM
    elif score >= 1:
        verdict = Verdict.SUSPICIOUS
    else:
        verdict = Verdict.NO_KNOWN_SIGNS
    return ScamReport(verdict, score, found)


HEADLINES = {
    Verdict.LIKELY_SCAM: {"en": "LIKELY SCAM.", "sw": "HUU NI UTAPELI MTARAJIWA.", "fr": "ARNAQUE PROBABLE."},
    Verdict.SUSPICIOUS: {"en": "BE CAREFUL.", "sw": "KUWA MWANGALIFU.", "fr": "SOYEZ PRUDENT."},
    Verdict.NO_KNOWN_SIGNS: {
        "en": "I found no known scam signs, but that does not prove it is safe.",
        "sw": "Sijaona dalili zinazojulikana za utapeli, lakini hilo halithibitishi kuwa ni salama.",
        "fr": "Aucun signe d'arnaque connu, mais cela ne prouve pas que le message est sûr."},
}
SIGNS_LABEL = {"en": "Warning signs:", "sw": "Dalili za hatari:", "fr": "Signes d'alerte :"}
# Kenya: Safaricom's free fraud short code, cited from the mobile money safety pack.
REPORT_LINE = {"en": "Forward it to 333, it is free.", "sw": "Utume kwa 333, ni bure.",
               "fr": "Transférez-le au 333, c'est gratuit."}
# Every other country: no operator pack yet, so ACE gives no number it cannot cite.
GENERIC_REPORT_LINE = {
    "en": "Do not reply or send money. Report it to your provider using the number on its official website or SIM pack.",
    "sw": "Usijibu wala kutuma pesa. Ripoti kwa mtoa huduma wako kupitia nambari iliyo kwenye tovuti yake rasmi.",
    "fr": "Ne répondez pas et n'envoyez pas d'argent. Signalez-le à votre opérateur via le numéro de son site officiel.",
}
NEUTRAL_ADVICE = {
    "en": "Never share your PIN, and check your mobile money balance before acting on any message.",
    "sw": "Usitoe PIN yako, na angalia salio lako la pesa kwa simu kabla ya kufuata ujumbe wowote.",
    "fr": "Ne partagez jamais votre code secret et vérifiez votre solde mobile money avant de suivre un message.",
}
