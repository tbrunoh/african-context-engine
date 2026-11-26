"""ACE: the African Context Engine.

Checked, local, citable knowledge behind every entry point people in Africa
actually use: USSD, SMS, RCS, voice, WhatsApp, apps and AI assistants. From 2.0, decision
services turn dated public data into short, cited answers for 34 countries, in English, Swahili,
French, Portuguese, Arabic, Amharic, Afaan Oromo and Somali.
"""
from .context import ContextFact, ContextQuery, ContextStore, ReviewStatus, load_pack, load_packs
from .engine import CHANNEL_BUDGETS, Engine, EngineConfig
from .identity import ProfileStore, normalize_msisdn
from .models import Channel, Citation, GeoPoint, Message, Reply, ReplyKind
from .scam import Verdict, analyse

__version__ = "2.2.0b3"

__all__ = [
    "CHANNEL_BUDGETS", "Channel", "Citation", "ContextFact", "ContextQuery", "ContextStore", "Engine",
    "EngineConfig", "GeoPoint", "Message", "ProfileStore", "Reply", "ReplyKind", "ReviewStatus", "Verdict",
    "__version__", "analyse", "load_pack", "load_packs", "normalize_msisdn",
]
