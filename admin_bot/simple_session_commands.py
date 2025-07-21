"""Simplified session management commands."""

import asyncio
from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

from core.database import Database
from core.advanced_session_manager import AdvancedSessionManager


class SimpleSessionCommands:
    """Simplified session management with one-command setup."""
    
    def __init__(self, database: Database, advanced_session_manager: AdvancedSessionManager):
        self.database = database
        self.advanced_session_manager = advanced_session_manager
        # Store pending sessions for OTP verification
        self.pending_sessions = {}
    
    async def quick_session_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /quicksession command - complete session setup in one go."""
        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "📱 **Quick Session Setup**\n\n"
                    "Usage: `/quicksession <session_name> <phone_number>`\n\n"
                    "Example: `/quicksession my_session +1234567890`\n\n"
                    "This will:\n"
                    "1. Register the session\n"
                    "2. Send OTP to your phone\n"
                    "3. Wait for you to enter the code\n\n"
                    "Then use: `/entercode <session_name> <code>`",
                    parse_mode='Markdown'
                )
                return
            
            session_name = args[0]
            phone_number = args[1]
            
            # Validate inputs
            if not session_name.replace('_', '').isalnum():
                await update.message.reply_text("❌ Session name must be alphanumeric (underscores allowed)")
                return
            
            if not phone_number.startswith('+'):
                await update.message.reply_text("❌ Phone number must include country code (e.g., +1234567890)")
                return
            
            await update.message.reply_text(f"🔄 Setting up session '{session_name}' for {phone_number}...")
            
            # Check if session already exists
            existing_session = await self.database.get_session_info(session_name)
            if existing_session:
                await update.message.reply_text(f"❌ Session '{session_name}' already exists. Choose a different name.")
                return
            
            # Register session
            success = await self.advanced_session_manager.register_session(
                session_name, phone_number, priority=3, max_pairs=30
            )
            
            if not success:
                await update.message.reply_text(f"❌ Failed to register session '{session_name}'")
                return
            
            # Start authentication and send OTP
            auth_result = await self.advanced_session_manager.authenticate_session(
                session_name, phone_number, None
            )
            
            if auth_result.get("needs_otp"):
                # Store session info for OTP verification
                self.pending_sessions[session_name] = {
                    'phone_number': phone_number,
                    'user_id': update.effective_user.id,
                    'created_at': update.message.date
                }
                
                await update.message.reply_text(
                    f"✅ Session registered and OTP sent!\n\n"
                    f"📱 Check your Telegram app for verification code\n"
                    f"📝 Then use: `/entercode {session_name} <your_code>`\n\n"
                    f"Example: `/entercode {session_name} 12345`",
                    parse_mode='Markdown'
                )
            elif auth_result.get("success"):
                await update.message.reply_text(
                    f"✅ Session '{session_name}' is ready to use immediately!"
                )
            else:
                error_msg = auth_result.get("error", "Authentication failed")
                await update.message.reply_text(
                    f"❌ Setup failed: {error_msg}\n"
                    f"Please try again with `/quicksession {session_name} {phone_number}`"
                )
                
        except Exception as e:
            logger.error(f"Error in quick_session_command: {e}")
            await update.message.reply_text("❌ An error occurred during session setup")
    
    async def enter_code_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /entercode command - verify OTP for pending session."""
        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "📱 **Enter Verification Code**\n\n"
                    "Usage: `/entercode <session_name> <verification_code>`\n\n"
                    "Example: `/entercode my_session 12345`\n\n"
                    "Make sure you've already used `/quicksession` first!",
                    parse_mode='Markdown'
                )
                return
            
            session_name = args[0]
            verification_code = args[1]
            
            # Check if session is pending
            if session_name not in self.pending_sessions:
                await update.message.reply_text(
                    f"❌ No pending session found for '{session_name}'\n"
                    f"Please use `/quicksession` first to set up the session."
                )
                return
            
            pending_info = self.pending_sessions[session_name]
            
            # Verify user
            if pending_info['user_id'] != update.effective_user.id:
                await update.message.reply_text("❌ You can only verify sessions you created")
                return
            
            await update.message.reply_text(f"🔄 Verifying code for '{session_name}'...")
            
            # Authenticate with code
            auth_result = await self.advanced_session_manager.authenticate_session(
                session_name, pending_info['phone_number'], verification_code
            )
            
            if auth_result.get("success"):
                # Remove from pending
                del self.pending_sessions[session_name]
                
                await update.message.reply_text(
                    f"🎉 **Session '{session_name}' is now active!**\n\n"
                    f"✅ Authentication successful\n"
                    f"🟢 Session ready for forwarding pairs\n"
                    f"📊 Capacity: 30 pairs\n\n"
                    f"Use `/sessionstatus {session_name}` to check details"
                )
            elif auth_result.get("error"):
                error_msg = auth_result["error"]
                if "Invalid verification code" in error_msg:
                    await update.message.reply_text(
                        f"❌ Invalid verification code\n\n"
                        f"Please check your Telegram app and try again:\n"
                        f"`/entercode {session_name} <correct_code>`",
                        parse_mode='Markdown'
                    )
                elif "expired" in error_msg.lower():
                    # Remove expired session
                    if session_name in self.pending_sessions:
                        del self.pending_sessions[session_name]
                    
                    await update.message.reply_text(
                        f"❌ Verification code expired\n\n"
                        f"Please start over with:\n"
                        f"`/quicksession {session_name} {pending_info['phone_number']}`",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        f"❌ Verification failed: {error_msg}\n\n"
                        f"You can try again with:\n"
                        f"`/entercode {session_name} <new_code>`",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    f"❌ Unexpected error during verification\n"
                    f"Please try starting over with `/quicksession`"
                )
                
        except Exception as e:
            logger.error(f"Error in enter_code_command: {e}")
            await update.message.reply_text("❌ An error occurred during code verification")
    
    async def session_guide_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sessionguide command - show simplified guide."""
        try:
            guide_text = (
                "🚀 **Easy Session Setup Guide**\n\n"
                "**Step 1: Quick Setup**\n"
                "`/quicksession my_session +1234567890`\n"
                "• This sends OTP to your phone\n"
                "• Replace with your actual phone number\n\n"
                "**Step 2: Enter Verification Code**\n"
                "`/entercode my_session 12345`\n"
                "• Check Telegram app for 5-digit code\n"
                "• Replace 12345 with actual code\n\n"
                "**Step 3: Done!**\n"
                "Your session is ready for forwarding pairs.\n\n"
                "**Check Status:**\n"
                "`/sessionstatus` - View all sessions\n"
                "`/sessionstatus my_session` - View specific session\n\n"
                "**Tips:**\n"
                "• Use simple names: my_session, backup, main_account\n"
                "• Keep phone accessible for OTP\n"
                "• Each session can handle 30 forwarding pairs\n"
                "• Codes expire in 5 minutes\n\n"
                "**Need Help?**\n"
                "Contact admin if OTP doesn't arrive or codes don't work."
            )
            
            await update.message.reply_text(guide_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in session_guide_command: {e}")
            await update.message.reply_text("❌ An error occurred while showing the guide")
    
    async def pending_sessions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pendingsessions command - show sessions waiting for OTP."""
        try:
            user_pending = {
                name: info for name, info in self.pending_sessions.items() 
                if info['user_id'] == update.effective_user.id
            }
            
            if not user_pending:
                await update.message.reply_text(
                    "ℹ️ No pending sessions\n\n"
                    "Use `/quicksession <name> <phone>` to create a new session"
                )
                return
            
            message = "📋 **Your Pending Sessions**\n\n"
            
            for session_name, info in user_pending.items():
                time_ago = (update.message.date - info['created_at']).total_seconds() // 60
                message += (
                    f"📱 **{session_name}**\n"
                    f"   Phone: {info['phone_number']}\n"
                    f"   Waiting: {time_ago:.0f} minutes\n"
                    f"   Use: `/entercode {session_name} <code>`\n\n"
                )
            
            message += (
                "💡 **Tips:**\n"
                "• Check Telegram app for verification codes\n"
                "• Codes expire in 5 minutes\n"
                "• Use `/quicksession` again if expired"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in pending_sessions_command: {e}")
            await update.message.reply_text("❌ An error occurred while showing pending sessions")