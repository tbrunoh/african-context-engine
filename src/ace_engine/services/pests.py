"""Pest and disease check: from the crop and what the farmer sees, the likely problem and what to do first.

Every answer comes from sourced pack facts (fall armyworm, maize lethal necrosis, cassava mosaic disease,
banana Xanthomonas wilt, tomato leaf miner). ACE cannot see the crop, so it names the likely problem, gives
the signs to check and the first step, and refers to an extension officer before any spraying.
"""
from __future__ import annotations

import re

from .. import i18n
from ..countries import COUNTRIES
from ..text import fold, token_forms
from .base import LANGS, Answer, Context, Query, Refusal, Result, all_langs, cite_fact, fit, say

CROPS = {
    "maize": {"maize", "corn", "mahindi", "mais"},
    "cassava": {"cassava", "muhogo", "mihogo", "manioc"},
    "banana": {"banana", "bananas", "ndizi", "migomba", "mgomba", "banane", "bananier", "matoke", "plantain"},
    "tomato": {"tomato", "tomatoes", "nyanya", "tomate", "tomates"},
}

# crop -> [(problem id, signs fact, action fact, words that point to it)]
PROBLEMS = {
    "maize": [
        ("fall_armyworm", "africa-maize-fall-armyworm/damage-signs", "africa-maize-fall-armyworm/squash-eggs-larvae",
         {"worm", "worms", "armyworm", "caterpillar", "caterpillars", "larva", "larvae", "holes", "eaten", "sawdust",
          "frass", "whorl", "viwavi", "kiwavi", "viwavijeshi", "funza", "chenille", "chenilles", "trous", "ver", "vers"}),
        ("maize_lethal_necrosis", "africa-crop-pests-diseases/mln-signs", "africa-crop-pests-diseases/mln-action",
         {"yellow", "yellowing", "mottled", "mottling", "dry", "drying", "dead", "necrosis", "mln", "njano", "kukauka",
          "kunyauka", "jaune", "jaunes", "seche", "seches", "necrose", "marbrure"}),
    ],
    "cassava": [
        ("cassava_mosaic", "africa-crop-pests-diseases/cmd-signs", "africa-crop-pests-diseases/cmd-action", set()),
    ],
    "banana": [
        ("banana_xanthomonas_wilt", "africa-crop-pests-diseases/bxw-signs", "africa-crop-pests-diseases/bxw-action", set()),
    ],
    "tomato": [
        ("tomato_leaf_miner", "africa-crop-pests-diseases/tuta-signs", "africa-crop-pests-diseases/tuta-action", set()),
    ],
}

def _widen() -> None:
    """Add every locale's crop and symptom words. Matching is on folded tokens, so the words are folded too."""
    from ..text import tokens as _tokens
    for crop in CROPS:
        CROPS[crop] |= {t for w in i18n.phrases(f"services.pests.CROPS.{crop}", ()) for t in _tokens(w)}
    for crop, options in PROBLEMS.items():
        PROBLEMS[crop] = [(pid, signs, action, set(words) | {t for w in i18n.phrases(f"services.pests.PROBLEMS.{pid}", ())
                                                           for t in _tokens(w)})
                          for pid, signs, action, words in options]


_widen()


def signs_only(text: str) -> str:
    """The pack's short sign text starts with its own label (Armyworm signs:), which the lead-in already says."""
    body = re.sub(r"^[^:.]{1,45}\s?:\s+", "", text, count=1)
    return body[:1].lower() + body[1:] if body[:2] != body[:2].upper() else body


LIKELY = {"en": "This may be {problem}. ACE cannot see your crop, so check these signs:",
          "sw": "Huenda ni {problem}. ACE haioni zao lako, hivyo kagua dalili hizi:",
          "fr": "Il pourrait s'agir de {problem}. ACE ne voit pas votre culture, vérifiez ces signes :"}
MAYBE = {"en": "Maybe {problem}.", "sw": "Huenda ni {problem}.", "fr": "Peut-être {problem}."}
REFER = {"en": "Ask an extension officer to confirm before you spray.",
         "sw": "Muulize afisa ugani athibitishe kabla ya kunyunyizia dawa.",
         "fr": "Demandez à un agent de vulgarisation de confirmer avant de traiter."}
