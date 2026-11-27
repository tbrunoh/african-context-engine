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

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Protocol

from . import i18n
from .context.schema import Contact, ContextFact
from .text import _needle, phrase_in, token_hay

# Groups of phrases. A rule is a tuple of groups; all groups must match.
PREGNANCY = ("pregnant", "pregnancy", "expecting", "months pregnant", "mjamzito", "ujauzito", "mimba",
             "nina mimba", "ana mimba", "enceinte", "grossesse")
POSTPARTUM = ("gave birth", "giving birth", "after giving birth", "just delivered", "after delivery", "after birth",
              "amejifungua", "nimejifungua",
              "baada ya kujifungua", "baada ya kuzaa", "amezaa", "alipojifungua",
              "accouche", "vient d accoucher", "apres l accouchement")
MATERNAL_DANGER = ("bleeding", "fits", "convulsion", "convulsions", "seizure", "blurred vision",
                   "severe headache", "baby not moving", "baby stopped moving", "not kicking", "water broke",
                   "damu", "degedege", "kifafa", "kichwa kinauma sana", "maumivu makali", "haoni vizuri",
                   "mtoto hachezi", "hachezi tumboni", "saigne", "saignement", "saignements", "sang",
                   "vision trouble", "maux de tete violents", "mal de tete severe", "le bebe ne bouge plus",
                   "bebe ne bouge pas", "perte des eaux", "poche des eaux")
URGENT = ("not breathing", "not breathin", "cannot breathe", "can't breathe", "cant breathe", "cant breath",
          "difficulty breathing", "unconscious",
          "collapsed", "fainted", "convulsion", "convulsions", "seizure", "having fits", "heavy bleeding",
          "bleeding heavily", "chest pain", "snake bite", "snakebite", "bitten by a snake", "snake bit",
          "snake has bitten",
          "severe burn", "struggling to breathe", "trouble breathing", "hard to breathe", "short of breath",
          "can not breathe", "cannot breath", "gasping for air", "turning blue", "stopped breathing",
          "stop breathing", "no longer breathing", "passed out", "unconcious", "unconsious",
          "bledding alot", "bleeding alot", "bleeding a lot",
          "hapumui", "anashindwa kupumua", "amezimia", "amepoteza fahamu", "kupoteza fahamu", "degedege",
          "kutokwa na damu nyingi", "damu nyingi", "maumivu ya kifua", "ameumwa na nyoka", "kuumwa na nyoka",
          "ameng'atwa na nyoka", "nimeumwa na nyoka", "nimeng'atwa na nyoka", "hawezi kupumua", "anapumua kwa shida",
          "shida ya kupumua", "damu mingi", "anatoka damu nyingi", "anatoka damu mingi", "amezirai", "hajitambui",
          "ne respire plus", "ne respire pas", "respire mal", "inconscient", "inconsciente", "evanoui", "evanouie",
          "convulse", "saigne beaucoup", "hemorragie", "douleur a la poitrine", "douleur thoracique",
          "morsure de serpent", "mordu par un serpent", "mordue par un serpent", "serpent a mordu",
          "brulure grave", "a du mal a respirer", "difficulte a respirer", "n arrive pas a respirer",
          "n arrive plus a respirer")
POISON_ACT = ("swallowed", "drank", "ate", "omodho", "amodho", "amekunywa", "amemeza", "alikunywa", "alimeza",
              "amekula",
              "a avale", "avale", "a bu", "a mange")
POISON_WHAT = ("poison", "pesticide", "insecticide", "chemical", "chemicals", "rat poison", "paraffin",
               "kerosene", "kerosine", "bleach", "jik", "sumu", "dawa ya wadudu", "dawa ya kuua wadudu",
               "dawa ya kuulia wadudu", "dawa ya magugu", "dawa ya panya", "mafuta taa", "mafuta ya taa",
               "produit chimique", "mort aux rats", "petrole", "eau de javel", "javel")
POISONED = ("poisoned", "poisoning", "overdosed", "took an overdose", "took too many pills", "swallowed all the pills",
            "amewekewa sumu", "amekunywa sumu", "amemeza sumu", "sumu ya panya",
            "empoisonne", "empoisonnee", "empoisonnement", "intoxication", "intoxique", "intoxiquee")
