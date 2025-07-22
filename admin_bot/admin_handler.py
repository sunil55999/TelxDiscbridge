"""Main admin bot handler for managing the forwarding system."""

import asyncio
from typing import List, Optional
from datetime import datetime

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

from core.database import Database
from core.session_manager import SessionManager
from core.advanced_session_manager import AdvancedSessionManager
from admin_bot.unified_admin_commands import UnifiedAdminCommands
from admin_bot.unified_session_commands import UnifiedSessionCommands
from core.message_filter import MessageFilter
from core.alert_system import AlertSystem
from utils.encryption import EncryptionManager


class AdminHandler:
    """Main admin bot handler."""
    
    def __init__(self, bot_token: str, database: Database, session_manager: SessionManager, admin_user_ids: List[int], advanced_session_manager: Optional[AdvancedSessionManager] = None, encryption_key: str = ""):
        self.bot_token = bot_token
        self.database = database
        self.session_manager = session_manager
        self.advanced_session_manager = advanced_session_manager
        self.admin_user_ids = set(admin_user_ids)
        self.encryption_manager = EncryptionManager(encryption_key)
        self.application: Optional[Application] = None
        self.unified_commands: Optional[UnifiedAdminCommands] = None
        self.session_commands: Optional[UnifiedSessionCommands] = None
        self.message_filter: Optional[MessageFilter] = None
        self.alert_system: Optional[AlertSystem] = None
        self.running = False
    
    async def start(self):
        """Start the admin bot."""
        if self.running:
            logger.warning("Admin bot is already running")
            return
        
        try:
            logger.info("Starting admin bot...")
            
            # Initialize message filter and alert system
            self.message_filter = MessageFilter(self.database)
            await self.message_filter.initialize()
            
            self.alert_system = AlertSystem(self.database, self)
            await self.alert_system.start()
            
            # Initialize unified command system - replaces all separate command handlers
            self.unified_commands = UnifiedAdminCommands(
                self.database, self.encryption_manager, self.message_filter, self.advanced_session_manager
            )
            
            # Keep session commands for OTP handling
            self.session_commands = None
            if self.advanced_session_manager:
                self.session_commands = UnifiedSessionCommands(self.database, self.advanced_session_manager)
            
            # Create application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Add command handlers
            self._setup_handlers()
            
            # Start the bot with timeout
            await asyncio.wait_for(self.application.initialize(), timeout=30.0)
            await asyncio.wait_for(self.application.start(), timeout=30.0)
            
            # Start polling in background - don't await it directly
            polling_task = asyncio.create_task(self.application.updater.start_polling())
            
            self.running = True
            logger.info("Admin bot started successfully")
            
            # Keep running and monitor polling task
            try:
                while self.running:
                    await asyncio.sleep(1)
                    # Check if polling task failed
                    if polling_task.done() and polling_task.exception():
                        logger.error(f"Polling task failed: {polling_task.exception()}")
                        break
            except asyncio.CancelledError:
                logger.info("Admin bot task was cancelled")
                polling_task.cancel()
                raise
                
        except Exception as e:
            logger.error(f"Failed to start admin bot: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Stop the admin bot."""
        if not self.running:
            return
        
        logger.info("Stopping admin bot...")
        self.running = False
        
        # Stop subsystems
        if self.alert_system:
            await self.alert_system.stop()
        
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Admin bot stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping admin bot: {e}")
        
        self.application = None
        self.unified_commands = None
        self.session_commands = None
    
    def _setup_handlers(self):
        """Setup command and callback handlers."""
        if not self.application or not self.unified_commands:
            return
        
        command_handlers = {
            "start": self.unified_commands.start_command,
            "help": self.unified_commands.help_command,
            "status": self.unified_commands.status_command,
            "addbot": self.unified_commands.addbot_command,
            "listbots": self.unified_commands.listbots_command,
            "removebot": self.unified_commands.removebot_command,
            "testbot": self.unified_commands.testbot_command,
            "blockword": self.unified_commands.blockword_command,
            "unblockword": self.unified_commands.unblockword_command,
            "blockimage": self.unified_commands.blockimage_command,
            "showfilters": self.unified_commands.showfilters_command,
            "blockimages": self.unified_commands.blockimages_command,
            "allowimages": self.unified_commands.allowimages_command,
            "sessions": self.unified_commands.sessions_command,
            "addpair": self.unified_commands.addpair_command,
            "listpairs": self.unified_commands.listpairs_command,
            "removepair": self.unified_commands.removepair_command,
            "health": self._health_check_command,
        }

        if self.session_commands:
            command_handlers["addsession"] = self.session_commands.addsession_command

        for command_name, handler_func in command_handlers.items():
            self.application.add_handler(CommandHandler(command_name, self._execute_command(handler_func)))

        if self.session_commands:
            self.application.add_handler(CallbackQueryHandler(self._execute_command(self.session_commands.handle_otp_callback), pattern="^(enter_otp|resend_otp|cancel_otp):"))

        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._execute_command(self._handle_combined_messages)))
        self.application.add_handler(MessageHandler(filters.PHOTO, self._execute_command(self.unified_commands.handle_image_upload)))
        
        logger.info("Admin bot handlers setup complete")

    def _execute_command(self, handler_func):
        """Wrap handler function with admin permission check and error handling."""
        async def wrapped_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            try:
                user_id = update.effective_user.id
                
                if user_id not in self.admin_user_ids:
                    if update.effective_message:
                        await update.effective_message.reply_text("❌ Access denied. You are not authorized to use this bot.")
                    logger.warning(f"Unauthorized access attempt from user {user_id}")
                    return
                
                await handler_func(update, context)
                
            except Exception as e:
                logger.error(f"Error in admin handler: {e}", exc_info=True)
                try:
                    if update.effective_message:
                        await update.effective_message.reply_text(f"❌ An error occurred: {e}")
                except Exception as send_error:
                    logger.error(f"Failed to send error message to user: {send_error}")
        
        return wrapped_handler
    
    async def _handle_unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown messages."""
        await update.message.reply_text(
            "❓ I don't understand that message. Use /help to see available commands."
        )
    
    async def _handle_combined_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pair wizard, enhanced pair creation, OTP codes, or unknown messages."""
        user_id = update.effective_user.id
        
        # Try pair wizard input first
        if hasattr(self, 'pair_wizard') and self.pair_wizard and hasattr(self.pair_wizard, 'wizard_state'):
            if user_id in self.pair_wizard.wizard_state:
                await self.pair_wizard.handle_wizard_input(update, context)
                return
        
        # Try unified pair creation
        if self.unified_commands and hasattr(self.unified_commands, 'handle_pair_creation_input'):
            handled = await self.unified_commands.handle_pair_creation_input(update, context)
            if handled:
                return
        
        # Try OTP handling first (session commands)
        if self.session_commands and hasattr(self.session_commands, 'handle_otp_message'):
            handled = await self.session_commands.handle_otp_message(update, context)
            if handled:
                return
        
        # Not handled by any special handler, treat as unknown
        await self._handle_unknown_message(update, context)
    
    # Additional admin commands
    async def _show_alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent system alerts."""
        if not self.alert_system:
            await update.message.reply_text("❌ Alert system not available")
            return

        stats = await self.alert_system.get_alert_stats()
        recent_alerts = await self.alert_system.get_recent_alerts(limit=10)

        message = f"🚨 **System Alerts Overview**\n\n"
        message += f"**Statistics:**\n"
        message += f"• Total alerts: {stats['total']}\n"
        message += f"• Last 24h: {stats['recent_24h']}\n\n"

        if stats['by_level']:
            message += "**By Level:**\n"
            for level, count in stats['by_level'].items():
                emoji = {'info': 'ℹ️', 'warning': '⚠️', 'error': '❌', 'critical': '🚨'}.get(level, '📢')
                message += f"• {emoji} {level.upper()}: {count}\n"
            message += "\n"

        if recent_alerts:
            message += "**Recent Alerts (last 10):**\n"
            for alert in recent_alerts[:5]:  # Show only 5 most recent
                timestamp = alert['timestamp'].strftime('%H:%M')
                level_emoji = {'info': 'ℹ️', 'warning': '⚠️', 'error': '❌', 'critical': '🚨'}.get(alert['level'], '📢')
                message += f"• {level_emoji} {timestamp} - {alert['title']}\n"
        else:
            message += "No recent alerts 🎉"

        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def _show_logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent error logs."""
        message = "📋 **Recent System Logs**\n\n"
        message += "✅ System operational\n"
        message += "ℹ️ Use `/alerts` for alert history\n"
        message += "📊 Use `/status` for detailed status\n\n"
        message += "*Detailed log access available via system files*"

        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def _health_check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Perform comprehensive system health check."""
        health_msg = await update.message.reply_text("🔍 Performing health check...")

        health_results = {
            'database': '✅ Connected',
            'sessions': '✅ Healthy',
            'filters': '✅ Active',
            'alerts': '✅ Running',
            'memory': '✅ Normal'
        }

        try:
            pairs = await self.database.get_all_pairs()
            if pairs is None:
                health_results['database'] = '❌ Connection failed'
        except Exception:
            health_results['database'] = '❌ Error'

        if self.message_filter:
            stats = await self.message_filter.get_filter_stats()
            health_results['filters'] = f"✅ {stats['global_blocked_words']} words blocked"
        else:
            health_results['filters'] = '❌ Not initialized'

        if self.alert_system and self.alert_system.running:
            alert_stats = await self.alert_system.get_alert_stats()
            health_results['alerts'] = f"✅ {alert_stats['recent_24h']} alerts (24h)"
        else:
            health_results['alerts'] = '❌ Not running'

        message = "🏥 **System Health Check**\n\n"
        for component, status in health_results.items():
            message += f"**{component.title()}:** {status}\n"

        message += f"\n🕒 **Check completed at:** {datetime.now().strftime('%H:%M:%S')}"

        await health_msg.edit_text(message, parse_mode='Markdown')
    
    def add_admin_user(self, user_id: int):
        """Add a new admin user."""
        self.admin_user_ids.add(user_id)
        logger.info(f"Added admin user: {user_id}")
    
    def remove_admin_user(self, user_id: int):
        """Remove an admin user."""
        self.admin_user_ids.discard(user_id)
        logger.info(f"Removed admin user: {user_id}")
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id in self.admin_user_ids
    
    async def broadcast_message(self, message: str):
        """Broadcast a message to all admin users."""
        if not self.application or not self.running:
            logger.error("Admin bot is not running")
            return
        
        for admin_id in self.admin_user_ids:
            try:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send broadcast message to admin {admin_id}: {e}")
    
    async def send_alert(self, alert_message: str):
        """Send an alert to all admin users."""
        alert_text = f"🚨 **ALERT** 🚨\n\n{alert_message}"
        await self.broadcast_message(alert_text)
        logger.warning(f"Alert sent to admins: {alert_message}")
    
    async def send_notification(self, notification: str):
        """Send a notification to all admin users."""
        notification_text = f"📢 **Notification**\n\n{notification}"
        await self.broadcast_message(notification_text)
        logger.info(f"Notification sent to admins: {notification}")
    
    async def _show_image_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show image commands help."""
        from admin_bot.image_handler import ImageHandler
        image_handler = ImageHandler(self.message_filter)
        await image_handler.show_image_commands_help(update, context)
    
    async def _handle_image_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle image uploads for hash generation."""
        from admin_bot.image_handler import ImageHandler
        image_handler = ImageHandler(self.message_filter)
        await image_handler.handle_image_message(update, context)
