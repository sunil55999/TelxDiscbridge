"""Core modules for the forwarding bot."""

# This file makes the core directory a Python package
from .database import Database, ForwardingPair, MessageMapping
from .session_manager import SessionManager
from .telegram_source import TelegramSource
from .telegram_destination import TelegramDestination
from .discord_relay import DiscordRelay
from .message_formatter import MessageFormatter
from .message_orchestrator import MessageOrchestrator

__all__ = [
    "Database",
    "ForwardingPair", 
    "MessageMapping",
    "SessionManager",
    "TelegramSource", 
    "TelegramDestination",
    "DiscordRelay",
    "MessageFormatter", 
    "MessageOrchestrator"
]