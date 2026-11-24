"""ACE: the African Context Engine.

Checked, local, citable knowledge behind every entry point people in Africa
actually use: USSD, SMS, voice, WhatsApp, apps and AI assistants.
"""
from .context import ContextFact, ContextQuery, ContextStore, ReviewStatus, load_pack, load_packs
from .engine import CHANNEL_BUDGETS, Engine, EngineConfig
from .identity import ProfileStore, normalize_msisdn
from .models import Channel, Citation, GeoPoint, Message, Reply, ReplyKind
from .scam import Verdict, analyse

__version__ = "1.1.0"

__all__ = [
    "CHANNEL_BUDGETS", "Channel", "Citation", "ContextFact", "ContextQuery", "ContextStore", "Engine",
    "EngineConfig", "GeoPoint", "Message", "ProfileStore", "Reply", "ReplyKind", "ReviewStatus", "Verdict",
    "__version__", "analyse", "load_pack", "load_packs", "normalize_msisdn",
]
