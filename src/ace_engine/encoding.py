"""What fits on a phone screen, by alphabet.

SMS and USSD carry text in one of two alphabets. The GSM 7 bit alphabet holds English, Swahili, Oromo and
Somali, most French and some Portuguese letters: 160 characters per SMS and about 182 per USSD screen. Any
character outside it switches the whole message to UCS-2, which halves the room: 70 characters per SMS and
about 80 per USSD screen. Arabic and Ge'ez script always need UCS-2.

ACE keeps Latin script replies in GSM-7 by folding the few accented letters the alphabet lacks (ã to a, ç to c,
ê to e) and shrinks every budget for Arabic and Amharic, so no reply is cut off by the network.
"""
from __future__ import annotations

import unicodedata

from . import i18n

# GSM 03.38 basic character set. Text outside it is sent as UCS-2.
GSM7 = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
GSM7_EXT = set("^{}\\[~]|€")  # each costs two septets
TYPOGRAPHY = {"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...", " ": " ",
              "«": '"', "»": '"', "ç": "c", "œ": "oe", "Œ": "OE"}

SMS_GSM, SMS_GSM_MULTI = 160, 153
SMS_UCS2, SMS_UCS2_MULTI = 70, 67
USSD_GSM, USSD_UCS2 = 182, 80


def is_gsm7(text: str) -> bool:
    return all(c in GSM7 or c in GSM7_EXT for c in text)


def gsm_fold(text: str) -> str:
    """Keep Latin script text inside GSM-7: typographic marks to plain ones, missing accents removed.

    Letters the alphabet has (é, è, à, ù, ä, ö, ñ, ü) stay as they are. Text in another script is left alone,
    because folding cannot help it: it travels as UCS-2 and its budget is already smaller.
    """
    out = []
    for c in text:
        c = TYPOGRAPHY.get(c, c)
        if len(c) == 1 and c not in GSM7 and c not in GSM7_EXT and c.isalpha():
            base = unicodedata.normalize("NFKD", c)[0]
            c = base if base in GSM7 else c
        out.append(c)
    return "".join(out)


def ussd_limit(lang: str, gsm_limit: int = USSD_GSM) -> int:
    """Characters one USSD screen carries in a language."""
    return round(gsm_limit * USSD_UCS2 / USSD_GSM) if i18n.is_ucs2(lang) else gsm_limit


def sms_limit(lang: str, segments: int = 3) -> int:
    """Characters a reply of this many SMS segments carries in a language."""
    if i18n.is_ucs2(lang):
        return SMS_UCS2 if segments == 1 else SMS_UCS2_MULTI * segments
    return SMS_GSM if segments == 1 else SMS_GSM_MULTI * segments


def scale(max_chars: int, channel: str, lang: str) -> int:
    """A channel budget in GSM characters, scaled to what the language's alphabet carries."""
    if not i18n.is_ucs2(lang) or channel not in ("ussd", "sms", "rcs"):
        return max_chars
    ratio = USSD_UCS2 / USSD_GSM if channel == "ussd" else SMS_UCS2_MULTI / SMS_GSM_MULTI  # RCS falls back to SMS
    return max(40, int(max_chars * ratio))
