"""ACE: the African Context Engine.

One context engine behind every entry point: voice, USSD, SMS, WhatsApp,
smartphone apps, trusted agents, interactive radio and AI assistants.
"""
from .engine import Engine, EngineConfig, Intent, KeywordClassifier
from .identity import ProfileStore, normalize_msisdn
from .models import Channel, GeoPoint, Message, Reply

__version__ = "0.1.0"

__all__ = [
           "Channel",
           "Engine",
           "EngineConfig",
           "GeoPoint",
           "Intent",
           "KeywordClassifier",
           "Message",
           "ProfileStore",
           "Reply",
           "__version__",
           "normalize_msisdn",
]
