# Telegram → Discord → Telegram Forwarding Bot

A comprehensive Python-based message forwarding bot that creates a bridge between Telegram and Discord platforms. The system receives messages from Telegram source chats (via user sessions), relays them through Discord channels, and then forwards them to Telegram destination chats.

## Features

- **Multi-Platform Bridge**: Seamlessly forward messages from Telegram → Discord → Telegram
- **Session Management**: Secure encrypted storage of Telegram user sessions  
- **Admin Interface**: Comprehensive Telegram bot commands for managing forwarding pairs
- **Media Support**: Forward photos, documents, videos, audio, stickers, and polls
- **Message Filtering**: Keyword-based filtering and spam detection
- **Database Persistence**: PostgreSQL support for production deployments
- **Worker Architecture**: Scalable design supporting 20-30 pairs per worker process
- **Real-time Monitoring**: Health checks and system status monitoring

## Architecture

### Core Components

- **MessageOrchestrator**: Central coordinator managing message flow
- **TelegramSource**: Handles incoming messages using Telethon user sessions
- **DiscordRelay**: Manages Discord bot interactions for message relay
- **TelegramDestination**: Sends messages to destination chats using Bot API
- **AdminHandler**: Telegram bot interface for configuration and monitoring
- **SessionManager**: Encrypted session storage with Fernet encryption

### Data Flow

1. **Telegram Source → Discord**: User session receives messages → Format conversion → Discord channel
2. **Discord → Telegram Destination**: Discord bot monitors channels → Format messages → Bot API sends to destination
3. **Admin Control**: Telegram admin bot manages pairs, sessions, and monitoring

## Quick Start

### 1. Install Dependencies

All required packages are already installed:
- telethon (Telegram user sessions)
- python-telegram-bot (Bot API)
- discord.py (Discord bot)
- SQLAlchemy (Database ORM)
- cryptography (Session encryption)
- loguru (Logging)

### 2. Configure API Credentials

1.  Create a `.env` file by copying the example file:
    ```bash
    cp .env.example .env
    ```
2.  Edit the `.env` file and fill in your API credentials.

    ```
    # Telegram Bot Token (from @BotFather)
    TELEGRAM_BOT_TOKEN=your_bot_token_here

    # Discord Bot Token (from Discord Developer Portal)
    DISCORD_BOT_TOKEN=your_discord_bot_token_here

    # Telegram API Credentials (from https://my.telegram.org)
    TELEGRAM_API_ID=your_api_id
    TELEGRAM_API_HASH=your_api_hash

    # Admin User IDs (comma-separated Telegram user IDs)
    ADMIN_USER_IDS=123456789,987654321

    # Database URL (PostgreSQL recommended for production)
    DATABASE_URL=postgresql://user:password@localhost/forwarding_bot
    ```

### 3. Run the Bot

```bash
python main.py
```

## Getting API Credentials

### Telegram Bot Token
1. Message @BotFather on Telegram
2. Use `/newbot` command
3. Follow instructions to create your bot
4. Copy the bot token

### Discord Bot Token  
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create "New Application" 
3. Go to "Bot" section
4. Click "Add Bot"
5. Copy the bot token
6. Enable required bot permissions (Send Messages, Embed Links, Attach Files)

### Telegram API Credentials
1. Visit [https://my.telegram.org](https://my.telegram.org)
2. Log in with your phone number
3. Go to "API development tools"
4. Create a new application
5. Copy the `api_id` and `api_hash`

### Admin User IDs
1. Message @userinfobot on Telegram
2. It will reply with your user ID
3. Add any additional admin user IDs

## Usage

### Admin Commands

Once configured, message your admin bot with these commands:

- `/start` - Welcome message and help
- `/help` - Show all available commands
- `/status` - System status and statistics
- `/add_pair` - Add new forwarding pair (interactive)
- `/list_pairs` - Show all forwarding pairs
- `/delete_pair <id>` - Remove forwarding pair
- `/toggle_pair <id>` - Enable/disable pair
- `/add_session` - Add new Telegram user session
- `/list_sessions` - Show available sessions
- `/test_pair <id>` - Test pair connectivity

### Adding Forwarding Pairs

1. Use `/add_pair` command in admin bot
2. Provide required information:
   - **Pair name**: Descriptive name for the pair
   - **Telegram source chat ID**: Source chat/channel ID
   - **Discord channel ID**: Discord channel for relay
   - **Telegram destination chat ID**: Destination chat/channel ID
   - **Session name**: Telegram user session to use

### Session Management

Sessions are encrypted user sessions that allow the bot to receive messages from Telegram chats:

1. Use `/add_session` to start session creation
2. Follow the authentication process (phone number, code, password if needed)
3. Session data is encrypted and stored securely
4. Use sessions in forwarding pairs to access specific chats

## Configuration

The `config.yaml` file contains optional settings that override defaults:

```yaml
# Performance settings
max_pairs_per_worker: 25
message_rate_limit: 30
max_file_size_mb: 50

# Feature toggles
enable_media_forwarding: true
enable_sticker_forwarding: true 
enable_poll_forwarding: true

# Logging
log_level: "INFO"
```

## Database Schema

### ForwardingPair
- Stores forwarding pair configurations
- Links source chat → Discord channel → destination chat
- Includes filtering rules and media settings

### MessageMapping  
- Maps message IDs between platforms
- Enables proper reply threading
- Automatic cleanup of old mappings

### Sessions
- Encrypted Telegram user session storage
- Session validation and management
- Secure encryption with Fernet

## Security Features

- **Session Encryption**: All Telegram session data encrypted with Fernet
- **Admin Authorization**: Command access restricted to configured admin users
- **Data Isolation**: Each session runs in isolated context
- **Secure Storage**: Sensitive data never logged or exposed

## Monitoring & Health Checks

- Real-time system status monitoring
- Component health verification
- Message flow statistics
- Automatic session validation
- Database cleanup and maintenance

## Troubleshooting

### Common Issues

**"Configuration validation failed"**
- Ensure all required environment variables are set
- Check that API tokens are valid and not expired

**"Session not found"**  
- Add user sessions using `/add_session` command
- Verify session names match in forwarding pairs

**"Discord channel access denied"**
- Ensure Discord bot has proper permissions
- Check that channel IDs are correct

**"Database connection failed"**
- Verify DATABASE_URL is correct
- Ensure PostgreSQL server is running

### Logs

Check application logs for detailed error information:
- Console output shows real-time status
- File logs (if configured) contain detailed debugging info
- Admin bot provides status updates and error notifications

## Production Deployment

For production use:
- Use PostgreSQL database (not SQLite)
- Configure proper logging levels  
- Set up process supervision (systemd, supervisor, PM2)
- Monitor system resources and performance
- Regular database backups
- Session key backup and rotation

## Support

The system provides comprehensive error reporting and status monitoring through:
- Console logging with configurable levels
- Admin bot notifications for critical issues  
- Health check endpoints for monitoring systems
- Database query monitoring and optimization

For additional help, check the admin bot `/help` command or review the application logs for specific error details.