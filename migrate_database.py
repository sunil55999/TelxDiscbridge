#!/usr/bin/env python3
"""
Database migration script to fix schema mismatch issues.
This script adds missing columns and fixes the database structure.
"""

import sqlite3
import os
import sys
from datetime import datetime
from loguru import logger


def backup_database(db_path: str):
    """Create a backup of the current database."""
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        return None


def check_column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate_database():
    """Perform database migration to fix schema issues."""
    db_path = "forwarding_bot.db"
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    # Create backup
    backup_path = backup_database(db_path)
    if not backup_path:
        logger.error("Failed to create backup, aborting migration")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("Starting database migration...")
        
        # Check and add missing columns to forwarding_pairs table
        missing_columns = []
        
        # Required columns for forwarding_pairs
        required_columns = {
            'telegram_bot_token_encrypted': 'TEXT',
            'telegram_bot_name': 'VARCHAR(100) DEFAULT ""',
            'discord_webhook_url': 'TEXT DEFAULT ""'
        }
        
        for column, column_type in required_columns.items():
            if not check_column_exists(cursor, 'forwarding_pairs', column):
                missing_columns.append((column, column_type))
        
        # Add missing columns
        for column, column_type in missing_columns:
            try:
                cursor.execute(f"ALTER TABLE forwarding_pairs ADD COLUMN {column} {column_type}")
                logger.info(f"Added column: {column}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    logger.error(f"Error adding column {column}: {e}")
                    raise
                else:
                    logger.info(f"Column {column} already exists")
        
        # Commit changes
        conn.commit()
        logger.info("Database migration completed successfully!")
        
        # Verify the migration
        cursor.execute("SELECT sql FROM sqlite_master WHERE name = 'forwarding_pairs'")
        schema = cursor.fetchone()
        if schema:
            logger.info("Updated forwarding_pairs schema:")
            logger.info(schema[0])
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        logger.info(f"Database backup is available at: {backup_path}")
        return False


def verify_database_structure():
    """Verify the database structure after migration."""
    try:
        conn = sqlite3.connect("forwarding_bot.db")
        cursor = conn.cursor()
        
        # Check forwarding_pairs table
        cursor.execute("PRAGMA table_info(forwarding_pairs)")
        columns = cursor.fetchall()
        
        logger.info("Current forwarding_pairs table structure:")
        for col in columns:
            logger.info(f"  {col[1]} ({col[2]})")
        
        # Check sessions table
        cursor.execute("PRAGMA table_info(sessions)")
        sessions_columns = cursor.fetchall()
        
        logger.info("Current sessions table structure:")
        for col in sessions_columns:
            logger.info(f"  {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    logger.info("=== Database Migration Tool ===")
    
    if migrate_database():
        logger.info("Migration successful!")
        verify_database_structure()
    else:
        logger.error("Migration failed!")
        sys.exit(1)