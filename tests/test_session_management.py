"""Test suite for advanced session management functionality."""

import asyncio
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from core.database import Database, SessionInfo, ForwardingPair
from core.session_manager import SessionManager
from core.advanced_session_manager import AdvancedSessionManager


class TestAdvancedSessionManagement(unittest.IsolatedAsyncioTestCase):
    """Test cases for advanced session management."""
    
    async def asyncSetUp(self):
        """Set up test environment."""
        # Use in-memory SQLite for testing
        self.database = Database("sqlite+aiosqlite:///:memory:")
        await self.database.initialize()
        
        # Mock session manager
        self.session_manager = AsyncMock(spec=SessionManager)
        
        # Initialize advanced session manager
        self.advanced_session_manager = AdvancedSessionManager(
            self.database, 
            self.session_manager
        )
    
    async def asyncTearDown(self):
        """Clean up test environment."""
        await self.database.close()
    
    async def test_session_registration(self):
        """Test session registration functionality."""
        # Register a new session
        success = await self.advanced_session_manager.register_session(
            "test_session_1", 
            "+1234567890", 
            priority=1, 
            max_pairs=25
        )
        
        self.assertTrue(success)
        
        # Verify session was stored
        session_info = await self.database.get_session_info("test_session_1")
        self.assertIsNotNone(session_info)
        self.assertEqual(session_info.name, "test_session_1")
        self.assertEqual(session_info.phone_number, "+1234567890")
        self.assertEqual(session_info.max_pairs, 25)
        self.assertEqual(session_info.priority, 1)
    
    async def test_bulk_session_reassignment(self):
        """Test bulk reassignment of pairs to sessions."""
        # Create sessions
        await self.advanced_session_manager.register_session("session_1", "+1111111111", priority=1)
        await self.advanced_session_manager.register_session("session_2", "+2222222222", priority=2)
        
        # Create test pairs
        pair1 = ForwardingPair(
            name="test_pair_1",
            telegram_source_chat_id=123,
            discord_channel_id=456,
            telegram_dest_chat_id=789,
            session_name="session_1"
        )
        pair2 = ForwardingPair(
            name="test_pair_2",
            telegram_source_chat_id=124,
            discord_channel_id=457,
            telegram_dest_chat_id=790,
            session_name="session_1"
        )
        
        pair1_id = await self.database.add_pair(pair1)
        pair2_id = await self.database.add_pair(pair2)
        
        # Mock health check to return healthy
        with patch.object(self.advanced_session_manager, '_perform_health_check') as mock_health:
            mock_health.return_value = AsyncMock()
            mock_health.return_value.is_healthy = True
            mock_health.return_value.status = "healthy"
            mock_health.return_value.last_verified = datetime.utcnow()
            
            # Perform bulk reassignment
            result = await self.advanced_session_manager.bulk_reassign_session(
                [pair1_id, pair2_id], 
                "session_2"
            )
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['reassigned_pairs']), 2)
        
        # Verify pairs were reassigned
        updated_pair1 = await self.database.get_pair(pair1_id)
        updated_pair2 = await self.database.get_pair(pair2_id)
        
        self.assertEqual(updated_pair1.session_name, "session_2")
        self.assertEqual(updated_pair2.session_name, "session_2")
    
    async def test_optimal_session_selection(self):
        """Test optimal session selection algorithm."""
        # Create sessions with different priorities and capacities
        await self.advanced_session_manager.register_session("low_priority", "+1111111111", priority=1, max_pairs=10)
        await self.advanced_session_manager.register_session("high_priority", "+2222222222", priority=3, max_pairs=10)
        await self.advanced_session_manager.register_session("medium_priority", "+3333333333", priority=2, max_pairs=10)
        
        # Update health status to healthy for all sessions
        await self.database.update_session_health("low_priority", "healthy", datetime.utcnow())
        await self.database.update_session_health("high_priority", "healthy", datetime.utcnow())
        await self.database.update_session_health("medium_priority", "healthy", datetime.utcnow())
        
        # Get optimal session
        optimal_session = await self.advanced_session_manager.get_optimal_session_for_assignment()
        
        # Should select highest priority session
        self.assertEqual(optimal_session, "high_priority")
    
    async def test_session_health_monitoring(self):
        """Test session health monitoring functionality."""
        # Register a session
        await self.advanced_session_manager.register_session("health_test", "+1234567890")
        
        # Mock health check
        with patch.object(self.advanced_session_manager, '_perform_health_check') as mock_health:
            mock_health.return_value = AsyncMock()
            mock_health.return_value.is_healthy = False
            mock_health.return_value.status = "unhealthy"
            mock_health.return_value.error_message = "Connection failed"
            mock_health.return_value.last_verified = datetime.utcnow()
            
            # Perform health check
            health_result = await self.advanced_session_manager._perform_health_check("health_test")
        
        self.assertFalse(health_result.is_healthy)
        self.assertEqual(health_result.status, "unhealthy")
        self.assertEqual(health_result.error_message, "Connection failed")
    
    async def test_worker_group_management(self):
        """Test worker group creation and management."""
        # Register session and create pairs
        await self.advanced_session_manager.register_session("worker_test", "+1234567890", max_pairs=5)
        
        pairs = []
        for i in range(10):  # Create 10 pairs (should create 2 worker groups)
            pair = ForwardingPair(
                name=f"pair_{i}",
                telegram_source_chat_id=100 + i,
                discord_channel_id=200 + i,
                telegram_dest_chat_id=300 + i,
                session_name="worker_test"
            )
            pair_id = await self.database.add_pair(pair)
            pairs.append(pair_id)
        
        # Initialize session to create worker groups
        await self.advanced_session_manager._ensure_worker_group_for_session("worker_test")
        
        # Check worker groups were created
        session_workers = [
            wg for wg in self.advanced_session_manager.worker_groups.values()
            if wg.session_name == "worker_test"
        ]
        
        # Should have created at least one worker group
        self.assertGreater(len(session_workers), 0)
        
        # Total pairs across workers should equal created pairs
        total_worker_pairs = sum(len(wg.pair_ids) for wg in session_workers)
        self.assertEqual(total_worker_pairs, 10)
    
    async def test_session_capacity_limits(self):
        """Test session capacity enforcement."""
        # Register session with limited capacity
        await self.advanced_session_manager.register_session("limited", "+1234567890", max_pairs=2)
        await self.database.update_session_health("limited", "healthy", datetime.utcnow())
        
        # Create pairs beyond capacity
        pair_ids = []
        for i in range(3):
            pair = ForwardingPair(
                name=f"capacity_pair_{i}",
                telegram_source_chat_id=400 + i,
                discord_channel_id=500 + i,
                telegram_dest_chat_id=600 + i,
                session_name="limited"
            )
            pair_id = await self.database.add_pair(pair)
            pair_ids.append(pair_id)
        
        # Try to reassign more pairs than capacity allows
        with patch.object(self.advanced_session_manager, '_perform_health_check') as mock_health:
            mock_health.return_value = AsyncMock()
            mock_health.return_value.is_healthy = True
            mock_health.return_value.status = "healthy"
            mock_health.return_value.last_verified = datetime.utcnow()
            
            result = await self.advanced_session_manager.bulk_reassign_session(pair_ids, "limited")
        
        # Should fail due to capacity limits
        self.assertFalse(result['success'])
        self.assertIn("exceed capacity", result.get('error', ''))
    
    async def test_session_deletion_with_force(self):
        """Test session deletion with force flag."""
        # Create session with pairs
        await self.advanced_session_manager.register_session("delete_test", "+1234567890")
        await self.advanced_session_manager.register_session("backup", "+9876543210")
        
        pair = ForwardingPair(
            name="delete_pair",
            telegram_source_chat_id=777,
            discord_channel_id=888,
            telegram_dest_chat_id=999,
            session_name="delete_test"
        )
        await self.database.add_pair(pair)
        
        # Mock session manager delete method
        self.session_manager.delete_session = AsyncMock(return_value=True)
        
        # Mock optimal session selection for reassignment
        with patch.object(self.advanced_session_manager, 'get_optimal_session_for_assignment') as mock_optimal:
            mock_optimal.return_value = "backup"
            
            # Force delete session
            success = await self.advanced_session_manager.delete_session("delete_test", force=True)
        
        self.assertTrue(success)
        
        # Verify session was marked as deleted
        session_info = await self.database.get_session_info("delete_test")
        self.assertEqual(session_info.health_status, "deleted")


if __name__ == '__main__':
    unittest.main()