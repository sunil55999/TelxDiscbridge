#!/usr/bin/env python3
"""
Environment setup script - creates proper .env file and verifies encryption setup.
"""

import os
import base64
from cryptography.fernet import Fernet
from loguru import logger


def generate_encryption_key():
    """Generate a new encryption key."""
    return base64.urlsafe_b64encode(Fernet.generate_key()).decode()


def setup_environment():
    """Set up the environment configuration."""
    logger.info("=== Environment Setup ===")
    
    # Check if .env already exists
    if os.path.exists(".env"):
        logger.info(".env file already exists")
        return True
    
    # Read encryption key from session_key.key if it exists
    encryption_key = None
    if os.path.exists("session_key.key"):
        with open("session_key.key", 'r') as f:
            encryption_key = f.read().strip()
        logger.info("Using existing encryption key from session_key.key")
    else:
        encryption_key = generate_encryption_key()
        logger.info("Generated new encryption key")
    
    # Create .env file with minimal required configuration
    env_content = f"""# Telegram → Discord → Telegram Forwarding Bot Configuration
DATABASE_URL=sqlite:///forwarding_bot.db
ENCRYPTION_KEY={encryption_key}

# REQUIRED: Add your bot tokens and API credentials here
# Get Telegram Bot Token from @BotFather
TELEGRAM_BOT_TOKEN=

# Get Discord Bot Token from Discord Developer Portal  
DISCORD_BOT_TOKEN=

# Get API credentials from https://my.telegram.org
TELEGRAM_API_ID=
TELEGRAM_API_HASH=

# Add your Telegram user ID (get from @userinfobot)
ADMIN_USER_IDS=

# Optional settings
LOG_LEVEL=INFO
"""
    
    try:
        with open(".env", "w") as f:
            f.write(env_content)
        logger.info("Created .env file")
        return True
    except Exception as e:
        logger.error(f"Failed to create .env file: {e}")
        return False


def verify_database_structure():
    """Verify the database has the correct structure."""
    import sqlite3
    
    try:
        conn = sqlite3.connect("forwarding_bot.db")
        cursor = conn.cursor()
        
        # Check if required columns exist
        cursor.execute("PRAGMA table_info(forwarding_pairs)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = [
            'telegram_bot_token_encrypted', 
            'telegram_bot_name', 
            'discord_webhook_url'
        ]
        
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            logger.error(f"Database missing required columns: {missing_columns}")
            logger.error("Please run: python migrate_database.py")
            return False
        
        logger.info("Database structure verified")
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False


def check_session_status():
    """Check the status of sessions in the database."""
    import sqlite3
    
    try:
        conn = sqlite3.connect("forwarding_bot.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name, phone_number, is_active, 
                   session_data IS NOT NULL as has_data,
                   health_status
            FROM sessions
        """)
        sessions = cursor.fetchall()
        
        if not sessions:
            logger.warning("No sessions found in database")
            logger.info("Use admin bot command: /addsession <name> <phone_number>")
            return True
        
        logger.info(f"Found {len(sessions)} sessions:")
        active_sessions = 0
        
        for name, phone, is_active, has_data, health_status in sessions:
            status_icon = "✅" if is_active and has_data else "❌"
            data_status = "HAS DATA" if has_data else "NO DATA"
            logger.info(f"  {status_icon} {name} ({phone}): {data_status} - {health_status}")
            
            if is_active and has_data:
                active_sessions += 1
        
        if active_sessions == 0:
            logger.warning("No active sessions with data found")
            logger.info("Sessions need re-authentication via admin bot")
        else:
            logger.info(f"{active_sessions} sessions are ready for use")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Session status check failed: {e}")
        return False


def provide_next_steps():
    """Provide clear next steps for the user."""
    logger.info("\n=== NEXT STEPS ===")
    logger.info("1. Edit .env file and add your bot tokens:")
    logger.info("   - TELEGRAM_BOT_TOKEN (from @BotFather)")
    logger.info("   - DISCORD_BOT_TOKEN (from Discord Developer Portal)")
    logger.info("   - TELEGRAM_API_ID and TELEGRAM_API_HASH (from my.telegram.org)")
    logger.info("   - ADMIN_USER_IDS (your Telegram user ID)")
    logger.info("")
    logger.info("2. Restart the bot: python main.py")
    logger.info("")
    logger.info("3. Use admin bot commands:")
    logger.info("   - /addsession <name> <phone> - Add/re-authenticate sessions")
    logger.info("   - /addbot <name> <token> - Add bot tokens for destinations")
    logger.info("   - /addpair - Create forwarding pairs")
    logger.info("")
    logger.info("4. The bot will guide you through the setup process")


if __name__ == "__main__":
    success = True
    
    if not setup_environment():
        success = False
    
    if not verify_database_structure():
        success = False
    
    if not check_session_status():
        success = False
    
    if success:
        logger.info("Environment setup completed successfully!")
        provide_next_steps()
    else:
        logger.error("Environment setup encountered issues!")
        logger.error("Please check the errors above and resolve them")