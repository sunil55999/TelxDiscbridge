#!/usr/bin/env python3
"""
Fix the fox session by loading session data from file into database.
"""

import asyncio
import sys
import base64
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import Database
from config.settings import Settings


async def fix_fox_session():
    """Fix fox session by loading from session file."""
    print("🔧 FIXING FOX SESSION")
    print("=" * 30)
    
    try:
        # Initialize database
        settings = Settings.load_from_file("config.yaml")
        database = Database(settings.database_url)
        await database.initialize()
        
        # Load fox.session file
        fox_session_file = Path("sessions/fox.session")
        if not fox_session_file.exists():
            print("❌ fox.session file not found!")
            return False
        
        print("📁 Reading fox.session file...")
        with open(fox_session_file, 'rb') as f:
            session_bytes = f.read()
        
        if not session_bytes:
            print("❌ Session file is empty!")
            return False
        
        print(f"✅ Loaded session data ({len(session_bytes)} bytes)")
        
        # Convert to base64 for storage
        session_b64 = base64.b64encode(session_bytes).decode('ascii')
        
        # Update the session in database using proper SQLAlchemy syntax
        async with database.Session() as session:
            try:
                from sqlalchemy import text
                
                # First check if fox session exists
                result = await session.execute(
                    text("SELECT id FROM sessions WHERE name = :name"),
                    {"name": "fox"}
                )
                session_row = result.fetchone()
                
                if session_row:
                    print("📝 Updating existing fox session...")
                    await session.execute(
                        text("UPDATE sessions SET session_data = :data, health_status = 'healthy', is_active = 1 WHERE name = 'fox'"),
                        {"data": session_b64}
                    )
                else:
                    print("📝 Creating new fox session...")
                    await session.execute(
                        text("INSERT INTO sessions (name, session_data, health_status, is_active) VALUES ('fox', :data, 'healthy', 1)"),
                        {"data": session_b64}
                    )
                
                await session.commit()
                print("✅ Session updated in database!")
                
                # Verify the update
                result = await session.execute(
                    text("SELECT name, health_status, is_active, LENGTH(session_data) as data_len FROM sessions WHERE name = 'fox'")
                )
                row = result.fetchone()
                if row:
                    print(f"✅ Verification: {row[0]}, {row[1]}, active={bool(row[2])}, data_len={row[3]}")
                
                return True
                
            except Exception as e:
                print(f"❌ Database error: {e}")
                await session.rollback()
                return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if database:
            await database.close()


if __name__ == "__main__":
    success = asyncio.run(fix_fox_session())
    if success:
        print("\n🚀 Fox session fixed! Restart the bot to apply changes.")
    else:
        print("\n❌ Failed to fix fox session.")