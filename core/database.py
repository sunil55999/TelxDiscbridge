"""Database operations for the forwarding bot."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from loguru import logger

Base = declarative_base()


@dataclass
class ForwardingPair:
    """Forwarding pair configuration."""
    id: Optional[int] = None
    name: str = ""
    telegram_source_chat_id: int = 0
    discord_channel_id: int = 0
    telegram_dest_chat_id: int = 0
    session_name: str = ""
    session_id: Optional[int] = None  # Reference to session ID
    is_active: bool = True
    keyword_filters: List[str] = None
    media_enabled: bool = True
    worker_id: Optional[str] = None  # Associated worker process ID
    health_status: str = "active"  # active, paused, error, reassigning
    last_message_time: Optional[datetime] = None
    message_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.keyword_filters is None:
            self.keyword_filters = []


@dataclass
class SessionInfo:
    """Enhanced session information for management."""
    id: Optional[int] = None
    name: str = ""
    phone_number: Optional[str] = None
    is_active: bool = True
    health_status: str = "unknown"
    last_verified: Optional[datetime] = None
    pair_count: int = 0
    worker_id: Optional[str] = None
    max_pairs: int = 30
    priority: int = 1
    metadata_info: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class MessageMapping:
    """Message ID mapping for reply threading."""
    id: Optional[int] = None
    pair_id: int = 0
    telegram_source_id: int = 0
    discord_message_id: int = 0
    telegram_dest_id: int = 0
    created_at: Optional[datetime] = None


class ForwardingPairModel(Base):
    """SQLAlchemy model for enhanced forwarding pairs."""
    __tablename__ = 'forwarding_pairs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    telegram_source_chat_id = Column(String(50), nullable=False)
    discord_channel_id = Column(String(50), nullable=False)
    telegram_dest_chat_id = Column(String(50), nullable=False)
    session_name = Column(String(100), nullable=False)
    session_id = Column(Integer, nullable=True)  # Foreign key to sessions
    is_active = Column(Boolean, default=True)
    keyword_filters = Column(JSON, default=list)
    media_enabled = Column(Boolean, default=True)
    worker_id = Column(String(50), nullable=True)
    health_status = Column(String(20), default='active')
    last_message_time = Column(DateTime, nullable=True)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MessageMappingModel(Base):
    """SQLAlchemy model for message mappings."""
    __tablename__ = 'message_mappings'
    
    id = Column(Integer, primary_key=True)
    pair_id = Column(Integer, nullable=False)
    telegram_source_id = Column(String(50), nullable=False)
    discord_message_id = Column(String(50), nullable=False)
    telegram_dest_id = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SessionModel(Base):
    """SQLAlchemy model for enhanced session storage."""
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    phone_number = Column(String(20), nullable=True)
    session_data = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    health_status = Column(String(20), default='unknown')  # healthy, unhealthy, expired, unauthorized
    last_verified = Column(DateTime, nullable=True)
    pair_count = Column(Integer, default=0)  # Number of pairs using this session
    worker_id = Column(String(50), nullable=True)  # Associated worker process ID
    max_pairs = Column(Integer, default=30)  # Maximum pairs for this session
    priority = Column(Integer, default=1)  # Session priority for assignment
    metadata_info = Column(JSON, nullable=True)  # Additional session metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Database:
    """Database manager for the forwarding bot."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.Session = None
        
    async def initialize(self):
        """Initialize database connection and create tables."""
        try:
            # Handle SQLite URLs for async
            if self.database_url.startswith('sqlite:'):
                # Convert to aiosqlite for async support
                self.database_url = self.database_url.replace('sqlite:', 'sqlite+aiosqlite:', 1)
            
            self.engine = create_async_engine(self.database_url, echo=False)
            self.Session = sessionmaker(bind=self.engine, class_=AsyncSession, expire_on_commit=False)
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info(f"Database initialized: {self.database_url}")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
    
    async def add_pair(self, pair: ForwardingPair) -> int:
        """Add a new forwarding pair."""
        async with self.Session() as session:
            try:
                db_pair = ForwardingPairModel(
                    name=pair.name,
                    telegram_source_chat_id=str(pair.telegram_source_chat_id),
                    discord_channel_id=str(pair.discord_channel_id),
                    telegram_dest_chat_id=str(pair.telegram_dest_chat_id),
                    session_name=pair.session_name,
                    session_id=pair.session_id,
                    is_active=pair.is_active,
                    keyword_filters=pair.keyword_filters or [],
                    media_enabled=pair.media_enabled,
                    worker_id=pair.worker_id,
                    health_status=pair.health_status,
                    message_count=pair.message_count
                )
                
                session.add(db_pair)
                await session.commit()
                await session.refresh(db_pair)
                
                logger.info(f"Added forwarding pair: {pair.name} (ID: {db_pair.id})")
                return db_pair.id
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to add pair: {e}")
                raise
    
    async def get_pair(self, pair_id: int) -> Optional[ForwardingPair]:
        """Get a forwarding pair by ID."""
        async with self.Session() as session:
            try:
                result = await session.get(ForwardingPairModel, pair_id)
                if result:
                    return ForwardingPair(
                        id=result.id,
                        name=result.name,
                        telegram_source_chat_id=int(result.telegram_source_chat_id),
                        discord_channel_id=int(result.discord_channel_id),
                        telegram_dest_chat_id=int(result.telegram_dest_chat_id),
                        session_name=result.session_name,
                        is_active=result.is_active,
                        keyword_filters=result.keyword_filters or [],
                        media_enabled=result.media_enabled,
                        created_at=result.created_at,
                        updated_at=result.updated_at,
                        session_id=result.session_id,
                        worker_id=result.worker_id,
                        health_status=result.health_status,
                        last_message_time=result.last_message_time,
                        message_count=result.message_count
                    )
                return None
                
            except Exception as e:
                logger.error(f"Failed to get pair {pair_id}: {e}")
                return None
    
    async def get_all_pairs(self) -> List[ForwardingPair]:
        """Get all forwarding pairs."""
        async with self.Session() as session:
            try:
                result = await session.execute(text("SELECT * FROM forwarding_pairs WHERE is_active = 1"))
                pairs = []
                
                for row in result:
                    pairs.append(ForwardingPair(
                        id=row.id,
                        name=row.name,
                        telegram_source_chat_id=int(row.telegram_source_chat_id),
                        discord_channel_id=int(row.discord_channel_id),
                        telegram_dest_chat_id=int(row.telegram_dest_chat_id),
                        session_name=row.session_name,
                        is_active=bool(row.is_active),
                        keyword_filters=json.loads(row.keyword_filters) if row.keyword_filters else [],
                        media_enabled=bool(row.media_enabled),
                        created_at=row.created_at,
                        updated_at=row.updated_at
                    ))
                
                return pairs
                
            except Exception as e:
                logger.error(f"Failed to get all pairs: {e}")
                return []
    
    async def update_pair(self, pair: ForwardingPair) -> bool:
        """Update a forwarding pair."""
        async with self.Session() as session:
            try:
                result = await session.get(ForwardingPairModel, pair.id)
                if not result:
                    return False
                
                result.name = pair.name
                result.telegram_source_chat_id = str(pair.telegram_source_chat_id)
                result.discord_channel_id = str(pair.discord_channel_id)
                result.telegram_dest_chat_id = str(pair.telegram_dest_chat_id)
                result.session_name = pair.session_name
                result.session_id = pair.session_id
                result.is_active = pair.is_active
                result.keyword_filters = pair.keyword_filters or []
                result.media_enabled = pair.media_enabled
                result.worker_id = pair.worker_id
                result.health_status = pair.health_status
                result.message_count = pair.message_count
                result.updated_at = datetime.utcnow()
                
                await session.commit()
                logger.info(f"Updated forwarding pair: {pair.name} (ID: {pair.id})")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update pair {pair.id}: {e}")
                return False
    
    async def delete_pair(self, pair_id: int) -> bool:
        """Delete a forwarding pair."""
        async with self.Session() as session:
            try:
                result = await session.get(ForwardingPairModel, pair_id)
                if not result:
                    return False
                
                # Soft delete by setting is_active to False
                result.is_active = False
                result.updated_at = datetime.utcnow()
                
                await session.commit()
                logger.info(f"Deleted forwarding pair ID: {pair_id}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete pair {pair_id}: {e}")
                return False
    
    async def add_message_mapping(self, mapping: MessageMapping) -> int:
        """Add a message mapping."""
        async with self.Session() as session:
            try:
                db_mapping = MessageMappingModel(
                    pair_id=mapping.pair_id,
                    telegram_source_id=str(mapping.telegram_source_id),
                    discord_message_id=str(mapping.discord_message_id),
                    telegram_dest_id=str(mapping.telegram_dest_id)
                )
                
                session.add(db_mapping)
                await session.commit()
                await session.refresh(db_mapping)
                
                return db_mapping.id
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to add message mapping: {e}")
                raise
    
    async def get_message_mapping(self, telegram_source_id: int, pair_id: int) -> Optional[MessageMapping]:
        """Get message mapping by source ID and pair ID."""
        async with self.Session() as session:
            try:
                result = await session.execute(
                    text("SELECT * FROM message_mappings WHERE telegram_source_id = :source_id AND pair_id = :pair_id"),
                    {"source_id": str(telegram_source_id), "pair_id": pair_id}
                )
                row = result.first()
                
                if row:
                    return MessageMapping(
                        id=row.id,
                        pair_id=row.pair_id,
                        telegram_source_id=int(row.telegram_source_id),
                        discord_message_id=int(row.discord_message_id),
                        telegram_dest_id=int(row.telegram_dest_id),
                        created_at=row.created_at
                    )
                return None
                
            except Exception as e:
                logger.error(f"Failed to get message mapping: {e}")
                return None
    
    async def cleanup_old_mappings(self, days: int = 30):
        """Clean up old message mappings."""
        async with self.Session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                await session.execute(
                    text("DELETE FROM message_mappings WHERE created_at < :cutoff"),
                    {"cutoff": cutoff_date}
                )
                await session.commit()
                logger.info(f"Cleaned up message mappings older than {days} days")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to cleanup old mappings: {e}")
    
    # Enhanced Session Management Methods
    
    async def add_session_info(self, session_info: SessionInfo) -> int:
        """Add enhanced session information."""
        async with self.Session() as session:
            try:
                db_session = SessionModel(
                    name=session_info.name,
                    phone_number=session_info.phone_number,
                    is_active=session_info.is_active,
                    health_status=session_info.health_status,
                    pair_count=session_info.pair_count,
                    worker_id=session_info.worker_id,
                    max_pairs=session_info.max_pairs,
                    priority=session_info.priority,
                    metadata_info=session_info.metadata_info or {}
                )
                
                session.add(db_session)
                await session.commit()
                await session.refresh(db_session)
                
                logger.info(f"Added session info: {session_info.name} (ID: {db_session.id})")
                return db_session.id
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to add session info: {e}")
                raise
    
    async def get_session_info(self, session_name: str) -> Optional[SessionInfo]:
        """Get enhanced session information by name."""
        async with self.Session() as session:
            try:
                result = await session.execute(
                    text("SELECT * FROM sessions WHERE name = :name"),
                    {"name": session_name}
                )
                row = result.first()
                
                if row:
                    return SessionInfo(
                        id=row.id,
                        name=row.name,
                        phone_number=row.phone_number,
                        is_active=bool(row.is_active),
                        health_status=row.health_status,
                        last_verified=row.last_verified,
                        pair_count=row.pair_count,
                        worker_id=row.worker_id,
                        max_pairs=row.max_pairs,
                        priority=row.priority,
                        metadata_info=json.loads(row.metadata_info) if row.metadata_info else {},
                        created_at=row.created_at,
                        updated_at=row.updated_at
                    )
                return None
                
            except Exception as e:
                logger.error(f"Failed to get session info {session_name}: {e}")
                return None
    
    async def get_all_sessions(self) -> List[SessionInfo]:
        """Get all session information."""
        async with self.Session() as session:
            try:
                result = await session.execute(text("SELECT * FROM sessions ORDER BY priority DESC, created_at ASC"))
                sessions = []
                
                for row in result:
                    sessions.append(SessionInfo(
                        id=row.id,
                        name=row.name,
                        phone_number=row.phone_number,
                        is_active=bool(row.is_active),
                        health_status=row.health_status,
                        last_verified=row.last_verified,
                        pair_count=row.pair_count,
                        worker_id=row.worker_id,
                        max_pairs=row.max_pairs,
                        priority=row.priority,
                        metadata_info=json.loads(row.metadata_info) if row.metadata_info else {},
                        created_at=row.created_at,
                        updated_at=row.updated_at
                    ))
                
                return sessions
                
            except Exception as e:
                logger.error(f"Failed to get all sessions: {e}")
                return []
    
    async def update_session_health(self, session_name: str, health_status: str, last_verified: Optional[datetime] = None) -> bool:
        """Update session health status."""
        async with self.Session() as session:
            try:
                result = await session.execute(
                    text("SELECT * FROM sessions WHERE name = :name"),
                    {"name": session_name}
                )
                session_row = result.first()
                
                if not session_row:
                    return False
                
                update_data = {
                    "health_status": health_status,
                    "updated_at": datetime.utcnow()
                }
                
                if last_verified:
                    update_data["last_verified"] = last_verified
                
                await session.execute(
                    text("UPDATE sessions SET health_status = :health_status, last_verified = :last_verified, updated_at = :updated_at WHERE name = :name"),
                    {
                        "health_status": health_status,
                        "last_verified": last_verified or datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        "name": session_name
                    }
                )
                await session.commit()
                
                logger.info(f"Updated session health: {session_name} -> {health_status}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update session health {session_name}: {e}")
                return False
    
    async def get_pairs_by_session(self, session_name: str) -> List[ForwardingPair]:
        """Get all pairs assigned to a specific session."""
        async with self.Session() as session:
            try:
                result = await session.execute(
                    text("SELECT * FROM forwarding_pairs WHERE session_name = :session_name AND is_active = 1"),
                    {"session_name": session_name}
                )
                pairs = []
                
                for row in result:
                    pairs.append(ForwardingPair(
                        id=row.id,
                        name=row.name,
                        telegram_source_chat_id=int(row.telegram_source_chat_id),
                        discord_channel_id=int(row.discord_channel_id),
                        telegram_dest_chat_id=int(row.telegram_dest_chat_id),
                        session_name=row.session_name,
                        session_id=row.session_id,
                        is_active=bool(row.is_active),
                        keyword_filters=json.loads(row.keyword_filters) if row.keyword_filters else [],
                        media_enabled=bool(row.media_enabled),
                        worker_id=row.worker_id,
                        health_status=row.health_status,
                        last_message_time=row.last_message_time,
                        message_count=row.message_count,
                        created_at=row.created_at,
                        updated_at=row.updated_at
                    ))
                
                return pairs
                
            except Exception as e:
                logger.error(f"Failed to get pairs for session {session_name}: {e}")
                return []
    
    async def bulk_reassign_session(self, pair_ids: List[int], new_session_name: str, new_session_id: Optional[int] = None) -> bool:
        """Bulk reassign pairs to a new session."""
        async with self.Session() as session:
            try:
                for pair_id in pair_ids:
                    await session.execute(
                        text("UPDATE forwarding_pairs SET session_name = :session_name, session_id = :session_id, health_status = 'reassigning', updated_at = :updated_at WHERE id = :pair_id"),
                        {
                            "session_name": new_session_name,
                            "session_id": new_session_id,
                            "updated_at": datetime.utcnow(),
                            "pair_id": pair_id
                        }
                    )
                
                await session.commit()
                
                logger.info(f"Bulk reassigned {len(pair_ids)} pairs to session {new_session_name}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to bulk reassign pairs: {e}")
                return False
    
    async def update_session_pair_count(self, session_name: str) -> bool:
        """Update the pair count for a session."""
        async with self.Session() as session:
            try:
                # Count active pairs for this session
                result = await session.execute(
                    text("SELECT COUNT(*) as count FROM forwarding_pairs WHERE session_name = :session_name AND is_active = 1"),
                    {"session_name": session_name}
                )
                count = result.scalar()
                
                # Update session pair count
                await session.execute(
                    text("UPDATE sessions SET pair_count = :count, updated_at = :updated_at WHERE name = :name"),
                    {
                        "count": count,
                        "updated_at": datetime.utcnow(),
                        "name": session_name
                    }
                )
                await session.commit()
                
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update session pair count for {session_name}: {e}")
                return False
    
    async def store_session(self, name: str, phone_number: str, session_data: str) -> bool:
        """Store session data."""
        async with self.Session() as session:
            try:
                # Check if session exists
                result = await session.execute(
                    text("SELECT * FROM sessions WHERE name = :name"),
                    {"name": name}
                )
                existing = result.first()
                
                if existing:
                    # Update existing session
                    await session.execute(
                        text("UPDATE sessions SET phone_number = :phone, session_data = :data, updated_at = :updated WHERE name = :name"),
                        {"phone": phone_number, "data": session_data, "updated": datetime.utcnow(), "name": name}
                    )
                else:
                    # Create new session
                    db_session = SessionModel(
                        name=name,
                        phone_number=phone_number,
                        session_data=session_data
                    )
                    session.add(db_session)
                
                await session.commit()
                logger.info(f"Stored session: {name}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to store session {name}: {e}")
                return False
    
    async def get_session(self, name: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        async with self.Session() as session:
            try:
                result = await session.execute(
                    text("SELECT * FROM sessions WHERE name = :name AND is_active = 1"),
                    {"name": name}
                )
                row = result.first()
                
                if row:
                    return {
                        "name": row.name,
                        "phone_number": row.phone_number,
                        "session_data": row.session_data,
                        "is_active": row.is_active,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at
                    }
                return None
                
            except Exception as e:
                logger.error(f"Failed to get session {name}: {e}")
                return None