GBV = ("raped", "rape", "sexually assaulted", "assaulted me", "beats me", "beating me", "he hit me",
       "my husband beats", "domestic violence", "threatened to kill me", "hits me", "keeps hitting me",
       "beat me", "nimebakwa", "amebakwa", "kubakwa",
       "ananipiga", "amenipiga", "amenichapa", "ananichapa", "mume wangu ananipiga", "dhuluma za kijinsia",
       "ataniua", "anataka kuniua", "amenitishia kuniua", "ananitishia kuniua", "kunitishia kuniua",
       "ukatili wa kijinsia",
       "viol", "violee", "agression sexuelle", "agressee sexuellement", "mon mari me bat", "il me bat",
       "il me frappe", "m a frappee", "violence conjugale", "violences conjugales", "violence domestique",
       "menace de me tuer", "violences basees sur le genre", "me frappe", "me bat", "me tabasse")
CHILD = ("child", "my daughter", "my son", "girl", "boy", "mtoto", "msichana", "mvulana", "binti",
         "enfant", "ma fille", "mon fils", "fillette", "garcon")
CHILD_HARM = ("defiled", "defilement", "abused", "abuse", "molested", "touched", "beaten", "married off",
              "amenajisiwa", "unajisi", "ananyanyaswa", "amenyanyaswa", "anapigwa", "kuolewa kwa lazima",
              "abuse", "abusee", "maltraite", "maltraitee", "agresse", "agressee", "battu", "battue",
              "mariee de force", "mariage force", "attouchements")
SELF_HARM = ("kill myself", "end my life", "suicide", "suicidal", "want to die", "better off dead", "end it all",
             "take my own life", "no reason to live", "kill my self", "wanna die", "i took too many pills",
             "i swallowed all the pills",
             "hurt myself", "harm myself", "kujiua", "nataka kufa", "kujitoa uhai", "kujiumiza",
             "sitaki kuishi", "me suicider", "je vais me tuer", "je veux mourir", "mettre fin a mes jours",
             "en finir avec la vie", "me faire du mal", "je ne veux plus vivre")

# Fire, drowning, stabbing (and other violent wounds) and road accidents, added in 2.4. Each phrase names the
# emergency itself, so a word with an everyday meaning (fire alone, drowning in work, an accident last year) does not.
FIRE = ("prend feu", "a pris feu", "le feu brule", "on fire", "is on fire", "are on fire", "house is on fire",
        "home is on fire", "car is on fire",
        "shop is on fire", "kitchen is on fire",
        "building is on fire", "school is on fire", "market is on fire", "room is on fire", "hut is on fire",
        "church is on fire", "office is on fire", "bus is on fire", "flat is on fire", "shack is on fire",
        "kiosk is on fire", "set on fire", "caught fire", "catching fire", "burning house", "house is burning",
        "house burning", "fire in the house", "fire in my house", "fire in our house", "fire outbreak",
        "there is a fire",
        "theres a fire", "there's a fire", "fire broke out", "a fire broke out", "school is burning", "shop is burning",
        "market is burning", "building is burning", "bush fire", "bushfire", "wildfire", "trapped in a fire",
        "trapped in the fire", "gas explosion", "gas cylinder exploded", "gas cylinder burst",
        "nyumba inaungua", "nyumba yetu inaungua", "nyumba yangu inaungua", "inaungua moto", "imeshika moto",
        "imeshika moto", "kuna moto", "moto mkubwa", "moto umezuka", "moto unawaka nyumba", "nyumba inawaka moto",
        "soko linaungua", "shule inaungua", "duka linaungua", "mlipuko wa gesi", "mtungi wa gesi umelipuka",
        "maison brule", "la maison brule", "ma maison brule", "notre maison brule", "maison en feu", "en feu",
        "incendie", "au feu", "voiture en feu",
        "immeuble en feu", "boutique en feu", "cuisine en feu", "marche en feu", "ecole en feu",
        "maison est en feu", "voiture est en feu", "immeuble est en feu", "cuisine est en feu", "marche est en feu",
        "ecole est en feu", "boutique est en feu", "au feu au secours",
        "au secours au feu", "il y a le feu", "il y a un incendie", "un incendie a", "incendie dans", "incendie chez",
        "le feu a pris", "pris feu", "explosion de gaz", "bouteille de gaz a explose",
        "le marche brule", "l ecole brule")
