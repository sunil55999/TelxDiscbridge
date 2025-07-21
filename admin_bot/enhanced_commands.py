"""Enhanced admin commands for advanced session management."""

import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger

from core.database import Database, SessionInfo, ForwardingPair
from core.advanced_session_manager import AdvancedSessionManager


class EnhancedAdminCommands:
    """Enhanced admin command implementations for advanced session management."""
    
    def __init__(self, database: Database, advanced_session_manager: AdvancedSessionManager):
        self.database = database
        self.advanced_session_manager = advanced_session_manager
    
    async def register_session_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /registersession command."""
        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "❌ Usage: `/registersession <session_name> <phone_number> [priority] [max_pairs]`\n\n"
                    "Example: `/registersession user1_session +1234567890 1 30`",
                    parse_mode='Markdown'
                )
                return
            
            session_name = args[0]
            phone_number = args[1]
            priority = int(args[2]) if len(args) > 2 else 1
            max_pairs = int(args[3]) if len(args) > 3 else 30
            
            # Validate inputs
            if not session_name.replace('_', '').isalnum():
                await update.message.reply_text("❌ Session name must be alphanumeric (underscores allowed)")
                return
            
            if max_pairs < 1 or max_pairs > 50:
                await update.message.reply_text("❌ Max pairs must be between 1 and 50")
                return
            
            # Check if session already exists
            existing_session = await self.database.get_session_info(session_name)
            if existing_session:
                await update.message.reply_text(f"❌ Session '{session_name}' already exists")
                return
            
            # Register the session
            await update.message.reply_text(f"🔄 Registering session '{session_name}'...")
            
            success = await self.advanced_session_manager.register_session(
                session_name, phone_number, priority, max_pairs
            )
            
            if success:
                await update.message.reply_text(
                    f"✅ Successfully registered session '{session_name}'\n"
                    f"📱 Phone: {phone_number}\n"
                    f"⭐ Priority: {priority}\n"
                    f"📊 Max pairs: {max_pairs}\n\n"
                    f"Use `/authenticate {session_name}` to activate the session."
                )
            else:
                await update.message.reply_text(f"❌ Failed to register session '{session_name}'")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid priority or max_pairs value (must be numbers)")
        except Exception as e:
            logger.error(f"Error in register_session_command: {e}")
            await update.message.reply_text("❌ An error occurred while registering the session")
    
    async def authenticate_session_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /authenticate command."""
        try:
            args = context.args
            if len(args) < 1:
                await update.message.reply_text(
                    "❌ Usage: `/authenticate <session_name> [verification_code]`\n\n"
                    "Example: `/authenticate user1_session 12345`",
                    parse_mode='Markdown'
                )
                return
            
            session_name = args[0]
            verification_code = args[1] if len(args) > 1 else None
            
            # Check if session exists
            session_info = await self.database.get_session_info(session_name)
            if not session_info:
                await update.message.reply_text(f"❌ Session '{session_name}' not found")
                return
            
            await update.message.reply_text(f"🔄 Authenticating session '{session_name}'...")
            
            success = await self.advanced_session_manager.authenticate_session(
                session_name, session_info.phone_number, verification_code
            )
            
            if success:
                await update.message.reply_text(
                    f"✅ Successfully authenticated session '{session_name}'\n"
                    f"🟢 Session is now active and ready for use"
                )
            else:
                await update.message.reply_text(
                    f"❌ Failed to authenticate session '{session_name}'\n"
                    f"Please check your phone for verification code and try again"
                )
                
        except Exception as e:
            logger.error(f"Error in authenticate_session_command: {e}")
            await update.message.reply_text("❌ An error occurred during authentication")
    
    async def session_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sessionstatus command."""
        try:
            args = context.args
            if len(args) < 1:
                # Show all sessions if no specific session provided
                await self._show_all_sessions_status(update)
                return
            
            session_name = args[0]
            status = await self.advanced_session_manager.get_session_status(session_name)
            
            if "error" in status:
                await update.message.reply_text(f"❌ {status['error']}")
                return
            
            session_info = status['session_info']
            worker_info = status.get('worker_info', {})
            health_status = status.get('health_status', {})
            
            # Format status message
            status_emoji = "🟢" if session_info['health_status'] == "healthy" else "🔴"
            
            message = (
                f"{status_emoji} **Session Status: {session_name}**\n\n"
                f"📱 Phone: {session_info['phone_number'] or 'N/A'}\n"
                f"💚 Health: {session_info['health_status']}\n"
                f"📊 Pairs: {status['capacity_usage']} ({status['utilization_percent']}%)\n"
                f"⭐ Priority: {session_info['priority']}\n"
                f"🔧 Active: {'Yes' if session_info['is_active'] else 'No'}\n"
            )
            
            if session_info.get('last_verified'):
                last_verified = datetime.fromisoformat(session_info['last_verified'].replace('Z', '+00:00'))
                message += f"🕐 Last verified: {last_verified.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            if worker_info:
                message += f"\n👷 Worker: {worker_info['worker_id'][:12]}...\n"
                message += f"🏃 Worker active: {'Yes' if worker_info['is_active'] else 'No'}\n"
            
            if health_status and not health_status.get('is_healthy', True):
                message += f"\n⚠️ Health issues: {health_status.get('error_message', 'Unknown')}\n"
            
            # Add pairs information if any
            if status['pairs']:
                message += f"\n📋 **Active Pairs ({len(status['pairs'])})**:\n"
                for i, pair in enumerate(status['pairs'][:5]):  # Show first 5 pairs
                    message += f"• {pair['name']} (ID: {pair['id']})\n"
                
                if len(status['pairs']) > 5:
                    message += f"• ... and {len(status['pairs']) - 5} more pairs\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in session_status_command: {e}")
            await update.message.reply_text("❌ An error occurred while fetching session status")
    
    async def changesession_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /changesession command for bulk reassignment."""
        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "❌ Usage: `/changesession <new_session_name> <pair_ids>`\n\n"
                    "Examples:\n"
                    "• `/changesession user2_session 1,2,3`\n"
                    "• `/changesession user2_session 1-5` (range)\n"
                    "• `/changesession user2_session all_from:user1_session`",
                    parse_mode='Markdown'
                )
                return
            
            new_session_name = args[0]
            pair_spec = args[1]
            
            # Parse pair IDs
            pair_ids = await self._parse_pair_specification(pair_spec)
            
            if not pair_ids:
                await update.message.reply_text("❌ No valid pair IDs found")
                return
            
            # Validate new session exists
            new_session = await self.database.get_session_info(new_session_name)
            if not new_session:
                await update.message.reply_text(f"❌ Target session '{new_session_name}' not found")
                return
            
            await update.message.reply_text(
                f"🔄 Starting bulk reassignment of {len(pair_ids)} pairs to session '{new_session_name}'...\n"
                f"This may take a moment."
            )
            
            # Perform bulk reassignment
            result = await self.advanced_session_manager.bulk_reassign_session(pair_ids, new_session_name)
            
            if result['success']:
                message = (
                    f"✅ Successfully reassigned {len(result['reassigned_pairs'])} pairs to '{new_session_name}'\n\n"
                    f"📊 Session health: {'✅ Healthy' if result['session_health']['is_healthy'] else '❌ Unhealthy'}\n"
                    f"🔄 Workers will be reorganized automatically"
                )
                
                if result['failed_pairs']:
                    message += f"\n⚠️ Failed to reassign {len(result['failed_pairs'])} pairs"
            else:
                message = f"❌ Bulk reassignment failed: {result.get('error', 'Unknown error')}"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error in changesession_command: {e}")
            await update.message.reply_text("❌ An error occurred during bulk reassignment")
    
    async def session_health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sessionhealth command."""
        try:
            args = context.args
            
            if not args:
                # Show health overview for all sessions
                sessions = await self.database.get_all_sessions()
                
                healthy_count = sum(1 for s in sessions if s.health_status == "healthy")
                total_count = len(sessions)
                
                message = (
                    f"🏥 **Session Health Overview**\n\n"
                    f"📊 Total sessions: {total_count}\n"
                    f"💚 Healthy: {healthy_count}\n"
                    f"❤️‍🩹 Unhealthy: {total_count - healthy_count}\n\n"
                )
                
                for session in sessions:
                    status_emoji = "🟢" if session.health_status == "healthy" else "🔴"
                    last_check = "Never" if not session.last_verified else session.last_verified.strftime('%H:%M')
                    
                    message += f"{status_emoji} {session.name} ({session.health_status}) - Last: {last_check}\n"
                
                await update.message.reply_text(message, parse_mode='Markdown')
                return
            
            # Show detailed health for specific session
            session_name = args[0]
            status = await self.advanced_session_manager.get_session_status(session_name)
            
            if "error" in status:
                await update.message.reply_text(f"❌ {status['error']}")
                return
            
            health_status = status.get('health_status', {})
            
            if not health_status:
                await update.message.reply_text(f"ℹ️ No health data available for session '{session_name}'")
                return
            
            status_emoji = "🟢" if health_status.get('is_healthy', False) else "🔴"
            
            message = (
                f"{status_emoji} **Health Details: {session_name}**\n\n"
                f"💚 Status: {health_status.get('status', 'unknown')}\n"
                f"🕐 Last verified: {health_status['last_verified']}\n"
            )
            
            if health_status.get('error_message'):
                message += f"❌ Error: {health_status['error_message']}\n"
            
            # Show pair access status
            pair_access = health_status.get('pair_access_status', {})
            if pair_access:
                accessible_pairs = sum(1 for access in pair_access.values() if access)
                total_pairs = len(pair_access)
                
                message += f"\n📋 Pair access: {accessible_pairs}/{total_pairs} accessible\n"
                
                if accessible_pairs < total_pairs:
                    message += "⚠️ Some pairs may have access issues\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in session_health_command: {e}")
            await update.message.reply_text("❌ An error occurred while checking session health")
    
    async def delete_session_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /deletesession command."""
        try:
            args = context.args
            if len(args) < 1:
                await update.message.reply_text(
                    "❌ Usage: `/deletesession <session_name> [force]`\n\n"
                    "Use 'force' flag to delete sessions with active pairs (they will be reassigned)",
                    parse_mode='Markdown'
                )
                return
            
            session_name = args[0]
            force = len(args) > 1 and args[1].lower() == 'force'
            
            # Check session exists
            session_info = await self.database.get_session_info(session_name)
            if not session_info:
                await update.message.reply_text(f"❌ Session '{session_name}' not found")
                return
            
            # Check for active pairs
            pairs = await self.database.get_pairs_by_session(session_name)
            
            if pairs and not force:
                await update.message.reply_text(
                    f"⚠️ Session '{session_name}' has {len(pairs)} active pairs.\n"
                    f"Use `/deletesession {session_name} force` to delete and reassign pairs."
                )
                return
            
            # Confirm deletion
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm Delete", callback_data=f"delete_session_confirm:{session_name}:{force}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="delete_session_cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = (
                f"🗑️ **Confirm Session Deletion**\n\n"
                f"Session: {session_name}\n"
                f"Active pairs: {len(pairs)}\n"
                f"Force mode: {'Yes' if force else 'No'}\n\n"
                f"⚠️ This action cannot be undone!"
            )
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in delete_session_command: {e}")
            await update.message.reply_text("❌ An error occurred while preparing session deletion")
    
    async def optimal_session_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /optimalsession command."""
        try:
            optimal_session = await self.advanced_session_manager.get_optimal_session_for_assignment()
            
            if not optimal_session:
                await update.message.reply_text(
                    "❌ No optimal session found.\n"
                    "All sessions may be at capacity or unhealthy."
                )
                return
            
            # Get session details
            status = await self.advanced_session_manager.get_session_status(optimal_session)
            
            if "error" in status:
                await update.message.reply_text(f"❌ Error getting session details: {status['error']}")
                return
            
            session_info = status['session_info']
            
            message = (
                f"🎯 **Optimal Session for New Pairs**\n\n"
                f"📝 Session: {optimal_session}\n"
                f"📊 Current load: {status['capacity_usage']} ({status['utilization_percent']}%)\n"
                f"⭐ Priority: {session_info['priority']}\n"
                f"💚 Health: {session_info['health_status']}\n"
                f"📱 Phone: {session_info['phone_number'] or 'N/A'}\n\n"
                f"This session has the best combination of priority, capacity, and health."
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in optimal_session_command: {e}")
            await update.message.reply_text("❌ An error occurred while finding optimal session")
    
    async def worker_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /workerstatus command."""
        try:
            worker_groups = self.advanced_session_manager.worker_groups
            
            if not worker_groups:
                await update.message.reply_text("ℹ️ No active worker groups found")
                return
            
            active_workers = sum(1 for wg in worker_groups.values() if wg.is_active)
            total_pairs = sum(len(wg.pair_ids) for wg in worker_groups.values() if wg.is_active)
            
            message = (
                f"👷 **Worker Groups Status**\n\n"
                f"🏃 Active workers: {active_workers}\n"
                f"📊 Total pairs managed: {total_pairs}\n"
                f"📈 Average pairs per worker: {total_pairs / max(active_workers, 1):.1f}\n\n"
            )
            
            # Group workers by session
            session_workers = {}
            for worker_id, worker_group in worker_groups.items():
                if worker_group.is_active:
                    session_name = worker_group.session_name
                    if session_name not in session_workers:
                        session_workers[session_name] = []
                    session_workers[session_name].append(worker_group)
            
            for session_name, workers in session_workers.items():
                session_pairs = sum(len(w.pair_ids) for w in workers)
                message += f"📱 **{session_name}**: {len(workers)} workers, {session_pairs} pairs\n"
                
                for worker in workers[:3]:  # Show first 3 workers
                    last_check = "Never" if not worker.last_health_check else worker.last_health_check.strftime('%H:%M')
                    message += f"  • {worker.worker_id[:12]}... ({len(worker.pair_ids)} pairs, last check: {last_check})\n"
                
                if len(workers) > 3:
                    message += f"  • ... and {len(workers) - 3} more workers\n"
                
                message += "\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in worker_status_command: {e}")
            await update.message.reply_text("❌ An error occurred while fetching worker status")
    
    # Helper methods
    
    async def _show_all_sessions_status(self, update: Update):
        """Show status overview for all sessions."""
        try:
            sessions = await self.database.get_all_sessions()
            
            if not sessions:
                await update.message.reply_text("ℹ️ No sessions found")
                return
            
            message = "📋 **All Sessions Status**\n\n"
            
            for session in sessions:
                status_emoji = "🟢" if session.health_status == "healthy" else "🔴"
                active_emoji = "🟢" if session.is_active else "⚪"
                
                utilization = (session.pair_count / session.max_pairs) * 100 if session.max_pairs > 0 else 0
                
                message += (
                    f"{status_emoji}{active_emoji} **{session.name}**\n"
                    f"   📊 {session.pair_count}/{session.max_pairs} pairs ({utilization:.0f}%)\n"
                    f"   💚 {session.health_status}\n"
                    f"   📱 {session.phone_number or 'N/A'}\n\n"
                )
            
            message += (
                "Use `/sessionstatus <name>` for detailed information\n"
                "Use `/sessionhealth` for health overview"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in _show_all_sessions_status: {e}")
            await update.message.reply_text("❌ An error occurred while fetching sessions status")
    
    async def _parse_pair_specification(self, pair_spec: str) -> List[int]:
        """Parse pair specification string into list of pair IDs."""
        try:
            pair_ids = []
            
            if pair_spec.startswith("all_from:"):
                # Get all pairs from a specific session
                session_name = pair_spec.split(":", 1)[1]
                pairs = await self.database.get_pairs_by_session(session_name)
                return [pair.id for pair in pairs]
            
            # Handle comma-separated IDs and ranges
            parts = pair_spec.split(",")
            
            for part in parts:
                part = part.strip()
                
                if "-" in part and not part.startswith("-"):
                    # Handle range (e.g., "1-5")
                    start, end = map(int, part.split("-", 1))
                    pair_ids.extend(range(start, end + 1))
                else:
                    # Handle single ID
                    pair_ids.append(int(part))
            
            return list(set(pair_ids))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error parsing pair specification '{pair_spec}': {e}")
            return []
    
    async def handle_delete_session_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback for session deletion confirmation."""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "delete_session_cancel":
                await query.edit_message_text("❌ Session deletion cancelled")
                return
            
            if query.data.startswith("delete_session_confirm:"):
                _, session_name, force_str = query.data.split(":", 2)
                force = force_str == "True"
                
                await query.edit_message_text(f"🔄 Deleting session '{session_name}'...")
                
                success = await self.advanced_session_manager.delete_session(session_name, force)
                
                if success:
                    await query.edit_message_text(
                        f"✅ Successfully deleted session '{session_name}'\n"
                        f"{'🔄 Active pairs have been reassigned' if force else ''}"
                    )
                else:
                    await query.edit_message_text(f"❌ Failed to delete session '{session_name}'")
            
        except Exception as e:
            logger.error(f"Error in handle_delete_session_callback: {e}")
            await query.edit_message_text("❌ An error occurred during session deletion")