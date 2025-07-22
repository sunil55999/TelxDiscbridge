"""Session manager for Telethon user sessions."""

import os
from typing import Dict, List, Optional, Any
from loguru import logger
from cryptography.fernet import Fernet
from telethon import TelegramClient, errors

from core.database import Database, SessionModel


class SessionManager:
    """Manages Telegram user sessions with encryption."""
    
    def __init__(self, database: Database, encryption_key: str):
        self.database = database
        # Store active clients for OTP verification
        self.pending_clients = {}
        
        # Initialize encryption
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY is not set. Please set it in your environment variables.")
        self.cipher = Fernet(encryption_key.encode())
    
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
                from sqlalchemy import select
                
                # Query by name since it's a unique field, not primary key
                result = await session.execute(
                    select(SessionModel).where(SessionModel.name == name)
                )
                session_model = result.scalar_one_or_none()
                
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
        """Create a new session entry (only if not exists)."""
        try:
            async with self.database.Session() as session:
                # Check if session already exists
                existing = await session.get(SessionModel, name)
                if existing:
                    logger.info(f"Session {name} already exists, skipping creation")
                    return True  # Return True since session exists
                
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
    
    async def authenticate_session(self, name: str, phone_number: str, verification_code: Optional[str] = None, phone_code_hash: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate a session with Telegram."""
        try:
            from config.settings import Settings
            settings = Settings()
            
            # Ensure sessions directory exists
            import os
            os.makedirs("sessions", exist_ok=True)
            
            client_key = f"{name}_{phone_number}"
            
            # If no verification code, start the authentication process
            if not verification_code:
                # Create new client for this session
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
                
                # Send code request and store client + phone_code_hash
                try:
                    result = await client.send_code_request(phone_number)
                    phone_code_hash = result.phone_code_hash
                    
                    # Store the client and phone_code_hash for later verification
                    self.pending_clients[client_key] = {
                        'client': client,
                        'phone_code_hash': phone_code_hash,
                        'phone_number': phone_number,
                        'session_name': name
                    }
                    
                    logger.info(f"Verification code sent to {phone_number}, client stored with key: {client_key}")
                    logger.info(f"Stored phone_code_hash: {phone_code_hash}")
                    logger.info(f"Total pending clients: {len(self.pending_clients)}")
                    return {
                        "success": False, 
                        "needs_code": True, 
                        "phone_code_hash": phone_code_hash,
                        "message": "Check your phone for verification code"
                    }
                except Exception as e:
                    logger.error(f"Failed to send code to {phone_number}: {e}")
                    await client.disconnect()
                    return {"success": False, "error": f"Failed to send verification code: {e}"}
            
            else:
                # Use stored client for verification
                logger.info(f"Looking for pending client with key: {client_key}")
                logger.info(f"Available pending clients: {list(self.pending_clients.keys())}")
                
                if client_key not in self.pending_clients:
                    logger.error(f"No pending client found for {name}, creating new one")
                    # Fallback: create new client (this might fail but worth trying)
                    client = TelegramClient(
                        f"sessions/{name}",
                        settings.telegram_api_id,
                        settings.telegram_api_hash
                    )
                    await client.connect()
                else:
                    # Use stored client
                    logger.info(f"Found pending client for {client_key}, using stored session")
                    client_info = self.pending_clients[client_key]
                    client = client_info['client']
                    stored_phone_code_hash = client_info['phone_code_hash']
                    
                    logger.info(f"Using stored phone_code_hash: {stored_phone_code_hash}")
                    
                    # Use stored phone_code_hash if not provided
                    if not phone_code_hash:
                        phone_code_hash = stored_phone_code_hash
                    
                    logger.info(f"Final phone_code_hash for verification: {phone_code_hash}")
                
                # Verify with code using phone_code_hash
                try:
                    await client.sign_in(phone_number, verification_code, phone_code_hash=phone_code_hash)
                    
                    # Save session data
                    session_string = client.session.save()
                    success = await self.save_session(name, phone_number, session_string)
                    if not success:
                        logger.warning(f"Failed to save session data for {name}, but authentication successful")
                    
                    logger.info(f"Successfully authenticated session {name}")
                    
                    # Clean up stored client
                    if client_key in self.pending_clients:
                        del self.pending_clients[client_key]
                    
                    await client.disconnect()
                    return {"success": True}
                    
                except errors.PhoneCodeInvalidError:
                    logger.error(f"Invalid verification code for {name}")
                    return {"success": False, "error": "Invalid verification code"}
                except errors.PhoneCodeExpiredError:
                    logger.error(f"Verification code expired for {name}")
                    # Clean up expired client
                    if client_key in self.pending_clients:
                        try:
                            await self.pending_clients[client_key]['client'].disconnect()
                        except:
                            pass
                        del self.pending_clients[client_key]
                    return {"success": False, "error": "Verification code expired"}
                except Exception as e:
                    logger.error(f"Authentication failed for {name}: {e}")
                    return {"success": False, "error": str(e)}
                finally:
                    # Always try to disconnect if we created a new client
                    if client_key not in self.pending_clients:
                        try:
                            await client.disconnect()
                        except:
                            pass
            
        except Exception as e:
            logger.error(f"Failed to authenticate session {name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def cleanup_pending_client(self, name: str, phone_number: str) -> None:
        """Clean up a pending client session."""
        client_key = f"{name}_{phone_number}"
        if client_key in self.pending_clients:
            try:
                client = self.pending_clients[client_key]['client']
                await client.disconnect()
                logger.info(f"Disconnected pending client for {name}")
            except:
                pass
            del self.pending_clients[client_key]
    
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