DROWNING = ("are drowning", "people are drowning", "boat capsized", "canoe capsized", "is drowning", "drowned",
            "he is drowning", "she is drowning", "child is drowning", "someone is drowning",
            "somebody is drowning",
            "son is drowning", "daughter is drowning", "boy is drowning", "girl is drowning", "baby is drowning",
            "man is drowning", "woman is drowning", "brother is drowning", "sister is drowning", "friend is drowning",
            "kid is drowning",
            "drowning in the river", "drowning in the lake", "drowning in the sea", "drowning in the dam",
            "has drowned", "nearly drowned", "almost drowned", "drowned in the", "child drowned", "someone drowned",
            "somebody drowned", "son drowned", "daughter drowned", "boy drowned", "girl drowned", "baby drowned",
            "man drowned", "woman drowned", "brother drowned", "sister drowned", "friend drowned", "kid drowned",
            "fell into the river", "fell in the river", "fell into the lake", "fell into the dam",
            "fell into the water", "fell in the water", "fell into a well", "fell into the well", "fell in the well",
            "pulled from the water", "swept away by the flood", "swept away by water", "swept away by the river",
            "anazama", "amezama", "anazama majini", "amezama majini", "ametumbukia mtoni", "ametumbukia kisimani",
            "ameanguka mtoni", "ameanguka kisimani", "ameanguka majini", "amesombwa na maji", "amesombwa na mafuriko",
            "kuzama majini",
            "se noie", "il se noie", "elle se noie", "s est noye", "s est noyee", "noye dans la riviere",
            "noyee dans la riviere", "noye dans le fleuve", "noyee dans le fleuve",
            "tombe dans le fleuve", "tombe dans la riviere", "tombe dans le puits", "tombee dans le puits",
            "tombee dans la riviere", "tombe dans l eau", "emporte par les eaux", "emportee par les eaux",
            "emporte par la crue")
STABBING = ("stabbed", "been stabbed", "was stabbed", "stabbed me", "stabbed him", "stabbed her", "knife wound",
            "stab wound", "cut with a machete", "slashed with a panga", "cut with a panga", "attacked with a knife",
            "attacked with a machete", "was shot", "got shot", "been shot", "shot my", "shot his", "shot her",
            "police shot", "someone shot", "was shot in", "was shot by", "was shot dead", "shot dead", "been shot in",
            "has been shot", "shot him in the", "shot her in the", "shot me in the", "they shot him", "they shot her",
            "gunshot", "gunshot wound", "bullet wound",
            "amedungwa kisu", "amechomwa kisu", "amenichoma kisu", "amemchoma kisu", "kuchomwa kisu", "amepigwa kisu",
            "amekatwa panga", "amekatwa kwa panga", "jeraha la kisu", "amepigwa risasi", "wamempiga risasi",
            "poignarde", "poignardee", "coup de couteau", "coups de couteau", "blesse au couteau", "blessee au couteau",
            "coup de machette", "coups de machette", "blessure par balle", "recu une balle", "recue une balle",
            "tire sur mon", "tire sur ma", "tire sur son",
            "tire sur sa", "tire sur lui", "tire sur elle", "on lui a tire dessus", "touche par balle",
            "touchee par balle")
