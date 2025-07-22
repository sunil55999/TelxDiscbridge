"""Discord relay bot for message forwarding."""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Callable
from io import BytesIO

import discord
from discord.ext import commands
from loguru import logger

from core.database import Database


class DiscordRelay:
    """Handles Discord message relay functionality."""
    
    def __init__(self, bot_token: str, database: Database):
        self.bot_token = bot_token
        self.database = database
        self.bot: Optional[discord.Client] = None
        self.running = False
        self._bot_task: Optional[asyncio.Task] = None
        
        # Callback for when Discord messages are ready to forward to Telegram
        self.on_message_ready: Optional[Callable] = None
        
        # Store webhook URLs for channels
        self.webhooks: Dict[int, str] = {}
    
    async def start(self):
        """Start the Discord relay bot."""
        if self.running:
            logger.warning("Discord relay bot is already running")
            return
        
        try:
            # Create Discord bot instance
            intents = discord.Intents.default()
            intents.message_content = True
            intents.guilds = True
            intents.messages = True
            
            self.bot = discord.Client(intents=intents)
            
            # Setup event handlers
            @self.bot.event
            async def on_ready():
                logger.info(f"Discord bot logged in as {self.bot.user} ({self.bot.user.id})")
            
            @self.bot.event
            async def on_message(message):
                await self._handle_discord_message(message)
            
            @self.bot.event
            async def on_message_edit(before, after):
                await self._handle_discord_message_edit(before, after)
            
            @self.bot.event
            async def on_message_delete(message):
                await self._handle_discord_message_delete(message)
            
            # Start the bot in background
            self.running = True
            bot_task = asyncio.create_task(self.bot.start(self.bot_token))
            
            # Give it a moment to connect
            await asyncio.sleep(2)
            
            # Store the task for cleanup later
            self._bot_task = bot_task
            
        except Exception as e:
            logger.error(f"Failed to start Discord relay bot: {e}")
            raise
    
    async def stop(self):
        """Stop the Discord relay bot."""
        if not self.running:
            return
        
        logger.info("Stopping Discord relay bot...")
        self.running = False
        
        if self._bot_task and not self._bot_task.done():
            self._bot_task.cancel()
            try:
                await self._bot_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error cancelling Discord bot task: {e}")
        
        if self.bot:
            try:
                await self.bot.close()
            except Exception as e:
                logger.error(f"Error stopping Discord bot: {e}")
        
        self.bot = None
        self._bot_task = None
        logger.info("Discord relay bot stopped")
    
    async def send_message_to_discord(self, channel_id: int, message_data: Dict[str, Any], pair_id: int, original_message_id: int) -> Optional[int]:
        """Send a message to Discord channel."""
        if not self.bot or not self.running:
            logger.error("Discord bot is not running")
            return None
        
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Discord channel not found: {channel_id}")
                return None
            
            sent_message = None
            message_type = message_data.get('type', 'text')
            
            if message_type == 'text':
                sent_message = await self._send_text_to_discord(channel, message_data)
            elif message_type in ['photo', 'document', 'video', 'audio']:
                sent_message = await self._send_media_to_discord(channel, message_data)
            elif message_type == 'sticker':
                sent_message = await self._send_sticker_to_discord(channel, message_data)
            elif message_type == 'poll':
                sent_message = await self._send_poll_to_discord(channel, message_data)
            else:
                logger.warning(f"Unsupported Discord message type: {message_type}")
                return None
            
            if sent_message:
                logger.debug(f"Sent message to Discord channel {channel_id}, message ID: {sent_message.id}")
                return sent_message.id
            
        except discord.Forbidden as e:
            logger.error(f"Discord bot forbidden from sending to channel {channel_id}: {e}")
        except discord.NotFound as e:
            logger.error(f"Discord channel not found {channel_id}: {e}")
        except discord.HTTPException as e:
            logger.error(f"Discord HTTP error when sending to channel {channel_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending Discord message to channel {channel_id}: {e}")
        
        return None
    
    async def _send_text_to_discord(self, channel: discord.TextChannel, message_data: Dict[str, Any]) -> Optional[discord.Message]:
        """Send text message to Discord."""
        content = message_data.get('text', '')
        if not content:
            return None
        
        # Discord has a 2000 character limit
        if len(content) > 2000:
            content = content[:1997] + "..."
        
        # Handle embeds if formatting is preserved
        embed = None
        if message_data.get('has_formatting') and message_data.get('create_embed'):
            embed = discord.Embed(description=content, color=0x0099ff)
            if message_data.get('author_name'):
                embed.set_author(name=message_data['author_name'])
            content = None  # Use embed instead of content
        
        return await channel.send(content=content, embed=embed)
    
    async def _send_media_to_discord(self, channel: discord.TextChannel, message_data: Dict[str, Any]) -> Optional[discord.Message]:
        """Send media message to Discord."""
        media_data = message_data.get('media_data')
        filename = message_data.get('filename', 'media')
        caption = message_data.get('caption', '')
        
        if not media_data:
            return None
        
        # Create file object
        file_obj = discord.File(BytesIO(media_data), filename=filename)
        
        # Limit caption length
        if len(caption) > 2000:
            caption = caption[:1997] + "..."
        
        return await channel.send(content=caption if caption else None, file=file_obj)
    
    async def _send_sticker_to_discord(self, channel: discord.TextChannel, message_data: Dict[str, Any]) -> Optional[discord.Message]:
        """Send sticker as image to Discord."""
        sticker_data = message_data.get('media_data')
        if not sticker_data:
            # Fallback to text representation
            sticker_text = message_data.get('sticker_emoji', '🎭 Sticker')
            return await channel.send(f"Sticker: {sticker_text}")
        
        file_obj = discord.File(BytesIO(sticker_data), filename="sticker.png")
        return await channel.send(file=file_obj)
    
    async def _send_poll_to_discord(self, channel: discord.TextChannel, message_data: Dict[str, Any]) -> Optional[discord.Message]:
        """Send poll as Discord embed with reactions."""
        question = message_data.get('poll_question', '')
        options = message_data.get('poll_options', [])
        
        if not question or not options:
            return None
        
        # Create embed for poll
        embed = discord.Embed(title="📊 Poll", description=question, color=0x00ff00)
        
        # Add options to embed
        option_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        for i, option in enumerate(options[:10]):  # Limit to 10 options
            embed.add_field(
                name=f"Option {i + 1}",
                value=f"{option_emojis[i]} {option}",
                inline=False
            )
        
        message = await channel.send(embed=embed)
        
        # Add reaction emojis for voting
        for i in range(min(len(options), 10)):
            try:
                await message.add_reaction(option_emojis[i])
            except discord.HTTPException:
                pass  # Ignore reaction errors
        
        return message
    
    async def _handle_discord_message(self, message: discord.Message):
        """Handle incoming Discord messages (for monitoring purposes)."""
        # Skip messages from our own bot
        if message.author == self.bot.user:
            return
        
        # Skip messages from other bots (optional)
        if message.author.bot:
            return
        
        # This could be used for monitoring or logging Discord activity
        logger.debug(f"Discord message received in channel {message.channel.id}: {message.content[:100]}...")
    
    async def _handle_discord_message_edit(self, before: discord.Message, after: discord.Message):
        """Handle Discord message edits."""
        if after.author == self.bot.user:
            return
        
        logger.debug(f"Discord message edited in channel {after.channel.id}")
    
    async def _handle_discord_message_delete(self, message: discord.Message):
        """Handle Discord message deletions."""
        if message.author == self.bot.user:
            return
        
        logger.debug(f"Discord message deleted in channel {message.channel.id}")
    
    async def edit_discord_message(self, channel_id: int, message_id: int, new_content: str) -> bool:
        """Edit a Discord message."""
        if not self.bot or not self.running:
            logger.error("Discord bot is not running")
            return False
        
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Discord channel not found: {channel_id}")
                return False
            
            message = await channel.fetch_message(message_id)
            if not message:
                logger.error(f"Discord message not found: {message_id}")
                return False
            
            # Limit content length
            if len(new_content) > 2000:
                new_content = new_content[:1997] + "..."
            
            await message.edit(content=new_content)
            logger.debug(f"Edited Discord message {message_id} in channel {channel_id}")
            return True
            
        except discord.HTTPException as e:
            logger.error(f"Failed to edit Discord message {message_id}: {e}")
            return False
    
    async def delete_discord_message(self, channel_id: int, message_id: int) -> bool:
        """Delete a Discord message."""
        if not self.bot or not self.running:
            logger.error("Discord bot is not running")
            return False
        
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Discord channel not found: {channel_id}")
                return False
            
            message = await channel.fetch_message(message_id)
            if not message:
                logger.error(f"Discord message not found: {message_id}")
                return False
            
            await message.delete()
            logger.debug(f"Deleted Discord message {message_id} from channel {channel_id}")
            return True
            
        except discord.HTTPException as e:
            logger.error(f"Failed to delete Discord message {message_id}: {e}")
            return False
    
    async def get_channel_info(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a Discord channel."""
        if not self.bot or not self.running:
            return None
        
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return None
            
            return {
                'id': channel.id,
                'name': channel.name,
                'type': str(channel.type),
                'guild_id': channel.guild.id if channel.guild else None,
                'guild_name': channel.guild.name if channel.guild else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get Discord channel info for {channel_id}: {e}")
            return None
    
    async def test_channel_access(self, channel_ids: List[int]) -> Dict[int, bool]:
        """Test if the bot has access to specific Discord channels."""
        results = {}
        
        if not self.bot or not self.running:
            return {channel_id: False for channel_id in channel_ids}
        
        for channel_id in channel_ids:
            try:
                channel = self.bot.get_channel(channel_id)
                if channel and channel.permissions_for(channel.guild.me).send_messages:
                    results[channel_id] = True
                else:
                    results[channel_id] = False
            except Exception as e:
                logger.error(f"Bot cannot access Discord channel {channel_id}: {e}")
                results[channel_id] = False
        
        return results
    
    def set_message_callback(self, callback: Callable):
        """Set callback for when messages are ready to forward."""
        self.on_message_ready = callback
