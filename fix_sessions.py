#!/usr/bin/env python3
"""
Session repair and recovery script.
This script fixes session data storage and authentication issues.
"""

import sqlite3
import os
import sys
from datetime import datetime
from loguru import logger


def fix_sessions():
    """Fix session storage issues."""
    db_path = "forwarding_bot.db"
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("=== Session Repair Tool ===")
        
        # Check current session status
        cursor.execute("SELECT name, phone_number, is_active, session_data IS NULL as missing_data FROM sessions")
        sessions = cursor.fetchall()
        
        logger.info(f"Found {len(sessions)} sessions:")
        for name, phone, is_active, missing_data in sessions:
            status = "❌ INACTIVE" if not is_active else "✅ ACTIVE"
            data_status = "❌ NO DATA" if missing_data else "✅ HAS DATA"
            logger.info(f"  {name} ({phone}): {status}, {data_status}")
        
        # Check for corresponding session files
        session_files = []
        if os.path.exists("sessions"):
            session_files = [f for f in os.listdir("sessions") if f.endswith('.session')]
            logger.info(f"Found {len(session_files)} session files:")
            for session_file in session_files:
                logger.info(f"  {session_file}")
        
        # Update sessions to be marked as requiring re-authentication
        cursor.execute("""
            UPDATE sessions 
            SET is_active = 0, 
                health_status = 'needs_auth',
                metadata_info = json_set(
                    COALESCE(metadata_info, '{}'),
                    '$.authentication_pending', true,
                    '$.last_repair', ?
                )
            WHERE session_data IS NULL OR session_data = ''
        """, (datetime.now().isoformat(),))
        
        affected_rows = cursor.rowcount
        logger.info(f"Updated {affected_rows} sessions to require re-authentication")
        
        # Commit changes
        conn.commit()
        
        # Show updated status
        cursor.execute("SELECT name, phone_number, is_active, health_status FROM sessions")
        updated_sessions = cursor.fetchall()
        
        logger.info("Updated session status:")
        for name, phone, is_active, health_status in updated_sessions:
            status = "✅ ACTIVE" if is_active else "⏳ NEEDS AUTH"
            logger.info(f"  {name} ({phone}): {status} - {health_status}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Session repair failed: {e}")
        return False


def create_environment_template():
    """Create a template .env file with required variables."""
    env_template = """# Telegram → Discord → Telegram Forwarding Bot Configuration
# Copy this file to .env and fill in your actual values

# Database Configuration
DATABASE_URL=sqlite:///forwarding_bot.db

# Telegram Bot Token (from @BotFather)
TELEGRAM_BOT_TOKEN=

# Discord Bot Token (from Discord Developer Portal)
DISCORD_BOT_TOKEN=

# Telegram API Credentials (from my.telegram.org)
TELEGRAM_API_ID=
TELEGRAM_API_HASH=

# Admin User IDs (comma-separated Telegram user IDs)
ADMIN_USER_IDS=

# Encryption Key (will be auto-generated if empty)
ENCRYPTION_KEY=

# Optional: Logging Configuration
LOG_LEVEL=INFO
"""
    
    try:
        with open(".env.template", "w") as f:
            f.write(env_template)
        logger.info("Created .env.template file")
        
        if not os.path.exists(".env"):
            with open(".env", "w") as f:
                f.write(env_template)
            logger.info("Created .env file - please fill in your credentials")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create environment template: {e}")
        return False


if __name__ == "__main__":
    if fix_sessions():
        logger.info("Session repair completed!")
    else:
        logger.error("Session repair failed!")
        sys.exit(1)
    
    if create_environment_template():
        logger.info("Environment template created!")
    else:
        logger.error("Failed to create environment template!")