ROAD_ACCIDENT = ("renverse un enfant", "renverse une personne", "renverse un pieton", "renverse une femme",
                 "renverse un homme", "knocked my child", "knocked my son", "knocked my daughter", "knocked down by",
                 "knocked down a", "road accident", "car accident", "bus accident", "motorbike accident",
                 "motorcycle accident",
                 "boda accident", "boda boda accident", "bodaboda accident", "matatu accident", "okada accident",
                 "taxi accident", "lorry accident", "truck accident", "accident on the road",
                 "accident on the highway", "accident on the motorway", "accident on the main road",
                 "many injured", "people injured", "hit by a car",
                 "hit by a motorbike", "hit by a boda", "hit by a bus", "hit by a lorry", "hit by a truck",
                 "hit by a taxi", "knocked down by a car", "knocked down by a motorbike", "run over by", "car crash",
                 "bus crash", "car hit", "a car hit", "lorry hit", "truck hit", "motorbike hit", "car overturned",
                 "bus overturned",
                 "ajali ya barabarani", "ajali ya gari", "ajali ya pikipiki", "ajali ya boda", "ajali ya bodaboda",
                 "ajali ya basi", "ajali ya matatu", "amegongwa na gari", "amegongwa na pikipiki", "amegongwa na boda",
                 "amegongwa na basi", "gari limemgonga", "gari limegonga", "pikipiki imemgonga", "gari limepinduka",
                 "basi limepinduka",
                 "accident de la route", "accident de voiture", "accident de moto", "accident de bus",
                 "accident de circulation", "renverse par une voiture", "renversee par une voiture",
                 "renverse par une moto", "renversee par une moto", "percute par une voiture",
                 "percutee par une voiture", "heurte par une voiture", "la voiture s est renversee",
                 "le bus s est renverse")

