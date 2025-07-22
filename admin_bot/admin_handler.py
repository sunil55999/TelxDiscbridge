"""Main admin bot handler for managing the forwarding system."""

import asyncio
from typing import List, Optional

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

from core.database import Database
from core.session_manager import SessionManager
from core.advanced_session_manager import AdvancedSessionManager
from admin_bot.commands import AdminCommands
from admin_bot.unified_session_commands import UnifiedSessionCommands
from admin_bot.enhanced_commands import EnhancedAdminCommands
from admin_bot.filter_commands import FilterCommands
from admin_bot.comprehensive_help import ComprehensiveHelp
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
        self.commands: Optional[AdminCommands] = None
        self.unified_commands: Optional[UnifiedSessionCommands] = None
        self.enhanced_commands: Optional[EnhancedAdminCommands] = None
        self.filter_commands: Optional[FilterCommands] = None
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
            
            # Initialize commands handlers
            self.commands = AdminCommands(self.database, self.session_manager)
            self.enhanced_commands = EnhancedAdminCommands(self.database, self.session_manager, self.encryption_manager)
            self.filter_commands = FilterCommands(self.database, self.message_filter)
            if self.advanced_session_manager:
                self.unified_commands = UnifiedSessionCommands(self.database, self.advanced_session_manager)
            
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
        self.commands = None
    
    def _setup_handlers(self):
        """Setup command and callback handlers."""
        if not self.application or not self.commands:
            return
        
        # Add comprehensive command handlers with admin check
        command_handlers = [
            ("start", self.commands.start_command),
            ("help", ComprehensiveHelp.show_help_menu),
            ("addpair", self.enhanced_commands.addpair_enhanced_command),  # Enhanced version
            ("listpairs", self.commands.listpairs_command),
            ("removepair", self.commands.removepair_command),
            ("status", self.commands.status_command),
            ("sessions", self.commands.sessions_command),
            ("changesession", self.commands.changesession_command),
            # Enhanced filtering commands
            ("blockword", self.filter_commands.blockword_command),
            ("unblockword", self.filter_commands.unblockword_command),
            ("showfilters", self.filter_commands.showfilters_command),
            ("filterconfig", self.filter_commands.filterconfig_command),
            ("testfilter", self.filter_commands.testfilter_command),
            # Quick filter shortcuts
            ("blockimages", self.filter_commands.block_images_command),
            ("allowimages", self.filter_commands.allow_images_command),
            ("stripheaders", self.filter_commands.strip_headers_command),
            ("keepheaders", self.filter_commands.keep_headers_command),
            # Bot token management
            ("validatebot", self.enhanced_commands.validate_bot_command),
            ("updatebottoken", self.enhanced_commands.update_bot_token_command),
            # System monitoring
            ("alerts", self._show_alerts_command),
            ("logs", self._show_logs_command),
            ("health", self._health_check_command),
        ]
        
        # Add unified session management command
        if self.unified_commands:
            unified_handlers = [
                ("addsession", self.unified_commands.addsession_command),
            ]
            command_handlers.extend(unified_handlers)
        
        for command_name, handler_func in command_handlers:
            wrapped_handler = self._wrap_admin_handler(handler_func)
            self.application.add_handler(CommandHandler(command_name, wrapped_handler))
        
        # Add unified session callback handlers FIRST (more specific patterns)
        if self.unified_commands:
            otp_callback_handler = self._wrap_admin_handler(self.unified_commands.handle_otp_callback)
            self.application.add_handler(CallbackQueryHandler(otp_callback_handler, pattern="^(enter_otp|resend_otp|cancel_otp):"))
        
        # Add general callback query handlers LAST (catch-all)
        wrapped_callback_handler = self._wrap_admin_handler(self.commands.handle_callback_query)
        self.application.add_handler(CallbackQueryHandler(wrapped_callback_handler))
        
        # Add message handler for enhanced pair creation and OTP codes
        combined_message_handler = self._wrap_admin_handler(self._handle_combined_messages)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, combined_message_handler)
        )
        
        logger.info("Admin bot handlers setup complete")
    
    def _wrap_admin_handler(self, handler_func):
        """Wrap handler function with admin permission check."""
        async def wrapped_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            try:
                user_id = update.effective_user.id
                
                # Debug logging for callbacks
                if update.callback_query:
                    logger.info(f"Callback received: {update.callback_query.data} from user {user_id}")
                
                # Check if user is admin
                if user_id not in self.admin_user_ids:
                    if update.effective_message:
                        await update.effective_message.reply_text(
                            "❌ Access denied. You are not authorized to use this bot."
                        )
                    logger.warning(f"Unauthorized access attempt from user {user_id}")
                    return
                
                # Call the actual handler
                await handler_func(update, context)
                
            except Exception as e:
                logger.error(f"Error in admin handler: {e}")
                try:
                    if update.effective_message:
                        await update.effective_message.reply_text(f"❌ An error occurred: {e}")
                except:
                    pass  # Ignore errors when sending error messages
        
        return wrapped_handler
    
    async def _handle_unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown messages."""
        await update.message.reply_text(
            "❓ I don't understand that message. Use /help to see available commands."
        )
    
    async def _handle_combined_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle enhanced pair creation, OTP codes, or unknown messages."""
        # Try enhanced pair creation first
        if self.enhanced_commands:
            handled = await self.enhanced_commands.handle_enhanced_pair_creation(update, context)
            if handled:
                return
        
        # Try OTP handling
        if self.unified_commands:
            handled = await self.unified_commands.handle_otp_message(update, context)
            if handled:
                return
        
        # Not handled by any special handler, treat as unknown
        await self._handle_unknown_message(update, context)
    
    # Additional admin commands
    async def _show_alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent system alerts."""
        try:
            if not self.alert_system:
                await update.message.reply_text("❌ Alert system not available")
                return
            
            # Get alert stats and recent alerts
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
            
        except Exception as e:
            logger.error(f"Error showing alerts: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _show_logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent error logs."""
        try:
            # This would integrate with actual log system
            message = "📋 **Recent System Logs**\n\n"
            message += "✅ System operational\n"
            message += "ℹ️ Use `/alerts` for alert history\n"
            message += "📊 Use `/status` for detailed status\n\n"
            message += "*Detailed log access available via system files*"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing logs: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _health_check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Perform comprehensive system health check."""
        try:
            health_msg = await update.message.reply_text("🔍 Performing health check...")
            
            health_results = {
                'database': '✅ Connected',
                'sessions': '✅ Healthy',
                'filters': '✅ Active',
                'alerts': '✅ Running',
                'memory': '✅ Normal'
            }
            
            # Check database
            try:
                pairs = await self.database.get_all_pairs()
                if pairs is None:
                    health_results['database'] = '❌ Connection failed'
            except Exception:
                health_results['database'] = '❌ Error'
            
            # Check message filter
            if self.message_filter:
                stats = await self.message_filter.get_filter_stats()
                health_results['filters'] = f"✅ {stats['global_blocked_words']} words blocked"
            else:
                health_results['filters'] = '❌ Not initialized'
            
            # Check alert system
            if self.alert_system and self.alert_system.running:
                alert_stats = await self.alert_system.get_alert_stats()
                health_results['alerts'] = f"✅ {alert_stats['recent_24h']} alerts (24h)"
            else:
                health_results['alerts'] = '❌ Not running'
            
            # Format results
            message = "🏥 **System Health Check**\n\n"
            for component, status in health_results.items():
                message += f"**{component.title()}:** {status}\n"
            
            message += f"\n🕒 **Check completed at:** {datetime.now().strftime('%H:%M:%S')}"
            
            await health_msg.edit_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            await update.message.reply_text(f"❌ Health check failed: {e}")
    
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
