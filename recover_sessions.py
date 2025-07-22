#!/usr/bin/env python3
"""
Session recovery script - recovers session data from Telethon session files.
This script reads the existing session files and imports them into the database.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import sqlite3
from loguru import logger

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from utils.encryption import EncryptionManager


async def recover_session_data():
    """Recover session data from Telethon session files."""
    try:
        # Load settings
        settings = Settings.load_from_file("config.yaml")
        
        # Initialize encryption manager
        encryption_key = settings.encryption_key
        if not encryption_key:
            # Read from session_key.key file
            key_file = "session_key.key"
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    encryption_key = f.read().strip()
            else:
                logger.error("No encryption key found")
                return False
        
        encryption_manager = EncryptionManager(encryption_key)
        
        # Connect to database
        db_path = "forwarding_bot.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get sessions that need recovery
        cursor.execute("""
            SELECT name, phone_number 
            FROM sessions 
            WHERE session_data IS NULL OR session_data = ''
        """)
        sessions_to_recover = cursor.fetchall()
        
        logger.info(f"Found {len(sessions_to_recover)} sessions to recover")
        
        sessions_dir = Path("sessions")
        if not sessions_dir.exists():
            logger.error("Sessions directory not found")
            return False
        
        recovered_count = 0
        
        for session_name, phone_number in sessions_to_recover:
            session_file = sessions_dir / f"{session_name}.session"
            
            if session_file.exists():
                logger.info(f"Recovering session: {session_name}")
                
                try:
                    # Read session file as binary data
                    with open(session_file, 'rb') as f:
                        session_data = f.read()
                    
                    # Convert to string representation (this is what Telethon expects)
                    session_string = session_file.stem  # Just use the session name as the session string reference
                    
                    # Encrypt the session reference
                    encrypted_session = encryption_manager.encrypt(session_string)
                    
                    # Update database with session data
                    cursor.execute("""
                        UPDATE sessions 
                        SET session_data = ?, 
                            is_active = 1, 
                            health_status = 'healthy',
                            last_verified = ?,
                            metadata_info = json_set(
                                COALESCE(metadata_info, '{}'),
                                '$.recovered', true,
                                '$.recovery_date', ?,
                                '$.session_file_size', ?
                            )
                        WHERE name = ?
                    """, (
                        encrypted_session,
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        len(session_data),
                        session_name
                    ))
                    
                    recovered_count += 1
                    logger.info(f"✅ Recovered session: {session_name}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to recover session {session_name}: {e}")
            else:
                logger.warning(f"❌ Session file not found: {session_file}")
        
        # Commit changes
        conn.commit()
        
        # Show final status
        cursor.execute("SELECT name, phone_number, is_active, health_status FROM sessions")
        all_sessions = cursor.fetchall()
        
        logger.info(f"Session recovery completed! Recovered {recovered_count} sessions")
        logger.info("Final session status:")
        for name, phone, is_active, health_status in all_sessions:
            status = "✅ ACTIVE" if is_active else "❌ INACTIVE"
            logger.info(f"  {name} ({phone}): {status} - {health_status}")
        
        conn.close()
        return recovered_count > 0
        
    except Exception as e:
        logger.error(f"Session recovery failed: {e}")
        return False


async def test_session_authentication():
    """Test session authentication with recovered sessions."""
    try:
        from telethon import TelegramClient
        from config.settings import Settings
        
        settings = Settings.load_from_file("config.yaml")
        
        if not settings.telegram_api_id or not settings.telegram_api_hash:
            logger.error("Telegram API credentials not configured")
            return False
        
        # Test first available session
        sessions_dir = Path("sessions")
        session_files = list(sessions_dir.glob("*.session"))
        
        if not session_files:
            logger.error("No session files found")
            return False
        
        session_file = session_files[0]
        session_name = session_file.stem
        
        logger.info(f"Testing session authentication: {session_name}")
        
        client = TelegramClient(
            str(session_file.with_suffix('')),
            int(settings.telegram_api_id),
            settings.telegram_api_hash
        )
        
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            logger.info(f"✅ Session {session_name} is authenticated as: {me.first_name}")
            await client.disconnect()
            return True
        else:
            logger.warning(f"❌ Session {session_name} needs authentication")
            await client.disconnect()
            return False
        
    except Exception as e:
        logger.error(f"Session authentication test failed: {e}")
        return False


if __name__ == "__main__":
    logger.info("=== Session Recovery Tool ===")
    
    async def main():
        if await recover_session_data():
            logger.info("Session recovery successful!")
            
            # Test authentication
            if await test_session_authentication():
                logger.info("Session authentication test passed!")
            else:
                logger.warning("Session authentication test failed - sessions may need re-authentication")
                logger.info("Use the admin bot commands /sessions and /addsession to re-authenticate")
        else:
            logger.error("Session recovery failed!")
            return False
        
        return True
    
    if asyncio.run(main()):
        logger.info("All done! Your sessions should now be working.")
    else:
        logger.error("Recovery process failed!")
        sys.exit(1)