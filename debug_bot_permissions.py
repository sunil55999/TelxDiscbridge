#!/usr/bin/env python3
"""
Comprehensive bot permission diagnostic tool.
This script helps identify exactly what's wrong with bot permissions in destination chats.
"""

import asyncio
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram import Bot
from telegram.error import TelegramError, BadRequest, Forbidden
from config.settings import Settings


async def diagnose_bot_permissions(bot_token: str, chat_id: int):
    """Comprehensive bot permission diagnosis."""
    print(f"=== Bot Permission Diagnosis ===")
    print(f"Chat ID: {chat_id}")
    print(f"Bot Token: {bot_token[:10]}...")
    print()
    
    try:
        bot = Bot(token=bot_token)
        
        # Step 1: Validate bot token
        print("Step 1: Validating bot token...")
        try:
            me = await bot.get_me()
            print(f"✅ Bot token valid")
            print(f"   Bot ID: {me.id}")
            print(f"   Username: @{me.username}")
            print(f"   Name: {me.first_name}")
            print(f"   Can join groups: {me.can_join_groups}")
            print(f"   Can read all messages: {me.can_read_all_group_messages}")
        except Exception as e:
            print(f"❌ Bot token validation failed: {e}")
            return False
        
        print()
        
        # Step 2: Check if bot can access the chat
        print("Step 2: Checking chat access...")
        try:
            chat = await bot.get_chat(chat_id)
            print(f"✅ Bot can access chat")
            print(f"   Chat title: {getattr(chat, 'title', 'N/A')}")
            print(f"   Chat type: {chat.type}")
            print(f"   Chat username: {getattr(chat, 'username', 'None')}")
        except Forbidden as e:
            print(f"❌ Bot cannot access chat: {e}")
            print("   Solution: Add the bot to the chat first")
            return False
        except BadRequest as e:
            print(f"❌ Invalid chat ID or other error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error accessing chat: {e}")
            return False
        
        print()
        
        # Step 3: Check bot membership and permissions
        print("Step 3: Checking bot membership and permissions...")
        try:
            chat_member = await bot.get_chat_member(chat_id, me.id)
            print(f"✅ Bot is a member of the chat")
            print(f"   Status: {chat_member.status}")
            
            # Check specific permissions
            permissions = {}
            permission_attrs = [
                'can_send_messages',
                'can_send_media_messages', 
                'can_send_polls',
                'can_send_other_messages',
                'can_add_web_page_previews',
                'can_change_info',
                'can_invite_users',
                'can_pin_messages',
                'can_edit_messages',
                'can_delete_messages',
                'can_manage_chat',
                'can_restrict_members',
                'can_promote_members'
            ]
            
            for attr in permission_attrs:
                if hasattr(chat_member, attr):
                    value = getattr(chat_member, attr)
                    permissions[attr] = value
                    status = "✅" if value else "❌"
                    print(f"   {status} {attr}: {value}")
                else:
                    print(f"   ❓ {attr}: Not available")
            
            # Check minimum required permissions for forwarding
            required_permissions = ['can_send_messages']
            missing_permissions = []
            
            for perm in required_permissions:
                if perm in permissions and not permissions[perm]:
                    missing_permissions.append(perm)
            
            if missing_permissions:
                print(f"\n❌ Missing required permissions: {missing_permissions}")
                print("   Solution: Grant these permissions to the bot in chat settings")
                return False
            else:
                print(f"\n✅ Bot has all required permissions")
                
        except Forbidden as e:
            print(f"❌ Cannot get bot membership info: {e}")
            print("   This usually means the bot isn't added to the chat")
            return False
        except Exception as e:
            print(f"❌ Error checking bot membership: {e}")
            return False
        
        print()
        
        # Step 4: Test sending a message
        print("Step 4: Testing message sending...")
        try:
            test_message = await bot.send_message(
                chat_id=chat_id,
                text="🤖 Bot permission test - this message will be deleted automatically"
            )
            print(f"✅ Bot can send messages")
            
            # Try to delete the test message
            try:
                await bot.delete_message(chat_id=chat_id, message_id=test_message.message_id)
                print(f"✅ Bot can delete messages")
            except Exception as e:
                print(f"⚠️  Bot cannot delete messages: {e}")
                
        except Forbidden as e:
            print(f"❌ Bot cannot send messages: {e}")
            print("   Check if bot has 'can_send_messages' permission")
            return False
        except Exception as e:
            print(f"❌ Error sending test message: {e}")
            return False
        
        print()
        print("🎉 All permission checks passed! Bot should work for forwarding.")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error during diagnosis: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main diagnostic function."""
    print("=== Telegram Bot Permission Diagnostic Tool ===")
    print()
    
    # Get inputs
    if len(sys.argv) >= 3:
        bot_token = sys.argv[1]
        chat_id = int(sys.argv[2])
    else:
        print("Usage: python debug_bot_permissions.py <bot_token> <chat_id>")
        print()
        print("Example:")
        print("python debug_bot_permissions.py 5555555555:AAA... -1001234567890")
        print()
        print("Or use environment variables:")
        
        # Try to get from environment or user input
        bot_token = os.getenv("TEST_BOT_TOKEN")
        chat_id_str = os.getenv("TEST_CHAT_ID")
        
        if not bot_token:
            bot_token = input("Enter bot token: ").strip()
        if not chat_id_str:
            chat_id_str = input("Enter chat ID (like -1001234567890): ").strip()
            
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            print("❌ Invalid chat ID format")
            return 1
    
    if not bot_token or not chat_id:
        print("❌ Missing bot token or chat ID")
        return 1
    
    # Run diagnosis
    success = await diagnose_bot_permissions(bot_token, chat_id)
    
    if success:
        print("\n✅ DIAGNOSIS COMPLETE: Bot permissions are working correctly")
        return 0
    else:
        print("\n❌ DIAGNOSIS COMPLETE: Bot has permission issues")
        print("\nCommon solutions:")
        print("1. Make sure bot is added to the destination chat/channel")
        print("2. Give bot 'Admin' status or at least 'Send Messages' permission")
        print("3. For channels, make sure bot has 'Post Messages' permission")
        print("4. Check that chat ID is correct (use @userinfobot)")
        return 1


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)