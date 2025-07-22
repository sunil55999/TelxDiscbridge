"""Telegram source client using Telethon for user sessions."""

from typing import Dict, List, Optional, Callable

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import Message
from loguru import logger

from core.database import Database, ForwardingPair
from core.session_manager import SessionManager
from core.message_formatter import MessageFormatter
from utils.filters import MessageFilter


class TelegramSource:
    """Handles Telegram source connections and message receiving."""
    
    def __init__(self, session_manager: SessionManager, database: Database):
        self.session_manager = session_manager
        self.database = database
        self.clients: Dict[str, TelegramClient] = {}
        self.active_pairs: List[ForwardingPair] = []
        self.message_formatter = MessageFormatter()
        self.message_filter = MessageFilter()
        self.running = False
        
        # Callbacks for message forwarding
        self.on_message_received: Optional[Callable] = None
    
    async def start(self):
        """Start the Telegram source clients."""
        if self.running:
            logger.warning("Telegram source is already running")
            return
        
        logger.info("Starting Telegram source...")
        self.running = True
        
        try:
            # Load active forwarding pairs
            await self.reload_pairs()
            
            # Start clients for each unique session
            await self.start_clients()
            
            logger.info("Telegram source started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Telegram source: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Stop all Telegram source clients."""
        if not self.running:
            return
        
        logger.info("Stopping Telegram source...")
        self.running = False
        
        # Disconnect all clients
        for session_name, client in self.clients.items():
            try:
                if client.is_connected():
                    await client.disconnect()
                logger.debug(f"Disconnected client for session: {session_name}")
            except Exception as e:
                logger.error(f"Error disconnecting client {session_name}: {e}")
        
        self.clients.clear()
        logger.info("Telegram source stopped")
    
    async def reload_pairs(self):
        """Reload active forwarding pairs from database."""
        try:
            self.active_pairs = await self.database.get_all_pairs()
            logger.info(f"Loaded {len(self.active_pairs)} active forwarding pairs")
        except Exception as e:
            logger.error(f"Failed to reload pairs: {e}")
            self.active_pairs = []
    
    async def start_clients(self):
        """Start Telegram clients for unique sessions."""
        # Get unique session names from active pairs
        unique_sessions = set(pair.session_name for pair in self.active_pairs)
        
        for session_name in unique_sessions:
            try:
                await self.start_client_for_session(session_name)
            except Exception as e:
                logger.error(f"Failed to start client for session {session_name}: {e}")
    
    async def start_client_for_session(self, session_name: str):
        """Start a Telegram client for a specific session."""
        if session_name in self.clients:
            logger.debug(f"Client already exists for session: {session_name}")
            return
        
        client = None
        try:
            # Get session data
            session_info = await self.session_manager.get_session(session_name)
            if not session_info:
                logger.error(f"Session not found: {session_name}")
                return
            
            # Create client with session data
            client = TelegramClient(
                StringSession(session_info.get('session_data', '')),
                api_id=session_info.get('api_id'),
                api_hash=session_info.get('api_hash')
            )
            
            # Connect client
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.error(f"Session not authorized: {session_name}")
                return
            
            # Register message handler
            client.add_event_handler(
                self._handle_message,
                events.NewMessage()
            )
            
            # Register message edit handler
            client.add_event_handler(
                self._handle_message_edit,
                events.MessageEdited()
            )
            
            # Register message delete handler
            client.add_event_handler(
                self._handle_message_delete,
                events.MessageDeleted()
            )
            
            self.clients[session_name] = client
            
            # Get pairs for this session and add chat filters
            session_pairs = [p for p in self.active_pairs if p.session_name == session_name]
            chat_ids = [p.telegram_source_chat_id for p in session_pairs]
            
            logger.info(f"Started client for session {session_name} monitoring {len(chat_ids)} chats")
            
        except Exception as e:
            logger.error(f"Failed to start client for session {session_name}: {e}")
            if session_name in self.clients:
                del self.clients[session_name]
            raise
        finally:
            if client and not client.is_connected():
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting client {session_name} in finally block: {e}")

    async def _handle_message(self, event):
        """Handle new messages from Telegram."""
        try:
            message = event.message
            chat_id = message.peer_id.channel_id if hasattr(message.peer_id, 'channel_id') else message.peer_id.chat_id if hasattr(message.peer_id, 'chat_id') else message.peer_id.user_id
            
            # Find matching pairs for this chat
            matching_pairs = [
                pair for pair in self.active_pairs 
                if pair.telegram_source_chat_id == chat_id and pair.is_active
            ]
            
            if not matching_pairs:
                return
            
            logger.debug(f"Processing message {message.id} from chat {chat_id}")
            
            # Process message for each matching pair
            for pair in matching_pairs:
                try:
                    await self._process_message_for_pair(message, pair)
                except Exception as e:
                    logger.error(f"Failed to process message for pair {pair.id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_message_edit(self, event):
        """Handle message edits from Telegram."""
        try:
            # Similar logic to new messages but for edits
            message = event.message
            chat_id = message.peer_id.channel_id if hasattr(message.peer_id, 'channel_id') else message.peer_id.chat_id if hasattr(message.peer_id, 'chat_id') else message.peer_id.user_id
            
            # Find matching pairs
            matching_pairs = [
                pair for pair in self.active_pairs 
                if pair.telegram_source_chat_id == chat_id and pair.is_active
            ]
            
            for pair in matching_pairs:
                # Check if we have a mapping for this message
                mapping = await self.database.get_message_mapping(message.id, pair.id)
                if mapping and self.on_message_received:
                    # Forward the edit
                    formatted_message = await self.message_formatter.format_message(message, pair)
                    if formatted_message:
                        await self.on_message_received('edit', {
                            'pair': pair,
                            'original_message': message,
                            'formatted_message': formatted_message,
                            'mapping': mapping
                        })
                        
        except Exception as e:
            logger.error(f"Error handling message edit: {e}")
    
    async def _handle_message_delete(self, event):
        """Handle message deletions from Telegram."""
        try:
            # Handle message deletions
            for deleted_id in event.deleted_ids:
                # Find pairs that might have this message
                for pair in self.active_pairs:
                    mapping = await self.database.get_message_mapping(deleted_id, pair.id)
                    if mapping and self.on_message_received:
                        await self.on_message_received('delete', {
                            'pair': pair,
                            'deleted_id': deleted_id,
                            'mapping': mapping
                        })
                        
        except Exception as e:
            logger.error(f"Error handling message deletion: {e}")
    
    async def _process_message_for_pair(self, message: Message, pair: ForwardingPair):
        """Process a message for a specific forwarding pair."""
        try:
            # Apply filters
            if not await self.message_filter.should_forward_message(message, pair):
                logger.debug(f"Message filtered out for pair {pair.id}")
                return
            
            # Format message
            formatted_message = await self.message_formatter.format_message(message, pair)
            if not formatted_message:
                logger.debug(f"Message could not be formatted for pair {pair.id}")
                return
            
            # Forward to next stage if callback is set
            if self.on_message_received:
                await self.on_message_received('new', {
                    'pair': pair,
                    'original_message': message,
                    'formatted_message': formatted_message
                })
            
        except Exception as e:
            logger.error(f"Error processing message for pair {pair.id}: {e}")
    
    def set_message_callback(self, callback: Callable):
        """Set the callback function for handling received messages."""
        self.on_message_received = callback
    
    async def get_chat_info(self, session_name: str, chat_id: int) -> Optional[Dict]:
        """Get information about a chat."""
        if session_name not in self.clients:
            logger.error(f"Client not found for session: {session_name}")
            return None
        
        try:
            client = self.clients[session_name]
            entity = await client.get_entity(chat_id)
            
            return {
                'id': entity.id,
                'title': getattr(entity, 'title', getattr(entity, 'first_name', 'Unknown')),
                'type': type(entity).__name__,
                'username': getattr(entity, 'username', None)
            }
            
        except Exception as e:
            logger.error(f"Failed to get chat info for {chat_id}: {e}")
            return None
    
    async def test_session_access(self, session_name: str, chat_ids: List[int]) -> Dict[int, bool]:
        """Test if a session has access to specific chats."""
        results = {}
        
        if session_name not in self.clients:
            logger.error(f"Client not found for session: {session_name}")
            return {chat_id: False for chat_id in chat_ids}
        
        client = self.clients[session_name]
        
        for chat_id in chat_ids:
            try:
                await client.get_entity(chat_id)
                results[chat_id] = True
            except Exception as e:
                logger.error(f"Session {session_name} cannot access chat {chat_id}: {e}")
                results[chat_id] = False
        
        return results
    
    async def restart_client(self, session_name: str):
        """Restart a specific client."""
        try:
            # Stop existing client
            if session_name in self.clients:
                await self.clients[session_name].disconnect()
                del self.clients[session_name]
            
            # Restart client
            await self.start_client_for_session(session_name)
            logger.info(f"Restarted client for session: {session_name}")
            
        except Exception as e:
            logger.error(f"Failed to restart client for session {session_name}: {e}")
            raise