NAMES = {
    "fall_armyworm": {"en": "fall armyworm", "sw": "viwavijeshi vamizi", "fr": "la chenille légionnaire d'automne"},
    "maize_lethal_necrosis": {"en": "maize lethal necrosis", "sw": "ugonjwa wa MLN", "fr": "la nécrose létale du maïs"},
    "cassava_mosaic": {"en": "cassava mosaic disease", "sw": "batobato ya muhogo", "fr": "la mosaïque du manioc"},
    "banana_xanthomonas_wilt": {"en": "banana Xanthomonas wilt", "sw": "mnyauko bakteria wa migomba",
                                "fr": "le flétrissement bactérien du bananier"},
    "tomato_leaf_miner": {"en": "tomato leaf miner (Tuta absoluta)", "sw": "Tuta absoluta",
                          "fr": "la mineuse de la tomate (Tuta absoluta)"},
}
ASK = {"en": "Which crop, and what do you see? For example: maize leaves with holes and sawdust.",
       "sw": "Zao gani, na unaona nini? Kwa mfano: majani ya mahindi yenye matundu na vumbi kama la mbao.",
       "fr": "Quelle culture, et que voyez-vous ? Par exemple : feuilles de maïs trouées avec de la sciure."}
UNKNOWN = {"en": "ACE can check maize, cassava, banana and tomato so far. For other crops, ask an extension officer.",
           "sw": "Kwa sasa ACE inaweza kukagua mahindi, muhogo, ndizi na nyanya. Kwa mazao mengine, muulize afisa ugani.",
           "fr": "ACE vérifie pour l'instant le maïs, le manioc, la banane et la tomate. Pour d'autres cultures, demandez "
                 "à un agent de vulgarisation."}


def crop_in(text: str) -> str | None:
    words = token_forms(text)
    return next((crop for crop, names in CROPS.items() if words & names), None)


class PestService:
    id = "pest_check"
    title = {"en": "Crop problem check", "sw": "Kagua tatizo la zao", "fr": "Problème de culture",
             "pt": "Problema na cultura", "ar": "مشكلة في المحصول", "am": "የሰብል ችግር", "om": "Rakkoo midhaanii",
             "so": "Dhibaatada dalagga"}
    countries = frozenset(COUNTRIES)
    connectors = ()

    def coverage(self, country: str, ctx: Context) -> tuple[bool, str]:
        return True, "maize, cassava, banana and tomato, from sourced packs"

    def answer(self, q: Query, ctx: Context) -> Result:
        crop = q.params.get("crop") or crop_in(q.text)
        if crop is None:
            asked_other = bool(q.params.get("crop_text"))
            return Refusal(self.id, "no_match" if asked_other else "needs_crop",
                           all_langs(UNKNOWN if asked_other else ASK))
        options = PROBLEMS[crop]
        words = token_forms(q.text)
        scored = sorted(options, key=lambda p: -len(words & p[3]))
        problem, signs_id, action_id, _ = scored[0]
        signs = ctx.store.get(signs_id) if ctx.store is not None else None
        action = ctx.store.get(action_id) if ctx.store is not None else None
        if signs is None or action is None:
            return Refusal(self.id, "gap", all_langs(UNKNOWN))
        text = {}
        for lang in LANGS:
            act = action.render(lang, short=True)[0]
            refers = any(w in fold(act) for w in ("extension", "agriculture office", "ugani", "ofisi ya kilimo",
                                                  "service agricole", "agent agricole", "vulgarisation"))
            refer = "" if refers else say(REFER, lang)
            if q.max_chars < 300:  # USSD and short SMS: the likely problem and the first step come first
                pieces = [f"{say(MAYBE, lang, problem=NAMES[problem][lang])} {act}", refer]
            else:
                lead = say(LIKELY, lang, problem=NAMES[problem][lang])
                lead = lead.replace(" de le ", " du ") if lang == "fr" else lead
                pieces = [lead, signs_only(signs.render(lang, short=True)[0]),
                          act, refer]
            text[lang] = fit(pieces, q.max_chars)
        ambiguous = len(options) > 1 and len(words & scored[0][3]) == len(words & scored[1][3])
        return Answer(self.id, text, [cite_fact(signs), cite_fact(action)],
                      confidence="low" if ambiguous else "medium", next_step=all_langs(REFER),
                      data={"crop": crop, "problem": problem, "alternatives": [p[0] for p in scored[1:]]})


i18n.localize("services.pests", globals(), ("LIKELY", "MAYBE", "REFER", "NAMES", "ASK", "UNKNOWN"))
