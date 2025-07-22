"""Discord integration for automatic webhook creation."""

import asyncio
import aiohttp
from typing import Dict, Any, Optional
from loguru import logger


class DiscordWebhookManager:
    """Manages Discord webhook creation and validation."""
    
    def __init__(self, discord_bot_token: str):
        self.discord_bot_token = discord_bot_token
        self.headers = {
            'Authorization': f'Bot {discord_bot_token}',
            'Content-Type': 'application/json'
        }
    
    async def create_webhook_for_channel(self, channel_id: int, source_channel_name: str = None) -> Dict[str, Any]:
        """Create a webhook for a Discord channel using source channel name."""
        try:
            # Generate webhook name based on source channel
            webhook_name = f"TG-Forward-{source_channel_name}" if source_channel_name else f"TG-Forward-{channel_id}"
            webhook_name = webhook_name[:80]  # Discord limit
            
            # Create webhook payload
            payload = {
                'name': webhook_name,
                'avatar': None  # Could add a custom avatar later
            }
            
            async with aiohttp.ClientSession() as session:
                # Create webhook
                url = f'https://discord.com/api/v10/channels/{channel_id}/webhooks'
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status == 200:
                        webhook_data = await response.json()
                        return {
                            'success': True,
                            'webhook_url': webhook_data['url'],
                            'webhook_id': webhook_data['id'],
                            'webhook_name': webhook_data['name']
                        }
                    else:
                        error_data = await response.json() if response.content_type == 'application/json' else {'message': 'Unknown error'}
                        return {
                            'success': False,
                            'error': f"Discord API error {response.status}: {error_data.get('message', 'Unknown error')}"
                        }
                        
        except Exception as e:
            logger.error(f"Error creating Discord webhook: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def validate_channel_permissions(self, channel_id: int) -> Dict[str, Any]:
        """Validate bot permissions for a Discord channel."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get channel information
                url = f'https://discord.com/api/v10/channels/{channel_id}'
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        channel_data = await response.json()
                        return {
                            'success': True,
                            'channel_name': channel_data.get('name', 'Unknown'),
                            'channel_type': channel_data.get('type', 0),
                            'guild_id': channel_data.get('guild_id')
                        }
                    else:
                        return {
                            'success': False,
                            'error': f"Cannot access channel {channel_id}. Bot may not have permissions."
                        }
                        
        except Exception as e:
            logger.error(f"Error validating Discord channel: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_channel_webhooks(self, channel_id: int) -> Dict[str, Any]:
        """Get existing webhooks for a channel."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f'https://discord.com/api/v10/channels/{channel_id}/webhooks'
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        webhooks = await response.json()
                        return {
                            'success': True,
                            'webhooks': webhooks
                        }
                    else:
                        return {
                            'success': False,
                            'error': f"Cannot get webhooks for channel {channel_id}"
                        }
                        
        except Exception as e:
            logger.error(f"Error getting Discord webhooks: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class DiscordChannelCommands:
    """Admin commands for Discord channel integration."""
    
    def __init__(self, discord_bot_token: str):
        self.webhook_manager = DiscordWebhookManager(discord_bot_token)
    
    async def validate_discord_channel(self, channel_id: int) -> Dict[str, Any]:
        """Validate Discord channel and return information."""
        return await self.webhook_manager.validate_channel_permissions(channel_id)
    
    async def create_webhook_for_pair(self, channel_id: int, source_name: str) -> Dict[str, Any]:
        """Create webhook for a forwarding pair."""
        return await self.webhook_manager.create_webhook_for_channel(channel_id, source_name)