"""
Image handling commands for the admin bot.
Supports image upload, hash generation, and blocking.
"""
import os
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger
from utils.image_hash import image_hash_manager
import requests

class ImageHandler:
    """Handles image-related admin commands."""
    
    def __init__(self, message_filter=None):
        self.message_filter = message_filter
    
    async def handle_image_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle image uploads for hash generation."""
        if not update.message or not update.message.photo:
            return
        
        try:
            # Get the largest photo
            photo = update.message.photo[-1]
            
            # Download the image
            file = await context.bot.get_file(photo.file_id)
            
            # Download image data
            response = requests.get(file.file_path)
            if response.status_code != 200:
                await update.message.reply_text("❌ Failed to download image.")
                return
            
            image_data = response.content
            
            # Calculate perceptual hash
            image_hash = image_hash_manager.calculate_image_hash(image_data)
            
            if image_hash:
                await update.message.reply_text(
                    f"📸 **Image Hash Generated**\n\n"
                    f"**Hash:** `{image_hash}`\n\n"
                    f"**Commands you can use:**\n"
                    f"• `/blockimage {image_hash}` - Block globally\n"
                    f"• `/blockimage {image_hash} [pair_id]` - Block for specific pair\n"
                    f"• `/unblockimage {image_hash}` - Unblock image\n\n"
                    f"This hash uniquely identifies similar images using perceptual analysis.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Failed to generate image hash. Make sure imagehash library is installed."
                )
                
        except Exception as e:
            logger.error(f"Error handling image upload: {e}")
            await update.message.reply_text(f"❌ Error processing image: {e}")
    
    async def show_image_commands_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help for image-related commands."""
        help_text = (
            "📸 **Image Blocking Commands**\n\n"
            
            "**Upload Image for Hash:**\n"
            "• Send any image to the bot to get its perceptual hash\n\n"
            
            "**Blocking Commands:**\n"
            "• `/blockimage <hash>` - Block image globally\n"
            "• `/blockimage <hash> <pair_id>` - Block for specific pair\n"
            "• `/unblockimage <hash>` - Unblock image globally\n"
            "• `/unblockimage <hash> <pair_id>` - Unblock for specific pair\n\n"
            
            "**Quick Toggles:**\n"
            "• `/blockimages` - Block all images globally\n"
            "• `/allowimages` - Allow all images globally\n\n"
            
            "**How it works:**\n"
            "🔍 Uses perceptual hash (pHash) to identify similar images\n"
            "🎯 Detects images even if slightly modified (resized, compressed)\n"
            "⚡ Fast comparison using Hamming distance\n"
            "💾 Stores blocked hashes for persistent filtering\n\n"
            
            "**Example workflow:**\n"
            "1. Send image to bot → Get hash\n"
            "2. Copy hash from response\n"
            "3. Use `/blockimage <hash>` to block\n"
            "4. Similar images will be automatically filtered"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')