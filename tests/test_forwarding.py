import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from core.database import Database, ForwardingPair, MessageMapping
from core.message_orchestrator import MessageOrchestrator
from core.telegram_source import TelegramSource
from core.telegram_destination import TelegramDestination
from core.discord_relay import DiscordRelay
from handlers.telegram_handler import TelegramMessageHandler


class TestForwarding(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.db = MagicMock(spec=Database)
        self.ts = MagicMock(spec=TelegramSource)
        self.td = MagicMock(spec=TelegramDestination)
        self.dr = MagicMock(spec=DiscordRelay)
        self.mo = MessageOrchestrator(self.db, self.ts, self.td, self.dr, MagicMock())
        self.th = TelegramMessageHandler(self.db, self.dr, self.td)

    def test_handle_new_message(self):
        async def run_test():
            pair = ForwardingPair(id=1, discord_channel_id=123, telegram_dest_chat_id=456)
            self.dr.send_message_to_discord = AsyncMock(return_value=789)
            self.td.send_message = AsyncMock(return_value=101)

            await self.th._handle_new_message({
                "pair": pair,
                "original_message": MagicMock(id=111),
                "formatted_message": {"text": "hello"},
            })

            self.dr.send_message_to_discord.assert_called_once()
            self.td.send_message.assert_called_once()

        self.loop.run_until_complete(run_test())

    def test_handle_edit_message(self):
        async def run_test():
            pair = ForwardingPair(id=1, discord_channel_id=123, telegram_dest_chat_id=456)
            mapping = MessageMapping(discord_message_id=789, telegram_dest_id=101)
            self.dr.edit_discord_message = AsyncMock(return_value=True)
            self.td.edit_message = AsyncMock(return_value=True)

            await self.th._handle_message_edit({
                "pair": pair,
                "original_message": MagicMock(id=111),
                "formatted_message": {"text": "hello world", "type": "text"},
                "mapping": mapping,
            })

            self.dr.edit_discord_message.assert_called_once()
            self.td.edit_message.assert_called_once()

        self.loop.run_until_complete(run_test())

    def test_handle_delete_message(self):
        async def run_test():
            pair = ForwardingPair(id=1, discord_channel_id=123, telegram_dest_chat_id=456)
            mapping = MessageMapping(discord_message_id=789, telegram_dest_id=101)
            self.dr.delete_discord_message = AsyncMock(return_value=True)
            self.td.delete_message = AsyncMock(return_value=True)

            await self.th._handle_message_delete({
                "pair": pair,
                "mapping": mapping,
            })

            self.dr.delete_discord_message.assert_called_once()
            self.td.delete_message.assert_called_once()

if __name__ == "__main__":
    unittest.main()
