"""Unified session management with a single /addsession command."""

import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger

from core.database import Database
from core.advanced_session_manager import AdvancedSessionManager


class UnifiedSessionCommands:
    """Unified session management with single command for adding sessions."""
    
    def __init__(self, database: Database, advanced_session_manager: AdvancedSessionManager):
        self.database = database
        self.advanced_session_manager = advanced_session_manager
        # Store pending OTP verifications
        self.pending_verifications = {}
    
    async def addsession_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addsession command with automatic OTP verification."""
        try:
            args = context.args
            
            # Show help if no arguments provided
            if not args:
                help_text = (
                    "📱 **Add Session - Complete Guide**\n\n"
                    "**Step 1: Add your session**\n"
                    "`/addsession <session_name> <phone_number>`\n\n"
                    "**Example:**\n"
                    "`/addsession my_session +1234567890`\n\n"
                    "**What happens next:**\n"
                    "1. Bot registers your session\n"
                    "2. Sends OTP to your phone\n"
                    "3. You enter the code when prompted\n"
                    "4. Session is ready to use!\n\n"
                    "**Requirements:**\n"
                    "• Use country code with phone (+1, +44, etc.)\n"
                    "• Session name: letters, numbers, underscores only\n"
                    "• Have your phone ready for OTP\n\n"
                    "**Tips:**\n"
                    "• Choose a simple session name\n"
                    "• Keep your phone accessible\n"
                    "• OTP usually arrives within 30 seconds"
                )
                await update.message.reply_text(help_text, parse_mode='Markdown')
                return
            
            # Parse arguments
            if len(args) < 2:
                await update.message.reply_text(
                    "❌ **Missing information**\n\n"
                    "Usage: `/addsession <session_name> <phone_number>`\n"
                    "Example: `/addsession my_session +1234567890`",
                    parse_mode='Markdown'
                )
                return
            
            session_name = args[0].strip()
            phone_number = args[1].strip()
            user_id = update.effective_user.id if update.effective_user else 0
            
            # Validate session name
            if not session_name or not session_name.replace('_', '').replace('-', '').isalnum():
                await update.message.reply_text(
                    "❌ **Invalid session name**\n\n"
                    "Session name can only contain:\n"
                    "• Letters (a-z, A-Z)\n"
                    "• Numbers (0-9)\n"
                    "• Underscores (_)\n"
                    "• Hyphens (-)\n\n"
                    "Example: `my_session` or `user-1`"
                )
                return
            
            # Validate phone number
            if not phone_number.startswith('+') or len(phone_number) < 8:
                await update.message.reply_text(
                    "❌ **Invalid phone number**\n\n"
                    "Phone number must:\n"
                    "• Start with country code (+1, +44, etc.)\n"
                    "• Be at least 8 digits long\n\n"
                    "Examples:\n"
                    "• `+1234567890` (US)\n"
                    "• `+447123456789` (UK)\n"
                    "• `+91987654321` (India)"
                )
                return
            
            # Check if session already exists
            existing_session = await self.database.get_session_info(session_name)
            if existing_session:
                await update.message.reply_text(
                    f"❌ **Session already exists**\n\n"
                    f"Session '{session_name}' is already registered.\n"
                    f"Choose a different name or delete the existing session first."
                )
                return
            
            # Check if user has too many pending verifications
            user_pending = [k for k, v in self.pending_verifications.items() 
                           if v.get('user_id') == user_id]
            if len(user_pending) >= 3:
                await update.message.reply_text(
                    "❌ **Too many pending sessions**\n\n"
                    "You have too many sessions waiting for verification.\n"
                    "Please complete or cancel existing verifications first."
                )
                return
            
            # Start the session creation process
            progress_message = await update.message.reply_text(
                f"🔄 **Setting up session '{session_name}'**\n\n"
                f"📱 Phone: {phone_number}\n"
                f"⏳ Registering session...",
                parse_mode='Markdown'
            )
            
            try:
                # Register the session with default settings
                success = await self.advanced_session_manager.register_session(
                    session_name, 
                    phone_number, 
                    priority=5,  # Default priority
                    max_pairs=30  # Default capacity
                )
                
                if not success:
                    await progress_message.edit_text(
                        f"❌ **Session registration failed**\n\n"
                        f"Could not register session '{session_name}'.\n"
                        f"Please try again or contact support if the issue persists."
                    )
                    return
                
                # Update progress
                await progress_message.edit_text(
                    f"✅ **Session registered successfully**\n\n"
                    f"📱 Phone: {phone_number}\n"
                    f"🔄 Sending OTP to your phone...",
                    parse_mode='Markdown'
                )
                
                # Initiate authentication to send OTP
                auth_result = await self.advanced_session_manager.authenticate_session(
                    session_name, phone_number, None
                )
                
                if auth_result.get("success"):
                    # Session authenticated immediately (rare case)
                    await progress_message.edit_text(
                        f"🎉 **Session '{session_name}' is ready!**\n\n"
                        f"✅ Authentication completed automatically\n"
                        f"🚀 You can now use this session for forwarding pairs\n\n"
                        f"Use `/sessionstatus {session_name}` to check details"
                    )
                    return
                
                elif auth_result.get("needs_otp"):
                    # Store pending verification with timeout
                    verification_id = f"{session_name}_{user_id}_{int(datetime.now().timestamp())}"
                    self.pending_verifications[verification_id] = {
                        'session_name': session_name,
                        'phone_number': phone_number,
                        'phone_code_hash': auth_result.get("phone_code_hash"),
                        'user_id': user_id,
                        'created_at': datetime.now(),
                        'attempts': 0,
                        'max_attempts': 3
                    }
                    
                    # Debug logging
                    logger.info(f"Created verification ID: {verification_id}")
                    logger.info(f"Total pending verifications: {len(self.pending_verifications)}")
                    
                    # Create inline keyboard for OTP entry
                    keyboard = [
                        [InlineKeyboardButton("🔢 Enter OTP Code", callback_data=f"enter_otp:{verification_id}")],
                        [InlineKeyboardButton("🔄 Resend OTP", callback_data=f"resend_otp:{verification_id}")],
                        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_otp:{verification_id}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await progress_message.edit_text(
                        f"📱 **OTP sent to {phone_number}**\n\n"
                        f"✅ Session '{session_name}' registered\n"
                        f"📨 Verification code sent to your phone\n"
                        f"⏰ Code expires in 5 minutes\n\n"
                        f"**Next step:** Click 'Enter OTP Code' below and provide the verification code you received.",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    
                    # Set up automatic cleanup after 10 minutes
                    asyncio.create_task(self._cleanup_expired_verification(verification_id, 600))
                
                else:
                    # Authentication failed
                    error_msg = auth_result.get("error", "Unknown authentication error")
                    await progress_message.edit_text(
                        f"❌ **Authentication failed**\n\n"
                        f"Session: {session_name}\n"
                        f"Phone: {phone_number}\n"
                        f"Error: {error_msg}\n\n"
                        f"Please check your phone number and try again."
                    )
                    
                    # Clean up failed session
                    try:
                        await self.advanced_session_manager.delete_session(session_name, force=True)
                    except:
                        pass
                
            except Exception as e:
                logger.error(f"Error during session setup: {e}")
                await progress_message.edit_text(
                    f"❌ **Setup error**\n\n"
                    f"An error occurred while setting up session '{session_name}'.\n"
                    f"Please try again in a few moments."
                )
                
                # Clean up failed session
                try:
                    await self.advanced_session_manager.delete_session(session_name, force=True)
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Error in addsession_command: {e}")
            await update.message.reply_text(
                "❌ **System error**\n\n"
                "An unexpected error occurred. Please try again."
            )
    
    async def handle_otp_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle OTP-related callback queries."""
        try:
            query = update.callback_query
            if not query or not query.data:
                return
                
            await query.answer()
            
            callback_data = query.data
            if ':' not in callback_data:
                return
                
            action, verification_id = callback_data.split(':', 1)
            
            # Debug logging
            logger.info(f"OTP callback received: action={action}, verification_id={verification_id}")
            logger.info(f"Pending verifications: {list(self.pending_verifications.keys())}")
            
            if verification_id not in self.pending_verifications:
                logger.warning(f"Verification ID {verification_id} not found in pending verifications")
                if query.message:
                    await query.edit_message_text(
                        "❌ **Verification expired**\n\n"
                        "This verification session has expired or been completed.\n"
                        "Please use `/addsession` to start over."
                    )
                return
            
            verification_info = self.pending_verifications[verification_id]
            session_name = verification_info['session_name']
            phone_number = verification_info['phone_number']
            user_id = verification_info['user_id']
            
            # Check if user is authorized
            if query.from_user and query.from_user.id != user_id:
                await query.answer("❌ This verification is not for you", show_alert=True)
                return
            
            if action == "enter_otp":
                # Prompt user to send the OTP code
                keyboard = [
                    [InlineKeyboardButton("🔄 Resend OTP", callback_data=f"resend_otp:{verification_id}")],
                    [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_otp:{verification_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if query.message:
                    await query.edit_message_text(
                        f"🔢 **Enter your verification code**\n\n"
                        f"Session: {session_name}\n"
                        f"Phone: {phone_number}\n\n"
                        f"**Send your OTP code as a reply to this message**\n"
                        f"Example: Just type `12345` and send\n\n"
                        f"⏰ Waiting for your code...\n"
                        f"Attempts remaining: {verification_info['max_attempts'] - verification_info['attempts']}",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    
                    # Mark this verification as waiting for OTP input
                    verification_info['waiting_for_otp'] = True
                    verification_info['message_id'] = query.message.message_id
            
            elif action == "resend_otp":
                # Resend OTP
                if query.message:
                    await query.edit_message_text(
                        f"🔄 **Resending OTP**\n\n"
                        f"Session: {session_name}\n"
                        f"Phone: {phone_number}\n\n"
                        f"⏳ Requesting new verification code...",
                        parse_mode='Markdown'
                    )
                
                # Attempt to resend OTP
                auth_result = await self.advanced_session_manager.authenticate_session(
                    session_name, phone_number, None
                )
                
                if auth_result.get("needs_otp"):
                    keyboard = [
                        [InlineKeyboardButton("🔢 Enter OTP Code", callback_data=f"enter_otp:{verification_id}")],
                        [InlineKeyboardButton("🔄 Resend OTP", callback_data=f"resend_otp:{verification_id}")],
                        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_otp:{verification_id}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    if query.message:
                        await query.edit_message_text(
                            f"📱 **New OTP sent**\n\n"
                            f"Session: {session_name}\n"
                            f"Phone: {phone_number}\n"
                            f"📨 Fresh verification code sent\n\n"
                            f"Click 'Enter OTP Code' when ready.",
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                else:
                    if query.message:
                        await query.edit_message_text(
                            f"❌ **Could not resend OTP**\n\n"
                            f"Failed to send new verification code.\n"
                            f"Please try `/addsession {session_name} {phone_number}` again."
                        )
            
            elif action == "cancel_otp":
                # Cancel the verification
                if query.message:
                    await query.edit_message_text(
                        f"❌ **Verification cancelled**\n\n"
                        f"Session setup for '{session_name}' has been cancelled.\n"
                        f"Use `/addsession` to try again."
                    )
                
                # Clean up
                await self._cleanup_verification(verification_id)
        
        except Exception as e:
            logger.error(f"Error in handle_otp_callback: {e}")
            if query and query.message:
                try:
                    await query.edit_message_text(
                        "❌ **Error processing request**\n\n"
                        "Please try `/addsession` again."
                    )
                except:
                    pass
    
    async def handle_otp_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle OTP code sent as message."""
        try:
            user_id = update.effective_user.id if update.effective_user else 0
            message_text = update.message.text.strip() if update.message and update.message.text else ""
            
            # Find pending verification for this user that's waiting for OTP
            verification_info = None
            verification_id = None
            
            for vid, vinfo in self.pending_verifications.items():
                if (vinfo.get('user_id') == user_id and 
                    vinfo.get('waiting_for_otp')):
                    verification_info = vinfo
                    verification_id = vid
                    break
            
            if not verification_info:
                # Not an OTP message
                return False
            
            # Validate OTP format (typically 5-6 digits)
            if not message_text.isdigit() or len(message_text) < 4 or len(message_text) > 6:
                if update.message:
                    await update.message.reply_text(
                        "❌ **Invalid code format**\n\n"
                        "Verification codes are usually 4-6 digits.\n"
                        "Please check and try again."
                    )
                return True
            
            session_name = verification_info['session_name']
            phone_number = verification_info['phone_number']
            
            # Update attempts
            verification_info['attempts'] += 1
            
            # Delete the OTP message for security
            try:
                if update.message:
                    await update.message.delete()
            except:
                pass
            
            progress_message = None
            try:
                # Find and update the original message
                message_id = verification_info.get('message_id')
                if message_id and update.effective_chat:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=message_id,
                        text=f"🔄 **Verifying code**\n\n"
                             f"Session: {session_name}\n"
                             f"⏳ Checking verification code...",
                        parse_mode='Markdown'
                    )
                    progress_message = "edited"  # Indicate edit was successful
            except:
                if update.message:
                    progress_message = await update.message.reply_text(
                        f"🔄 **Verifying code**\n\n"
                        f"Session: {session_name}\n"
                        f"⏳ Checking verification code...",
                        parse_mode='Markdown'
                    )
            
            # Attempt authentication with OTP using stored phone_code_hash
            phone_code_hash = verification_info.get('phone_code_hash')
            auth_result = await self.advanced_session_manager.authenticate_session(
                session_name, phone_number, message_text, phone_code_hash
            )
            
            if auth_result.get("success"):
                # Success!
                try:
                    if progress_message == "edited" and update.effective_chat:
                        await context.bot.edit_message_text(
                            chat_id=update.effective_chat.id,
                            message_id=verification_info.get('message_id'),
                            text=f"🎉 **Session '{session_name}' is ready!**\n\n"
                                 f"✅ Verification successful\n"
                                 f"📱 Phone: {phone_number}\n"
                                 f"🚀 Session is active and ready for use\n\n"
                                 f"**What's next?**\n"
                                 f"• Use `/sessionstatus` to check details\n"
                                 f"• Add forwarding pairs with `/addpair`\n"
                                 f"• View help with `/help`"
                        )
                    elif progress_message and hasattr(progress_message, 'edit_text'):
                        await progress_message.edit_text(
                            f"🎉 **Session '{session_name}' is ready!**\n\n"
                            f"✅ Verification successful\n"
                            f"📱 Phone: {phone_number}\n"
                            f"🚀 Session is active and ready for use\n\n"
                            f"**What's next?**\n"
                            f"• Use `/sessionstatus` to check details\n"
                            f"• Add forwarding pairs with `/addpair`\n"
                            f"• View help with `/help`"
                        )
                except:
                    # Fallback - send new message
                    if update.effective_chat:
                        await update.effective_chat.send_message(
                            f"🎉 **Session '{session_name}' is ready!**\n\n"
                            f"✅ Verification successful\n"
                            f"📱 Phone: {phone_number}\n"
                            f"🚀 Session is active and ready for use\n\n"
                            f"**What's next?**\n"
                            f"• Use `/sessionstatus` to check details\n"
                            f"• Add forwarding pairs with `/addpair`\n"
                            f"• View help with `/help`"
                        )
                
                # Clean up verification
                await self._cleanup_verification(verification_id)
                
            else:
                # Failed verification
                error_msg = auth_result.get("error", "Invalid verification code")
                remaining_attempts = verification_info['max_attempts'] - verification_info['attempts']
                
                if remaining_attempts > 0:
                    # Allow retry
                    keyboard = [
                        [InlineKeyboardButton("🔢 Enter OTP Code", callback_data=f"enter_otp:{verification_id}")],
                        [InlineKeyboardButton("🔄 Resend OTP", callback_data=f"resend_otp:{verification_id}")],
                        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_otp:{verification_id}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    try:
                        if progress_message == "edited" and update.effective_chat:
                            await context.bot.edit_message_text(
                                chat_id=update.effective_chat.id,
                                message_id=verification_info.get('message_id'),
                                text=f"❌ **Verification failed**\n\n"
                                     f"Session: {session_name}\n"
                                     f"Error: {error_msg}\n"
                                     f"Attempts remaining: {remaining_attempts}\n\n"
                                     f"Try again with a fresh code or resend OTP.",
                                reply_markup=reply_markup,
                                parse_mode='Markdown'
                            )
                        elif progress_message and hasattr(progress_message, 'edit_text'):
                            await progress_message.edit_text(
                                f"❌ **Verification failed**\n\n"
                                f"Session: {session_name}\n"
                                f"Error: {error_msg}\n"
                                f"Attempts remaining: {remaining_attempts}\n\n"
                                f"Try again with a fresh code or resend OTP.",
                                reply_markup=reply_markup,
                                parse_mode='Markdown'
                            )
                    except:
                        if update.effective_chat:
                            await update.effective_chat.send_message(
                                f"❌ **Verification failed**\n\n"
                                f"Session: {session_name}\n"
                                f"Error: {error_msg}\n"
                                f"Attempts remaining: {remaining_attempts}\n\n"
                                f"Try again with a fresh code or resend OTP.",
                                reply_markup=reply_markup,
                                parse_mode='Markdown'
                            )
                    
                    # Reset waiting state
                    verification_info['waiting_for_otp'] = False
                    
                else:
                    # Max attempts reached
                    try:
                        if progress_message == "edited" and update.effective_chat:
                            await context.bot.edit_message_text(
                                chat_id=update.effective_chat.id,
                                message_id=verification_info.get('message_id'),
                                text=f"❌ **Verification failed - Max attempts reached**\n\n"
                                     f"Session: {session_name}\n"
                                     f"Too many failed attempts.\n\n"
                                     f"Please use `/addsession {session_name} {phone_number}` to start over."
                            )
                        elif progress_message and hasattr(progress_message, 'edit_text'):
                            await progress_message.edit_text(
                                f"❌ **Verification failed - Max attempts reached**\n\n"
                                f"Session: {session_name}\n"
                                f"Too many failed attempts.\n\n"
                                f"Please use `/addsession {session_name} {phone_number}` to start over."
                            )
                    except:
                        if update.effective_chat:
                            await update.effective_chat.send_message(
                                f"❌ **Verification failed - Max attempts reached**\n\n"
                                f"Session: {session_name}\n"
                                f"Too many failed attempts.\n\n"
                                f"Please use `/addsession {session_name} {phone_number}` to start over."
                            )
                    
                    # Clean up
                    await self._cleanup_verification(verification_id)
            
            return True  # Indicate we handled this message
            
        except Exception as e:
            logger.error(f"Error in handle_otp_message: {e}")
            if update.message:
                await update.message.reply_text(
                    "❌ **Verification error**\n\n"
                    "An error occurred during verification.\n"
                    "Please try `/addsession` again."
                )
            return True
    
    async def _cleanup_verification(self, verification_id: str):
        """Clean up a verification session."""
        try:
            verification_info = self.pending_verifications.get(verification_id)
            if verification_info:
                # If session was created but not verified, clean it up
                session_name = verification_info.get('session_name')
                if session_name:
                    try:
                        await self.advanced_session_manager.delete_session(session_name, force=True)
                    except:
                        pass
                
                # Remove from pending
                del self.pending_verifications[verification_id]
                logger.info(f"Cleaned up verification {verification_id}")
        except Exception as e:
            logger.error(f"Error cleaning up verification {verification_id}: {e}")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages for OTP verification."""
        if not update.message or not update.message.text:
            return
        
        try:
            user_id = update.effective_user.id if update.effective_user else 0
            message_text = update.message.text.strip()
            
            # Check if this is an OTP code (6 digits)
            if message_text.isdigit() and len(message_text) == 6:
                # Find pending verification for this user
                verification_id = None
                for vid in list(self.pending_verifications.keys()):
                    if vid.endswith(f"_{user_id}_"):
                        verification_id = vid
                        break
                
                if verification_id:
                    # Process OTP
                    await self._process_otp_verification(update, context, verification_id, message_text)
                    return
            
            # Not an OTP or no pending verification
            await update.message.reply_text(
                "❓ I don't understand that message. Use /help to see available commands."
            )
            
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _cleanup_expired_verification(self, verification_id: str, delay: int):
        """Clean up expired verification after delay."""
        await asyncio.sleep(delay)
        if verification_id in self.pending_verifications:
            logger.info(f"Cleaning up expired verification {verification_id}")
            await self._cleanup_verification(verification_id)
    
    def get_pending_verifications_count(self, user_id: int) -> int:
        """Get count of pending verifications for a user."""
        return len([v for v in self.pending_verifications.values() 
                   if v.get('user_id') == user_id])
    
    def is_waiting_for_otp(self, user_id: int) -> bool:
        """Check if user has any verification waiting for OTP input."""
        return any(v.get('user_id') == user_id and v.get('waiting_for_otp') 
                  for v in self.pending_verifications.values())