def _widen(group: tuple[str, ...], sw_first: str, fr_first: str, en: tuple[str, ...] = (), sw: tuple[str, ...] = (),
           fr: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Add phrases in each base language where that language's part of the group sits, so the split by language
    below still holds."""
    i, j = group.index(sw_first), group.index(fr_first)
    return tuple(dict.fromkeys((*en, *group[:i], *group[i:j], *sw, *group[j:], *fr)))


# Common emergencies the first rules missed, found by the 2.4.1 audit: a heart attack, a stroke, choking, a fit, a
# person who stops responding, heavy blood loss, electrocution, a person dying, hanging, cut wrists, poison taken,
# and labour. Each names a person or the emergency itself, so an app that is not responding or a crop that is dying
# does not raise an alarm.
_DYING = ("husband is dying", "wife is dying", "father is dying", "mother is dying", "child is dying", "baby is dying",
          "son is dying", "daughter is dying", "brother is dying", "sister is dying", "he is dying", "she is dying",
          "someone is dying")
URGENT = _widen(URGENT, "hapumui", "ne respire plus", en=(
    "heart attack", "cardiac arrest", "had a stroke", "having a stroke", "face is drooping", "face drooping",
    "baby is choking", "child is choking", "he is choking", "she is choking", "son is choking", "daughter is choking",
    "someone is choking", "he started choking", "she started choking", "baby started choking", "child started choking",
    "electrocuted", "he is not responding", "she is not responding", "baby is not responding",
    "child is not responding", "he is unresponsive",
    "she is unresponsive", "baby is unresponsive", "child is unresponsive", "bleeding badly",
    "there is a lot of blood", "lost a lot of blood", "losing a lot of blood", "is losing blood", "having a fit",
    *_DYING),
    sw=("shambulio la moyo", "mshtuko wa moyo", "kiharusi", "amepata kiharusi", "anakabwa", "amekabwa",
        "anakabwa koo", "amepigwa shoti", "amepigwa na shoti ya umeme", "amenaswa na umeme", "mtoto anakufa",
        "mume wangu anakufa", "mke wangu anakufa", "anatoka damu sana"),
    fr=("crise cardiaque", "arret cardiaque", "avc", "s etouffe", "electrocute", "electrocutee", "il ne repond plus",
        "elle ne repond plus", "bebe ne repond plus", "saigne abondamment", "beaucoup de sang",
        "est en train de mourir", "crise d epilepsie", "fait une convulsion"))
SELF_HARM = _widen(SELF_HARM, "kujiua", "me suicider", en=(
    "hang myself", "cut my wrists", "cut her wrists", "cut his wrists", "slit my wrists", "cut myself",
    "cutting myself", "been cutting myself", "dont want to live", "don't want to live", "do not want to live", "feel like dying",
    "want to end it", "no longer want to live"),
    sw=("kujinyonga", "nitajinyonga", "amejinyonga", "kujikata"),
    fr=("me pendre", "se pendre", "s est pendu", "s est pendue", "me couper les veines", "s est ouvert les veines",
        "envie de mourir"))
POISONED = _widen(POISONED, "amewekewa sumu", "empoisonne", en=(
    "took poison", "taken poison", "drank poison", "drunk poison", "ate poison", "swallowed poison",
    "took rat poison", "taken rat poison", "drank rat poison", "ate rat poison", "took the poison",
    "drank the poison", "drank pesticide", "took all the pills", "took all her pills",
    "took all his pills", "took all my pills", "took a lot of pills", "swallowed pills"),
    sw=("amekunywa dawa ya panya", "amekula dawa ya panya", "amemeza vidonge vingi", "amemeza dawa nyingi"),
    fr=("a pris du poison", "a bu du poison", "a avale du poison", "a pris de la mort aux rats",
        "a avale des medicaments", "a pris trop de medicaments", "a avale trop de comprimes"))
PREGNANCY = _widen(PREGNANCY, "mjamzito", "enceinte",
                   en=("in labour", "in labor", "my water broke", "her water broke", "waters broke"),
                   sw=("ana uchungu wa kujifungua", "uchungu wa uzazi"), fr=("en travail", "perdu les eaux"))
CHILD = _widen(CHILD, "mtoto", "enfant", en=("baby", "my baby", "toddler"), sw=("mtoto mchanga",), fr=("bebe",))
# A child who took pills is a poisoning, unless the message says what the pills were for (see LOOKALIKES).
PILLS = ("took pills", "took tablets", "took the pills", "took the tablets", "took my pills", "took my tablets",
         "took her pills", "took his pills", "took her tablets", "took his tablets", "swallowed pills",
         "swallowed tablets", "ate pills", "ate tablets", "amemeza vidonge", "amekula vidonge", "a avale des comprimes",
         "a avale des cachets", "a pris des comprimes")


# Everyday phrases that contain an emergency phrase. They are removed from a message before the rules are read, so
# the broad phrases above keep their reach (my child is on fire, he was shot, she drowned) without these false alarms.
LOOKALIKES = ("song is on fire", "track is on fire", "album is on fire", "beat is on fire", "player is on fire",
              "team is on fire", "striker is on fire", "on fire tonight", "on fire this season", "drowned out",
              "like it is on fire", "mouth on fire", "got shot of", "drowned his voice",
              "drowned her voice", "drowned my voice", "drowned the sound",
              "drowning in debt", "drowning in work", "drowning in paperwork", "drowning in bills", "drowning in emails",
              "drowning in homework", "drowning in assignments", "shot a photo", "shot a video", "shot a film",
              "shot me a message", "shot me an email", "shot me a text", "shot him a message", "shot her a message",
              "shot down", "shot my shot", "shot his shot", "shot my first", "shot my video", "shot my film",
              "assurance incendie", "detecteur d incendie", "extincteur", "mettre au feu",
              "casserole au feu", "marmite au feu", "en feu ce soir",
              # 2.4.1: a call is not a beating, rape is also a leafy crop, and crops, prices and stoves are not people
              "amenipiga simu", "ananipiga simu", "alinipiga simu", "wamenipiga simu", "aliyenipiga simu",
              "beat me to it", "ce qui me frappe", "plant rape", "planting rape", "grow rape", "growing rape",
              "rape seedlings", "rape seed", "rape seeds", "rape crop", "rape vegetable",
              "prices collapsed", "price collapsed", "prices have collapsed",
              "seedlings are drowning", "crops are drowning", "plants are drowning", "maize is drowning",
              "maize drowned", "crops drowned", "seedlings drowned", "plants drowned", "beans drowned",
              "field drowned", "fields drowned", "prevent a bushfire", "prevent bushfire", "prevent bushfires",
              "prevent a bush fire", "prevent bush fire", "au feu de bois", "stomach is on fire",
              "prise de sang", "test de sang", "analyse de sang", "kipimo cha damu", "vipimo vya damu",
              "kupima damu", "touched the stove", "touched the hot stove", "touched a hot stove",
              *(f"took {what} for {illness}" for what in ("pills", "tablets", "the pills", "the tablets", "his pills",
                                                           "her pills", "his tablets", "her tablets")
                for illness in ("malaria", "fever", "worms", "deworming", "pain", "the pain", "headache", "a headache",
                                "a cold", "flu", "cough", "his malaria", "her malaria")),
              "feel like dying of hunger", "i am dying of hunger", "im dying of hunger", "dying of laughter",
              "dying of boredom", "fit of laughter", "fit of rage",
              "fit of anger", "not responding to my messages", "not responding to my calls", "not responding to calls",
              "not responding to messages", "not responding to my texts", "not responding to texts",
              "not responding to my emails", "cut myself while", "cut myself by accident", "cut myself accidentally",
              "cut myself shaving", "cut myself cooking", "cut myself in the kitchen", "cut myself at work")
# Everyday openings that contain an emergency phrase, set aside only at the very start of a message: beats me why
# prices rose is an idiom, while my husband beats me, what should I do is not.
LEADING_LOOKALIKES = ("beats me why", "beats me how", "beats me what", "beats me where", "beats me when")

# A snake bite is a snake word and a bite word anywhere in the message, because verbs inflect in too many ways to list
# as whole phrases: nimeumwa na nyoka, nyoka ameniuma and nyoka amemng'ata are all a bite. Each language lists its own
# words, so an emergency reply comes in the language the bite was written in. A word that is common in another
# language counts only beside a bite word of its own language (Somali mas is Portuguese for but, see snake_bite_so) or
# is written as whole phrases in its locale (Portuguese cobra also means charges).
_SNAKE_BITE_ROWS = (
    ("en", ("snake", "snakes"), ("bite", "bitten", "bit me", "bit my", "bit him", "bit her", "bit our", "bit his")),
    ("sw", ("nyoka",), ("nimeumwa", "ameumwa", "aliumwa", "niliumwa", "wameumwa", "ameniuma", "amemuuma", "amemuma",
                        "ameuma", "aliniuma", "alimuuma", "ameng'atwa", "nimeng'atwa", "aling'atwa", "ameming'ata",
                        "amemng'ata", "ameniong'ata")),
    ("fr", ("serpent",), ("mordu", "mordue", "morsure", "a mordu", "m a mordu", "l a mordu", "pique", "piquee")),
    ("pt", ("serpente",), ("mordeu", "mordido", "mordida", "picou", "picado", "picada")),
    ("rw", ("inzoka",), ("yarumye", "yamurumye", "yandumye", "arumwe", "yaramurumye")),
    ("rn", ("inzoka",), ("yarumye", "yamurumye", "yandumye", "arumwe")),
    ("zu", ("inyoka", "yinyoka"), ("iluma", "ilume", "ulunywe", "ilumile", "imlumile", "yamluma", "ingilumile")),
    ("xh", ("inyoka", "yinyoka"), ("iluma", "ilume", "ulunywe", "ilumile", "imlumile", "yamluma")),
    ("so", ("mas", "abeeso", "maska", "maskii"), ("qaniinay", "qaniintay", "qaniiney", "qaniinyay")),
    ("ar", ("ثعبان", "أفعى", "افعى", "الثعبان", "الأفعى"),
           ("لدغ", "لدغت", "لدغه", "لدغها", "لدغني", "لدغته", "لدغتني", "عض", "عضه", "عضت", "عضني")),
    ("lg", ("omusota", "musota"), ("gwaluma", "gumuluma", "gwamuluma", "alumiddwa", "yalumiddwa")),
    ("ln", ("nyoka",), ("eswi", "eswaki", "aswami")),
    ("wo", ("jaan",), ("màtt",)),
    ("ig", ("agwo", "agwọ"), ("tagburu", "tara ya", "tara nwa", "tara m")),
    ("ha", ("maciji",), ("ciji", "ya ciji", "ta ciji", "ya sare", "ya sari", "ta sare")),
    ("om", ("bofa",), ("ciniine", "ciniinte")),
    ("am", ("እባብ",), ("ነደፈ", "ነደፈው", "ነደፈችው", "ነደፋት", "ነደፈኝ")),
    ("sn", ("nyoka",), ("yaruma", "yakaruma", "yamuruma")),
    ("ny", ("njoka",), ("yaluma", "yamuluma")),
    ("st", ("noha",), ("lomile", "e lomile", "e mo lomile")),
    ("tn", ("noga",), ("lomile", "lomilwe", "e lomile")),
)
# Somali mas counts only beside a Somali bite word, because mas is Portuguese for but.
_OWN_LANGUAGE_ONLY = {"mas"}
SNAKE = tuple(dict.fromkeys(w for _, snakes, _ in _SNAKE_BITE_ROWS for w in snakes if w not in _OWN_LANGUAGE_ONLY))
BITE = tuple(dict.fromkeys(w for _, _, bites in _SNAKE_BITE_ROWS for w in bites))

# The phrases above, before any locale widens them, by language. Each group lists English, then Swahili, then French.
_FIRST = ((PREGNANCY, "mjamzito", "enceinte"), (POSTPARTUM, "amejifungua", "accouche"),
          (MATERNAL_DANGER, "damu", "saigne"), (URGENT, "hapumui", "ne respire plus"),
          (POISON_ACT, "amekunywa", "a avale"), (POISON_WHAT, "sumu", "produit chimique"),
          (POISONED, "amewekewa sumu", "empoisonne"), (GBV, "nimebakwa", "viol"), (CHILD, "mtoto", "enfant"),
          (CHILD_HARM, "amenajisiwa", "abusee"), (SELF_HARM, "kujiua", "me suicider"),
          (FIRE, "nyumba inaungua", "maison brule"), (DROWNING, "anazama", "se noie"),
          (STABBING, "amedungwa kisu", "poignarde"), (ROAD_ACCIDENT, "ajali ya barabarani", "accident de la route"))
_BASE_EN: set[str] = set()
_BASE_SW: set[str] = set()
_BASE_FR: set[str] = set()
for _group, _sw, _fr in _FIRST:
    _i, _j = _group.index(_sw), _group.index(_fr)
    _BASE_EN.update(_group[:_i])
    _BASE_SW.update(_group[_i:_j])
    _BASE_FR.update(_group[_j:])
_BASE_SW.discard("abuse")  # CHILD_HARM lists abuse twice, once in English and once in French
_BASE_FR.add("abuse")

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
FIRE = i18n.phrases("safety.FIRE", FIRE)
DROWNING = i18n.phrases("safety.DROWNING", DROWNING)
STABBING = i18n.phrases("safety.STABBING", STABBING)
ROAD_ACCIDENT = i18n.phrases("safety.ROAD_ACCIDENT", ROAD_ACCIDENT)

DEFAULT_RULES: dict[str, tuple[tuple[str, ...], ...]] = {
    # Order matters: the first queue whose rule fires wins.
    "self_harm": ((*SELF_HARM,),),
    "maternal": ((*PREGNANCY, *POSTPARTUM), MATERNAL_DANGER),
    "poisoning": ((*POISONED,),),
    "poisoning_act": (POISON_ACT, POISON_WHAT),
    "poisoning_child": (CHILD, PILLS),
    "child_protection": (CHILD, CHILD_HARM),
    "gbv": ((*GBV,),),
    "fire": ((*FIRE,),),
    "health_urgent": ((*URGENT,),),
    "drowning": ((*DROWNING,),),
    "stabbing": ((*STABBING,),),
    "road_accident": ((*ROAD_ACCIDENT,),),
    "snake_bite": (SNAKE, BITE),
    "snake_bite_so": (("mas",), next(bites for code, _, bites in _SNAKE_BITE_ROWS if code == "so")),
}
_QUEUE_ALIASES = {"poisoning_act": "poisoning", "poisoning_child": "poisoning", "snake_bite": "health_urgent",
                  "snake_bite_so": "health_urgent",
                  "drowning": "health_urgent", "stabbing": "health_urgent", "road_accident": "health_urgent"}
# Queues whose own lines are often missing from a country's pack: their reply also gives the general emergency numbers.
WITH_EMERGENCY = frozenset({"fire"})


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
        hay = token_hay(text)
        for phrase in LEADING_LOOKALIKES:
            if hay.startswith(_needle(phrase)):
                hay = " ~ " + hay[len(_needle(phrase)):]
        for phrase in LOOKALIKES:
            if phrase_in(hay, phrase):
                hay = hay.replace(_needle(phrase), " ~ ")
        for queue, groups in self.rules.items():
            hits: list[str] = []
            for group in groups:
                found = next((p for p in group if phrase_in(hay, p)), None)
                if found is None:
                    break
                hits.append(found)
            else:
                return SafetyDecision(True, _QUEUE_ALIASES.get(queue, queue), hits)
        return SafetyDecision(False)


# Each language's own safety phrases, to answer an emergency in the language it was written in.
_OWN: dict[str, frozenset[str]] = {
    code: frozenset(p for path, group in loc.phrases.items() if path.startswith("safety.") for p in group)
    for code, loc in i18n.locales().items()}
_OWN.update(en=frozenset(_BASE_EN), sw=frozenset(_BASE_SW), fr=frozenset(_BASE_FR))
for _code, _snakes, _bites in _SNAKE_BITE_ROWS:
    _OWN[_code] = _OWN.get(_code, frozenset()) | frozenset(_snakes) | frozenset(_bites)


def alarm_language(text: str, lang: str, allowed: tuple[str, ...] | None) -> str:
    """The language to answer an emergency in.

    Marker words can miss a short message in a language with few of them, and the reply would then come in
    English or French. If none of the detected language's own safety phrases is in the message, but one from
    another language of the caller's country is, the reply comes in that language."""
    if not allowed:
        return lang
    hay = token_hay(text)

    def speaks(code: str) -> bool:
        return any(phrase_in(hay, p) for p in _OWN.get(code, ()))

    if speaks(lang):
        return lang
    return next((code for code in allowed if code != lang and speaks(code)), lang)


class HandoffSink(Protocol):
    """Where escalations go: a nurse helpdesk, an extension officer queue, a ticketing system."""

    def raise_handoff(self, queue: str, person_key: str, text: str, channel: str,
                      country: str | None = None) -> None: ...


@dataclass
class InMemoryHandoffs:
    events: list[dict[str, str]] = field(default_factory=list)

    def raise_handoff(self, queue: str, person_key: str, text: str, channel: str,
                      country: str | None = None) -> None:
        self.events.append({"queue": queue, "person": person_key, "text": text, "channel": channel,
                            "country": country or ""})


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
        "fr" :
        "Cela ressemble à un empoisonnement. Obtenez une aide médicale maintenant et emportez le produit. {numbers}",
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
    "fire": {
        "en": "This sounds like a fire. Get everyone out now and stay out. {numbers}",
        "sw": "Hii inaonekana kuwa moto. Watoe watu wote nje sasa na msirudi ndani. {numbers}",
        "fr": "Cela ressemble à un incendie. Faites sortir tout le monde maintenant et ne rentrez pas. {numbers}",
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
    """Every distinct contact that serves a queue, emergency numbers first. A fire also gets the general emergency
    numbers, because many countries' packs list no separate fire line."""
    queues = {queue, "emergency"} if queue in WITH_EMERGENCY else {queue}
    seen: dict[str, Contact] = {}
    for f in facts:
        if country and f.scope.countries and country.upper() not in f.scope.countries:
            continue
        for c in f.contacts:
            if queues & set(c.queues) and c.number not in seen:
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


def emergency_text_within(queue: str, contacts: list[Contact], language: str, fits: Callable[[str], bool]) -> str:
    """The emergency reply, shortened until it fits a small screen without losing a number.

    The numbers come last in the full reply, so cutting from the end would drop them. Instead the reply gives up,
    in turn, the advice after its first sentence, the labels beside the numbers, and then everything but the call
    line and the numbers themselves."""
    full = emergency_text(queue, contacts, language)
    if fits(full) or not contacts:
        return full
    lang = language if language in CALL_WORD else "en"
    opener = OPENERS.get(queue, OPENERS["health_urgent"])[lang].replace("{numbers}", "").strip()
    first = next((opener[: i + 1] for i, c in enumerate(opener) if c in ".!?።؟" and i > 0), opener)
    bare = call_line(", ".join(dict.fromkeys(c.number for c in contacts)), lang)
    for text in (f"{first} {format_numbers(contacts, lang)}", f"{first} {bare}", bare):
        if fits(text):
            return text
    return " ".join(dict.fromkeys(c.number for c in contacts))
