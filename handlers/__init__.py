"""Message handlers for the forwarding bot."""

# This file makes the handlers directory a Python package
from .telegram_handler import TelegramMessageHandler
from .discord_handler import DiscordMessageHandler

__all__ = [
    "TelegramMessageHandler",
    "DiscordMessageHandler"
]