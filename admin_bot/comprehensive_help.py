"""Comprehensive help documentation for admin bot commands."""

from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


class ComprehensiveHelp:
    """Enhanced help system with detailed documentation."""
    
    @staticmethod
    def get_main_help() -> str:
        """Get main help message with all commands."""
        return """🤖 **Telegram ↔ Discord ↔ Telegram Forwarding Bot**

**Per-Pair Bot Token Architecture - Enhanced Security**

📋 **CORE COMMANDS**
/start - Initialize bot and check status
/help - Show this help message
/status - Show system status and statistics

🔧 **PAIR MANAGEMENT**
/addpair - Create new forwarding pair (interactive wizard)
/listpairs - List all active forwarding pairs
/removepair <id> - Remove forwarding pair
/validatebot <id> - Validate bot token for pair
/updatebottoken <id> <token> - Update bot token

👥 **SESSION MANAGEMENT**
/addsession - Add new Telegram user session
/sessions - List all sessions with health status
/changesession <pair_id> <session> - Change session for pair

🛡️ **FILTERING & CONTROL**
/blockword <word> - Add word to global filter
/unblockword <word> - Remove word from filter
/showfilters - Show current filters
/filterconfig - Configure media/header/mention filtering

**Quick Filter Commands:**
• `/filterconfig images on/off` - Block image messages
• `/filterconfig headers on/off` - Remove message headers/footers  
• `/filterconfig mentions on/off` - Strip @mentions

📊 **MONITORING**
/logs - Show recent error logs
/health - System health check
/restart - Restart specific components

Use `/help <command>` for detailed information about specific commands.

💡 **Quick Setup:**
1. Add session: `/addsession`
2. Create pair: `/addpair` (follow wizard)
3. Monitor: `/status`"""

    @staticmethod
    def get_command_help(command: str) -> str:
        """Get detailed help for specific command."""
        help_data = {
            "addpair": """🔧 **Add Forwarding Pair - Interactive Wizard**

**Usage:** `/addpair` (interactive) or `/addpair <name> <source> <webhook> <dest> <session> <token>`

**Interactive Mode (Recommended):**
The wizard guides you through 6 steps:
1. **Name:** Unique identifier for the pair
2. **Source Chat:** Telegram chat ID to monitor
3. **Discord Webhook:** Discord webhook URL for relay
4. **Destination Chat:** Telegram chat ID for final messages  
5. **Session:** Telegram user session to use
6. **Bot Token:** Dedicated bot token for destination

**Validation Steps:**
✓ Bot token validation (getMe API)
✓ Chat permission verification
✓ Test message posting confirmation

**Security Features:**
🔒 Bot tokens encrypted before storage
🚫 Tokens never exposed in logs
✅ Multi-step validation process

**Example:**
`/addpair MyPair -1001234567 https://discord.com/api/webhooks/... -1009876543 session1 5555555555:AAA...`""",

            "validatebot": """🔍 **Validate Bot Token**

**Usage:** `/validatebot <pair_id>`

**What it checks:**
✓ Bot token validity (getMe API call)
✓ Bot information (username, name, ID)
✓ Chat access permissions
✓ Message posting capabilities
✓ Edit/delete permissions

**Example Output:**
```
✅ Bot Validation Successful

Pair: MyPair (ID: 123)
Bot: @mybot (My Bot Name)
Bot ID: 5555555555

Chat Permissions:
• Status: administrator
• Send Messages: ✅
• Send Media: ✅
• Edit Messages: ✅
• Delete Messages: ✅
```""",

            "addsession": """👥 **Add Telegram User Session**

**Usage:** `/addsession`

**Interactive Process:**
1. Enter phone number (+1234567890)
2. Receive and enter OTP code
3. Enter 2FA password (if enabled)
4. Session stored encrypted and ready

**Important Notes:**
🔐 Sessions use your personal Telegram account
📱 You'll receive OTP via Telegram mobile app
🔒 All session data encrypted before storage
⚡ Sessions enable message monitoring from source chats

**Session Management:**
• Sessions can monitor multiple source chats
• Each pair uses exactly one session
• Sessions can be reassigned between pairs
• Health monitoring every 5 minutes""",

            "status": """📊 **System Status & Statistics**

**Usage:** `/status`

**Information Displayed:**
📈 **Forwarding Statistics**
• Total active pairs
• Messages processed today
• Success/failure rates

🤖 **Bot Health**
• Per-pair bot token status
• Chat access verification
• Permission validation

💾 **Database Status**
• Connection health
• Storage usage
• Recent activity

👥 **Session Status**
• Active sessions count
• Health scores
• Worker assignments

🔧 **System Resources**
• Memory usage
• Process health
• Error rates

This command provides comprehensive monitoring of all system components.""",

            "listpairs": """📋 **List Forwarding Pairs**

**Usage:** `/listpairs`

**Display Format:**
```
🔗 Pair #123: MyPair
📨 Source: Private Chat (-1001234567)
🌐 Discord: webhook-url
📤 Destination: Group Chat (-1009876543)
🤖 Bot: @mybot (✅ Validated)
🔧 Session: session1 (✅ Healthy)
📊 Status: Active | 42 messages today
```

**Status Indicators:**
✅ Healthy/Validated
⚠️ Warning/Issues
❌ Error/Offline
🔄 Processing/Validating

**Filtering Options:**
• Shows only active pairs by default
• Includes health status for quick monitoring
• Bot validation status per pair"""
        }
        
        return help_data.get(command, f"No detailed help available for command: {command}")

    @staticmethod
    def get_setup_guide() -> str:
        """Get comprehensive setup guide."""
        return """🚀 **Complete Setup Guide**

**Prerequisites:**
1. Telegram user account (for session)
2. Discord server with webhook
3. Telegram bot token from @BotFather

**Step-by-Step Setup:**

**1. Add Telegram Session**
```
/addsession
```
Follow prompts to authenticate your Telegram account.

**2. Create Bot for Destination**
• Message @BotFather on Telegram
• Create new bot: `/newbot`
• Get bot token (format: 5555555555:AAA...)
• Add bot to destination chat
• Grant admin permissions (post messages)

**3. Setup Discord Webhook**
• Open Discord channel settings
• Go to Integrations → Webhooks
• Create new webhook
• Copy webhook URL

**4. Create Forwarding Pair**
```
/addpair
```
Follow interactive wizard with your data.

**5. Monitor & Verify**
```
/status
/validatebot <pair_id>
```

**Security Best Practices:**
🔒 Use dedicated bot tokens per pair
🚫 Never share bot tokens publicly
✅ Validate permissions before going live
📊 Monitor status regularly

**Troubleshooting:**
• Bot can't post: Check admin permissions
• Session issues: Re-add session
• Validation fails: Verify bot token"""

    @staticmethod
    async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show interactive help menu."""
        keyboard = [
            [
                InlineKeyboardButton("🔧 Pair Management", callback_data="help:pairs"),
                InlineKeyboardButton("👥 Sessions", callback_data="help:sessions")
            ],
            [
                InlineKeyboardButton("🛡️ Security", callback_data="help:security"),
                InlineKeyboardButton("📊 Monitoring", callback_data="help:monitoring")
            ],
            [
                InlineKeyboardButton("🚀 Setup Guide", callback_data="help:setup"),
                InlineKeyboardButton("❓ Commands", callback_data="help:commands")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = """🤖 **Interactive Help System**

