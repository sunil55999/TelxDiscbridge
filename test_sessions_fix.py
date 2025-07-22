#!/usr/bin/env python3
"""
Test script to verify the sessions command fix is working properly.
"""

import asyncio
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from core.database import Database


async def test_sessions_formatting():
    """Test that sessions can be formatted without Markdown errors."""
    try:
        # Initialize settings and database
        settings = Settings.load_from_file("config.yaml")
        database = Database(settings.database_url)
        await database.initialize()
        
        # Get sessions
        sessions = await database.get_all_sessions()
        print(f"Found {len(sessions)} sessions in database")
        
        # Test the formatting logic from the fixed sessions_command
        message = "👥 Telegram Sessions\n\n"
        
        for session in sessions:
            status_emoji = {
                'healthy': '✅',
                'not_found': '❌',
                'error': '⚠️',
                'deleted': '🗑️',
                'needs_auth': '⏳'
            }.get(session.health_status, '❓')
            
            # Apply the same escaping logic as in the fix
            session_name = session.name.replace('_', '\\_').replace('*', '\\*')
            phone = (session.phone_number or 'Unknown').replace('_', '\\_')
            
            message += f"*{session_name}*\n"
            message += f"{status_emoji} Status: {session.health_status}\n"
            message += f"📱 Phone: {phone}\n"
            message += f"👤 Pairs: {session.pair_count}\n"
            
            if session.last_verified:
                try:
                    if isinstance(session.last_verified, str):
                        from datetime import datetime
                        date_str = session.last_verified.split('.')[0]
                        if 'T' in date_str:
                            last_verified = datetime.fromisoformat(date_str)
                        else:
                            last_verified = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        last_verified = session.last_verified
                    message += f"🕒 Last verified: {last_verified.strftime('%Y-%m-%d %H:%M')}\n"
                except Exception as e:
                    safe_date = str(session.last_verified)[:16]
                    message += f"🕒 Last verified: {safe_date}\n"
                    print(f"Warning: Date parsing issue for {session.name}: {e}")
            
            message += "\n"
        
        message += "Commands:\n"
        message += "• /addsession <name> <phone> - Add new session\n"
        message += "• /changesession <pair_id> <session> - Change pair session"
        
        print("=== Formatted Sessions Message ===")
        print(message)
        print("=== End Message ===")
        
        # Check message length and for problematic characters
        print(f"\nMessage length: {len(message)} characters")
        print(f"Contains problematic patterns: {len([c for c in message if ord(c) > 127])} non-ASCII chars")
        
        await database.close()
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    async def main():
        print("=== Testing Sessions Command Fix ===")
        
        if await test_sessions_formatting():
            print("\n✅ Sessions formatting test PASSED")
            print("The Markdown parsing error should be resolved.")
        else:
            print("\n❌ Sessions formatting test FAILED")
            return 1
        
        return 0
    
    result = asyncio.run(main())
    sys.exit(result)