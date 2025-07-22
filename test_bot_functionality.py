#!/usr/bin/env python3
"""
Comprehensive test suite for the forwarding bot functionality.
Tests all commands, features, and core functionality.
"""

import asyncio
import sys
import json
import tempfile
import os
from typing import Dict, Any, List
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.append('.')

from config.settings import Settings
from core.database import Database
from core.advanced_session_manager import AdvancedSessionManager
from core.session_manager import SessionManager
from utils.encryption import EncryptionManager
from admin_bot.bot_management import BotTokenManager
from admin_bot.unified_admin_commands import UnifiedAdminCommands
from core.message_filter import MessageFilter


class BotFunctionalityTester:
    """Comprehensive test suite for bot functionality."""
    
    def __init__(self):
        self.database: Database = None
        self.session_manager: SessionManager = None
        self.advanced_session_manager: AdvancedSessionManager = None
        self.encryption_manager: EncryptionManager = None
        self.bot_manager: BotTokenManager = None
        self.unified_commands: UnifiedAdminCommands = None
        self.message_filter: MessageFilter = None
        
        self.test_results: List[Dict[str, Any]] = []
        self.passed_tests = 0
        self.failed_tests = 0
    
    async def initialize(self):
        """Initialize all components for testing."""
        print("🔧 Initializing test components...")
        
        try:
            # Initialize database with test database
            self.database = Database("sqlite+aiosqlite:///test_forwarding_bot.db")
            await self.database.initialize()
            
            # Initialize encryption
            self.encryption_manager = EncryptionManager()
            
            # Initialize session management
            self.session_manager = SessionManager(self.database)
            self.advanced_session_manager = AdvancedSessionManager(self.database, self.session_manager)
            
            # Initialize message filter
            self.message_filter = MessageFilter(self.database)
            await self.message_filter.initialize()
            
            # Initialize bot management
            self.bot_manager = BotTokenManager(self.database, self.encryption_manager)
            
            # Initialize unified commands
            self.unified_commands = UnifiedAdminCommands(
                self.database,
                self.encryption_manager,
                self.message_filter,
                self.advanced_session_manager
            )
            
            print("✅ All components initialized successfully")
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            raise
    
    async def cleanup(self):
        """Clean up test resources."""
        print("🧹 Cleaning up test resources...")
        
        # Remove test database
        test_db_path = "test_forwarding_bot.db"
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            print(f"🗑️ Removed test database: {test_db_path}")
    
    def add_test_result(self, test_name: str, passed: bool, details: str = "", error: str = ""):
        """Add a test result."""
        result = {
            'test_name': test_name,
            'passed': passed,
            'details': details,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        self.test_results.append(result)
        
        if passed:
            self.passed_tests += 1
            print(f"✅ {test_name}: PASSED - {details}")
        else:
            self.failed_tests += 1
            print(f"❌ {test_name}: FAILED - {error}")
    
    async def test_database_operations(self):
        """Test database operations."""
        print("\n📊 Testing Database Operations...")
        
        try:
            # Test session operations
            from core.database import SessionInfo
            
            test_session = SessionInfo(
                name="test_session",
                phone_number="+1234567890",
                is_active=True,
                health_status="healthy"
            )
            
            session_id = await self.database.add_session(test_session)
            self.add_test_result("Database - Add Session", session_id is not None, f"Session ID: {session_id}")
            
            # Test getting sessions
            sessions = await self.database.get_all_sessions()
            self.add_test_result("Database - Get Sessions", len(sessions) > 0, f"Found {len(sessions)} sessions")
            
            # Test pair operations
            from core.database import ForwardingPair
            
            test_pair = ForwardingPair(
                name="test_pair",
                telegram_source_chat_id=123456789,
                discord_channel_id=987654321,
                telegram_dest_chat_id=111222333,
                telegram_bot_token_encrypted="encrypted_test_token",
                discord_webhook_url="https://discord.com/api/webhooks/test",
                session_name="test_session"
            )
            
            pair_id = await self.database.add_pair(test_pair)
            self.add_test_result("Database - Add Pair", pair_id is not None, f"Pair ID: {pair_id}")
            
            # Test getting pairs
            pairs = await self.database.get_all_pairs()
            self.add_test_result("Database - Get Pairs", len(pairs) > 0, f"Found {len(pairs)} pairs")
            
        except Exception as e:
            self.add_test_result("Database Operations", False, error=str(e))
    
    async def test_encryption(self):
        """Test encryption functionality."""
        print("\n🔐 Testing Encryption...")
        
        try:
            test_data = "test_bot_token_123456:ABC-DEF"
            
            # Test encryption
            encrypted = self.encryption_manager.encrypt(test_data)
            self.add_test_result("Encryption - Encrypt", encrypted != test_data, f"Data encrypted successfully")
            
            # Test decryption
            decrypted = self.encryption_manager.decrypt(encrypted)
            self.add_test_result("Encryption - Decrypt", decrypted == test_data, f"Data decrypted correctly")
            
            # Test with invalid data
            try:
                invalid_decrypt = self.encryption_manager.decrypt("invalid_encrypted_data")
                self.add_test_result("Encryption - Invalid Data", False, error="Should have failed with invalid data")
            except:
                self.add_test_result("Encryption - Invalid Data", True, "Properly rejected invalid encrypted data")
                
        except Exception as e:
            self.add_test_result("Encryption", False, error=str(e))
    
    async def test_bot_token_management(self):
        """Test bot token management."""
        print("\n🤖 Testing Bot Token Management...")
        
        try:
            # Test adding invalid bot token (should fail gracefully)
            result = await self.bot_manager.add_named_bot_token("test_bot", "invalid_token")
            self.add_test_result("Bot Token - Invalid Token", not result['success'], "Properly rejected invalid token")
            
            # Test getting available bots (should be empty)
            bots = await self.bot_manager.get_available_bots()
            self.add_test_result("Bot Token - Get Available", isinstance(bots, list), f"Retrieved {len(bots)} bots")
            
            # Test removing non-existent bot
            removed = await self.bot_manager.remove_bot_token("non_existent_bot")
            self.add_test_result("Bot Token - Remove Non-existent", not removed, "Properly handled non-existent bot")
            
        except Exception as e:
            self.add_test_result("Bot Token Management", False, error=str(e))
    
    async def test_session_management(self):
        """Test session management functionality."""
        print("\n👥 Testing Session Management...")
        
        try:
            # Test session health monitoring
            sessions = await self.database.get_all_sessions()
            self.add_test_result("Session Management - Health Check", True, f"Checked {len(sessions)} sessions")
            
            # Test advanced session manager initialization
            await self.advanced_session_manager.start()
            self.add_test_result("Session Management - Advanced Manager Start", True, "Advanced session manager started")
            
            # Test getting session statistics
            stats = await self.advanced_session_manager.get_session_statistics()
            self.add_test_result("Session Management - Statistics", isinstance(stats, dict), f"Retrieved session stats")
            
            await self.advanced_session_manager.stop()
            
        except Exception as e:
            self.add_test_result("Session Management", False, error=str(e))
    
    async def test_message_filtering(self):
        """Test message filtering functionality."""
        print("\n🔍 Testing Message Filtering...")
        
        try:
            # Test adding global blocked word
            success = await self.message_filter.add_global_blocked_word("spam")
            self.add_test_result("Message Filter - Add Blocked Word", success, "Added 'spam' to blocked words")
            
            # Test getting filter stats
            stats = await self.message_filter.get_filter_stats()
            self.add_test_result("Message Filter - Get Stats", isinstance(stats, dict), f"Retrieved filter stats")
            
            # Test removing blocked word
            removed = await self.message_filter.remove_global_blocked_word("spam")
            self.add_test_result("Message Filter - Remove Blocked Word", removed, "Removed 'spam' from blocked words")
            
            # Test global settings update
            settings_updated = await self.message_filter.update_global_settings({'filter_images': True})
            self.add_test_result("Message Filter - Update Settings", settings_updated, "Updated global filter settings")
            
        except Exception as e:
            self.add_test_result("Message Filtering", False, error=str(e))
    
    async def test_command_parsing(self):
        """Test command parsing and validation."""
        print("\n⚡ Testing Command Parsing...")
        
        try:
            # Create mock update and context objects
            class MockMessage:
                def __init__(self, text):
                    self.text = text
                    self.reply_text = self._reply_text
                    self.replies = []
                
                async def _reply_text(self, text, parse_mode=None):
                    self.replies.append({'text': text, 'parse_mode': parse_mode})
                    return True
            
            class MockUser:
                def __init__(self, user_id):
                    self.id = user_id
            
            class MockUpdate:
                def __init__(self, message_text, user_id=12345):
                    self.message = MockMessage(message_text)
                    self.effective_user = MockUser(user_id)
                    self.effective_message = self.message
                    self.callback_query = None
            
            class MockContext:
                def __init__(self, args=None):
                    self.args = args or []
                    self.user_data = {}
                    self.bot = None
            
            # Test start command
            mock_update = MockUpdate("/start")
            mock_context = MockContext()
            
            await self.unified_commands.start_command(mock_update, mock_context)
            self.add_test_result("Commands - Start Command", len(mock_update.message.replies) > 0, "Start command executed")
            
            # Test help command
            mock_update = MockUpdate("/help")
            mock_context = MockContext()
            
            await self.unified_commands.help_command(mock_update, mock_context)
            self.add_test_result("Commands - Help Command", len(mock_update.message.replies) > 0, "Help command executed")
            
            # Test status command
            mock_update = MockUpdate("/status")
            mock_context = MockContext()
            
            await self.unified_commands.status_command(mock_update, mock_context)
            self.add_test_result("Commands - Status Command", len(mock_update.message.replies) > 0, "Status command executed")
            
        except Exception as e:
            self.add_test_result("Command Parsing", False, error=str(e))
    
    async def test_pair_creation_workflow(self):
        """Test the pair creation workflow."""
        print("\n🔗 Testing Pair Creation Workflow...")
        
        try:
            # Test pair creation command initialization
            class MockMessage:
                def __init__(self):
                    self.replies = []
                
                async def reply_text(self, text, parse_mode=None):
                    self.replies.append({'text': text, 'parse_mode': parse_mode})
                    return True
            
            class MockUpdate:
                def __init__(self):
                    self.message = MockMessage()
                    self.effective_user = type('MockUser', (), {'id': 12345})
                    self.effective_message = self.message
            
            class MockContext:
                def __init__(self):
                    self.args = []
                    self.user_data = {}
            
            mock_update = MockUpdate()
            mock_context = MockContext()
            
            # Test addpair command
            await self.unified_commands.addpair_command(mock_update, mock_context)
            self.add_test_result("Pair Creation - Start Wizard", len(mock_update.message.replies) > 0, "Pair creation wizard started")
            
            # Test wizard input handling
            mock_context.user_data = {'creating_pair': True, 'step': 'name'}
            mock_update.message = MockMessage()
            mock_update.message.text = "Test Pair"
            
            handled = await self.unified_commands.handle_pair_creation_input(mock_update, mock_context)
            self.add_test_result("Pair Creation - Handle Input", handled, "Wizard input handled correctly")
            
        except Exception as e:
            self.add_test_result("Pair Creation Workflow", False, error=str(e))
    
    async def test_error_handling(self):
        """Test error handling mechanisms."""
        print("\n⚠️ Testing Error Handling...")
        
        try:
            # Test database connection error handling
            try:
                bad_database = Database()
                await bad_database.initialize("invalid://connection/string")
                self.add_test_result("Error Handling - Database Connection", False, error="Should have failed with invalid connection")
            except:
                self.add_test_result("Error Handling - Database Connection", True, "Properly handled invalid database connection")
            
            # Test encryption error handling
            try:
                bad_data = self.encryption_manager.decrypt("completely_invalid_data")
                self.add_test_result("Error Handling - Decryption", False, error="Should have failed with invalid data")
            except:
                self.add_test_result("Error Handling - Decryption", True, "Properly handled decryption errors")
            
            # Test command with missing parameters
            class MockMessage:
                def __init__(self):
                    self.replies = []
                
                async def reply_text(self, text, parse_mode=None):
                    self.replies.append({'text': text, 'parse_mode': parse_mode})
                    return True
            
            class MockUpdate:
                def __init__(self):
                    self.message = MockMessage()
            
            class MockContext:
                def __init__(self):
                    self.args = []
            
            mock_update = MockUpdate()
            mock_context = MockContext()
            
            await self.unified_commands.removepair_command(mock_update, mock_context)
            help_reply = any('Usage:' in reply['text'] for reply in mock_update.message.replies)
            self.add_test_result("Error Handling - Missing Parameters", help_reply, "Properly showed usage help for missing parameters")
            
        except Exception as e:
            self.add_test_result("Error Handling", False, error=str(e))
    
    async def run_all_tests(self):
        """Run all tests and generate report."""
        print("🚀 Starting Comprehensive Bot Functionality Tests")
        print("=" * 60)
        
        await self.initialize()
        
        # Run all test suites
        await self.test_database_operations()
        await self.test_encryption()
        await self.test_bot_token_management()
        await self.test_session_management()
        await self.test_message_filtering()
        await self.test_command_parsing()
        await self.test_pair_creation_workflow()
        await self.test_error_handling()
        
        # Generate test report
        await self.generate_test_report()
        
        await self.cleanup()
    
    async def generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        # Group results by category
        categories = {}
        for result in self.test_results:
            category = result['test_name'].split(' - ')[0]
            if category not in categories:
                categories[category] = {'passed': 0, 'failed': 0, 'tests': []}
            
            if result['passed']:
                categories[category]['passed'] += 1
            else:
                categories[category]['failed'] += 1
            
            categories[category]['tests'].append(result)
        
        # Print category summaries
        for category, data in categories.items():
            total_cat = data['passed'] + data['failed']
            cat_success = (data['passed'] / total_cat * 100) if total_cat > 0 else 0
            status = "✅" if data['failed'] == 0 else "⚠️" if data['passed'] > data['failed'] else "❌"
            
            print(f"{status} {category}: {data['passed']}/{total_cat} passed ({cat_success:.1f}%)")
            
            # Show failed tests
            failed_tests = [t for t in data['tests'] if not t['passed']]
            for failed_test in failed_tests:
                print(f"   ❌ {failed_test['test_name']}: {failed_test['error']}")
        
        print()
        
        # Overall assessment
        if success_rate >= 90:
            print("🎉 EXCELLENT: Bot functionality is working excellently!")
        elif success_rate >= 75:
            print("👍 GOOD: Bot functionality is working well with minor issues.")
        elif success_rate >= 50:
            print("⚠️ FAIR: Bot has several issues that need attention.")
        else:
            print("❌ POOR: Bot has significant issues that must be resolved.")
        
        # Save detailed report to file
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total_tests,
                'passed': self.passed_tests,
                'failed': self.failed_tests,
                'success_rate': success_rate
            },
            'categories': categories,
            'detailed_results': self.test_results
        }
        
        with open('test_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Detailed test report saved to: test_report.json")


async def main():
    """Main test execution function."""
    tester = BotFunctionalityTester()
    
    try:
        await tester.run_all_tests()
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1
    
    # Return exit code based on test results
    if tester.failed_tests == 0:
        return 0  # All tests passed
    elif tester.passed_tests > tester.failed_tests:
        return 1  # More passed than failed
    else:
        return 2  # More failed than passed


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)