Choose a category for detailed information:

🔧 **Pair Management** - Creating and managing forwarding pairs
👥 **Sessions** - Telegram user session management  
🛡️ **Security** - Bot tokens and encryption features
📊 **Monitoring** - Status checking and health monitoring
🚀 **Setup Guide** - Complete step-by-step setup
❓ **Commands** - Full command reference

Or type `/help <command>` for specific command help."""

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message, 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup, 
                parse_mode='Markdown'
            )

    @staticmethod
    async def handle_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help menu callback queries."""
        query = update.callback_query
        data = query.data
        
        if data == "help:pairs":
            message = """🔧 **Pair Management Commands**

**Core Commands:**
• `/addpair` - Create new forwarding pair (interactive wizard)
• `/listpairs` - List all active forwarding pairs  
• `/removepair <id>` - Remove forwarding pair
• `/validatebot <id>` - Validate bot token for pair
• `/updatebottoken <id> <token>` - Update bot token

**Features:**
✅ Per-pair dedicated bot tokens
✅ Interactive creation wizard
✅ Comprehensive validation
✅ Encrypted token storage

Back to main menu: /help"""
            
        elif data == "help:sessions":
            message = """👥 **Session Management Commands**

**Core Commands:**
• `/addsession` - Add new Telegram user session
• `/sessions` - List all sessions with health status
• `/changesession <pair_id> <session>` - Change session for pair

**Features:**
🔐 Encrypted session storage
📱 OTP-based authentication
⚡ Health monitoring every 5 minutes
🔄 Session reassignment support

Back to main menu: /help"""
            
        elif data == "help:security":
            message = """🛡️ **Security & Filtering Commands**

**Filtering Commands:**
• `/filterconfig images on/off` - Block/allow image messages
• `/filterconfig videos on/off` - Block/allow video messages  
• `/filterconfig documents on/off` - Block/allow document messages
• `/filterconfig headers on/off` - Strip message headers/footers
• `/filterconfig mentions on/off` - Strip @mentions from messages
• `/filterconfig maxlength <number>` - Set maximum message length

**Word Filtering:**
• `/blockword <word>` - Add word to global filter
• `/unblockword <word>` - Remove word from filter
• `/showfilters` - Show current filter settings

**Security Features:**
🔒 All bot tokens encrypted
🚫 Tokens never exposed in logs
✅ Multi-step validation

Back to main menu: /help"""
            
        elif data == "help:monitoring":
            message = """📊 **Monitoring & Health Commands**

**System Commands:**
• `/status` - Complete system status and statistics
• `/health` - System health check
• `/logs` - Show recent error logs
• `/alerts` - View system alerts

**Validation Commands:**
• `/validatebot <id>` - Validate specific pair bot
• `/testfilter <text>` - Test message against filters

**Information Displayed:**
📈 Forwarding statistics
🤖 Bot health status
💾 Database connection
👥 Session health
🔧 System resources

Back to main menu: /help"""
            
        elif data == "help:setup":
            message = ComprehensiveHelp.get_setup_guide()
            
        elif data == "help:commands":
            message = ComprehensiveHelp.get_main_help()
            
        else:
            # Return to main menu
            await ComprehensiveHelp.show_help_menu(update, context)
            return
        
        # Create back button
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton("🔙 Back to Help Menu", callback_data="help:main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )