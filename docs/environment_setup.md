# Environment Variables Setup Guide

## Overview

The project now uses environment variables for all configuration, supporting both `.env` files for local development and system environment variables for production deployments.

## Quick Setup

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Fill in your API credentials:**
   - Get tokens from the respective services
   - Edit `.env` file with your actual values
   - Never commit `.env` to version control

3. **Run the bot:**
   ```bash
   python3 main.py
   ```

## Required Environment Variables

### Core API Credentials

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `TELEGRAM_BOT_TOKEN` | Bot token for Telegram API | [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_API_ID` | App ID for Telegram client | [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_API_HASH` | App hash for Telegram client | [my.telegram.org](https://my.telegram.org) |
| `DISCORD_BOT_TOKEN` | Discord bot token | [Discord Developer Portal](https://discord.com/developers/applications) |
| `ADMIN_USER_IDS` | Comma-separated Telegram user IDs | Your Telegram user ID |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///forwarding_bot.db` | Database connection string |
| `ENCRYPTION_KEY` | Auto-generated | 32-character encryption key for sessions |

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | `forwarding_bot.log` | Log file path |
| `MAX_PAIRS_PER_WORKER` | `25` | Maximum forwarding pairs per worker |
| `WORKER_TIMEOUT` | `300` | Worker timeout in seconds |
| `MESSAGE_RATE_LIMIT` | `30` | Messages per minute limit |

### Feature Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_MEDIA_FORWARDING` | `true` | Forward images, videos, documents |
| `ENABLE_STICKER_FORWARDING` | `true` | Forward stickers and animations |
| `ENABLE_POLL_FORWARDING` | `true` | Forward polls and surveys |
| `MAX_FILE_SIZE_MB` | `50` | Maximum file size for forwarding |

## Environment Variable Formats

### Boolean Values
```env
# These all evaluate to True
ENABLE_MEDIA_FORWARDING=true
ENABLE_MEDIA_FORWARDING=1  
ENABLE_MEDIA_FORWARDING=yes
ENABLE_MEDIA_FORWARDING=on

# These all evaluate to False
ENABLE_MEDIA_FORWARDING=false
ENABLE_MEDIA_FORWARDING=0
ENABLE_MEDIA_FORWARDING=no
ENABLE_MEDIA_FORWARDING=off
```

### List Values
```env
# Comma-separated values
ADMIN_USER_IDS=123456789,987654321,555666777
```

### Numeric Values
```env
# Plain numbers
MAX_PAIRS_PER_WORKER=25
MESSAGE_RATE_LIMIT=30
MAX_FILE_SIZE_MB=50
```

## Getting API Credentials

### 1. Telegram Bot Token
1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Choose a name and username for your bot
4. Copy the token provided
5. Set `TELEGRAM_BOT_TOKEN` in your `.env` file

### 2. Telegram API Credentials
1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in with your phone number
3. Go to "API Development Tools"
4. Create a new application
5. Copy the `App api_id` and `App api_hash`
6. Set `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`

### 3. Discord Bot Token
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" section
4. Click "Reset Token" and copy the token
5. Set `DISCORD_BOT_TOKEN`

### 4. Admin User IDs
1. Start a chat with [@userinfobot](https://t.me/userinfobot) on Telegram
2. Send any message to get your user ID
3. Add your ID to `ADMIN_USER_IDS`

## Example .env File

```env
# Core API Credentials
TELEGRAM_BOT_TOKEN=1234567890:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPxx
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
DISCORD_BOT_TOKEN=AAAABBBBCCCCDDDDEEEEFFFFGGGG.HHHIII.JJJKKKLLLMMMNNNOOOPPPQQQRRRSss

# Admin Configuration
ADMIN_USER_IDS=123456789,987654321

# Optional Settings
LOG_LEVEL=INFO
MAX_PAIRS_PER_WORKER=25
ENABLE_MEDIA_FORWARDING=true
MAX_FILE_SIZE_MB=50
```

## Production Deployment

For production deployments (like Replit, Heroku, etc.), set environment variables through the platform's interface instead of using a `.env` file:

### Replit
1. Go to your Repl's "Secrets" tab
2. Add each environment variable as a secret
3. The bot will automatically use these values

### Heroku
```bash
heroku config:set TELEGRAM_BOT_TOKEN=your_token_here
heroku config:set TELEGRAM_API_ID=your_api_id
# ... etc for each variable
```

### Docker
```bash
docker run -e TELEGRAM_BOT_TOKEN=your_token \
           -e TELEGRAM_API_ID=your_api_id \
           your-bot-image
```

## Configuration Priority

Environment variables are loaded in this order (higher priority overrides lower):

1. **System environment variables** (highest priority)
2. **`.env` file variables**
3. **YAML config file values** 
4. **Default values** (lowest priority)

## Security Best Practices

✅ **Do:**
- Use `.env` files for local development
- Add `.env` to your `.gitignore` 
- Use platform-specific secrets for production
- Rotate API tokens regularly
- Limit admin user IDs to trusted users

❌ **Don't:**
- Commit `.env` files to version control
- Share API tokens in chat or email
- Use the same tokens across environments
- Store production credentials locally

## Troubleshooting

### Missing Variables
If you get validation errors, check that all required variables are set:
```bash
python3 -c "from config.settings import Settings; print(Settings().validate())"
```

### Invalid Formats
- **Numeric values:** Must be valid integers
- **Boolean values:** Use true/false, 1/0, yes/no, on/off
- **List values:** Comma-separated with no spaces around commas

### Environment Not Loading
- Check that `.env` file exists in project root
- Verify file has correct format (KEY=value)
- Ensure python-dotenv is installed: `pip install python-dotenv`

## Migration from YAML Configuration

The bot still supports YAML configuration for backward compatibility, but environment variables take precedence. To migrate:

1. Copy values from `config.yaml` to `.env`
2. Set environment variables for production
3. Keep `config.yaml` for non-sensitive defaults only

This setup provides maximum flexibility for both development and production environments while maintaining security best practices.