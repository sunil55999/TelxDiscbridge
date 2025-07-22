import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from core.database import Database, ForwardingPair, SessionInfo
from admin_bot.unified_admin_commands import UnifiedAdminCommands
from admin_bot.unified_session_commands import UnifiedSessionCommands
from utils.encryption import EncryptionManager


class TestAdminCommands(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.db = MagicMock(spec=Database)
        self.encryption_manager = MagicMock(spec=EncryptionManager)
        self.message_filter = MagicMock()
        self.advanced_session_manager = MagicMock()
        self.bot_manager = MagicMock()
        self.unified_commands = UnifiedAdminCommands(self.db, self.encryption_manager, self.message_filter, self.advanced_session_manager)
        self.session_commands = UnifiedSessionCommands(self.db, self.advanced_session_manager)

    def test_add_pair(self):
        async def run_test():
            update = AsyncMock()
            context = MagicMock()
            context.user_data = {}

            await self.unified_commands.addpair_command(update, context)

            update.message.reply_text.assert_called_once()
            self.assertEqual(context.user_data['step'], 'name')

        self.loop.run_until_complete(run_test())

    def test_list_pairs(self):
        async def run_test():
            update = AsyncMock()
            context = MagicMock()
            self.db.get_all_pairs = AsyncMock(return_value=[])

            await self.unified_commands.listpairs_command(update, context)

            update.message.reply_text.assert_called_once()

        self.loop.run_until_complete(run_test())

    def test_add_session(self):
        async def run_test():
            update = AsyncMock()
            context = MagicMock()
            context.args = ["test_session", "+1234567890"]
            self.db.get_session_info = AsyncMock(return_value=None)
            self.advanced_session_manager.register_session = AsyncMock(return_value=True)
            self.advanced_session_manager.authenticate_session = AsyncMock(return_value={"needs_otp": True})

            await self.session_commands.addsession_command(update, context)

            update.message.reply_text.assert_called_once()

        self.loop.run_until_complete(run_test())

if __name__ == "__main__":
    unittest.main()
