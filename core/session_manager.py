"""Session manager for Telethon user sessions."""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger
from cryptography.fernet import Fernet

from core.database import Database, SessionModel


class SessionManager:
    """Manages Telegram user sessions with encryption."""
    
    def __init__(self, database: Database, encryption_key: Optional[str] = None):
        self.database = database
        
        # Initialize encryption
        if encryption_key:
            self.cipher = Fernet(encryption_key.encode())
        else:
            # Generate or load encryption key
            key_file = "session_key.key"
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    self.cipher = Fernet(f.read())
            else:
                key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(key)
                self.cipher = Fernet(key)
                logger.info("Generated new session encryption key")
    
    async def save_session(self, name: str, phone_number: str, session_data: str) -> bool:
        """Save encrypted session data."""
        try:
            # Encrypt session data
            encrypted_data = self.cipher.encrypt(session_data.encode()).decode()
            
            async with self.database.Session() as session:
                # Check if session exists
                existing = await session.get(SessionModel, name)
                if existing:
                    existing.session_data = encrypted_data
                    existing.phone_number = phone_number
                    existing.is_active = True
                else:
                    session_model = SessionModel(
                        name=name,
                        phone_number=phone_number,
                        session_data=encrypted_data,
                        is_active=True
                    )
                    session.add(session_model)
                
                await session.commit()
                logger.info(f"Session {name} saved successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save session {name}: {e}")
            return False
    
    async def get_session(self, name: str) -> Optional[Dict[str, Any]]:
        """Get and decrypt session data."""
        try:
            async with self.database.Session() as session:
                session_model = await session.get(SessionModel, name)
                if not session_model or not session_model.is_active:
                    return None
                
                if not session_model.session_data:
                    return {
                        'name': session_model.name,
                        'phone_number': session_model.phone_number,
                        'session_data': None,
                        'created_at': session_model.created_at
                    }
                
                # Decrypt session data
                decrypted_data = self.cipher.decrypt(session_model.session_data.encode()).decode()
                
                return {
                    'name': session_model.name,
                    'phone_number': session_model.phone_number, 
                    'session_data': decrypted_data,
                    'created_at': session_model.created_at
                }
                
        except Exception as e:
            logger.error(f"Failed to get session {name}: {e}")
            return None
    
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available sessions."""
        try:
            async with self.database.Session() as session:
                from sqlalchemy import select
                result = await session.execute(select(SessionModel))
                sessions = result.scalars().all()
                
                return [
                    {
                        'name': s.name,
                        'phone_number': s.phone_number,
                        'is_active': s.is_active,
                        'created_at': s.created_at,
                        'updated_at': s.updated_at
                    }
                    for s in sessions
                ]
                
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    async def delete_session(self, name: str) -> bool:
        """Delete a session."""
        try:
            async with self.database.Session() as session:
                session_model = await session.get(SessionModel, name)
                if session_model:
                    await session.delete(session_model)
                    await session.commit()
                    logger.info(f"Session {name} deleted")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete session {name}: {e}")
            return False
    
    async def deactivate_session(self, name: str) -> bool:
        """Deactivate a session without deleting."""
        try:
            async with self.database.Session() as session:
                session_model = await session.get(SessionModel, name)
                if session_model:
                    session_model.is_active = False
                    await session.commit()
                    logger.info(f"Session {name} deactivated")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to deactivate session {name}: {e}")
            return False
    
    async def validate_session(self, name: str) -> bool:
        """Validate if a session is active and accessible."""
        session_info = await self.get_session(name)
        return session_info is not None and session_info.get('session_data') is not None