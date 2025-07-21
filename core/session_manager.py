"""Session manager for Telethon user sessions."""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger
from cryptography.fernet import Fernet
from telethon import TelegramClient, errors

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
    
    async def create_session(self, name: str, phone_number: str) -> bool:
        """Create a new session entry."""
        try:
            async with self.database.Session() as session:
                # Check if session already exists
                existing = await session.get(SessionModel, name)
                if existing:
                    logger.warning(f"Session {name} already exists")
                    return False
                
                # Create new session without session data (to be filled during authentication)
                session_model = SessionModel(
                    name=name,
                    phone_number=phone_number,
                    session_data=None,
                    is_active=False
                )
                session.add(session_model)
                await session.commit()
                
                logger.info(f"Session {name} created for phone {phone_number}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create session {name}: {e}")
            return False
    
    async def authenticate_session(self, name: str, phone_number: str, verification_code: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate a session with Telegram."""
        try:
            from config.settings import Settings
            settings = Settings()
            
            # Create Telethon client
            client = TelegramClient(
                f"sessions/{name}",
                settings.telegram_api_id,
                settings.telegram_api_hash
            )
            
            await client.connect()
            
            # Check if already authenticated
            if await client.is_user_authorized():
                logger.info(f"Session {name} already authenticated")
                await client.disconnect()
                return {"success": True}
            
            # Start authentication process
            if not verification_code:
                # Send code request
                try:
                    await client.send_code_request(phone_number)
                    logger.info(f"Verification code sent to {phone_number}")
                    await client.disconnect()
                    return {"success": False, "needs_code": True, "message": "Check your phone for verification code"}
                except Exception as e:
                    logger.error(f"Failed to send code to {phone_number}: {e}")
                    await client.disconnect()
                    return {"success": False, "error": f"Failed to send verification code: {e}"}
            else:
                # Verify with code
                try:
                    await client.sign_in(phone_number, verification_code)
                    
                    # Save session data
                    session_string = client.session.save()
                    await self.save_session(name, phone_number, session_string)
                    
                    logger.info(f"Successfully authenticated session {name}")
                    await client.disconnect()
                    return {"success": True}
                    
                except errors.PhoneCodeInvalidError:
                    logger.error(f"Invalid verification code for {name}")
                    await client.disconnect()
                    return {"success": False, "error": "Invalid verification code"}
                except errors.PhoneCodeExpiredError:
                    logger.error(f"Verification code expired for {name}")
                    await client.disconnect()
                    return {"success": False, "error": "Verification code expired"}
                except Exception as e:
                    logger.error(f"Authentication failed for {name}: {e}")
                    await client.disconnect()
                    return {"success": False, "error": str(e)}
            
        except Exception as e:
            logger.error(f"Failed to authenticate session {name}: {e}")
            return {"success": False, "error": str(e)}
    
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