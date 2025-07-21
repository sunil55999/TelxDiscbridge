# Telegram → Discord → Telegram Forwarding Bot

A sophisticated Python-based message forwarding bot that creates a bridge between Telegram and Discord platforms with advanced multi-session management capabilities.

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd telegram-discord-forwarding-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
# or with uv
uv install
```

### 3. Configure Environment Variables
```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your API credentials
nano .env
```

### 4. Run the Bot
```bash
python3 main.py
```

## 📋 Prerequisites

### Required API Credentials
- **Telegram Bot Token** - Get from [@BotFather](https://t.me/BotFather)
- **Telegram API Credentials** - Get from [my.telegram.org](https://my.telegram.org)
- **Discord Bot Token** - Get from [Discord Developer Portal](https://discord.com/developers/applications)
- **Admin User ID** - Your Telegram user ID

### System Requirements
- Python 3.9+
- SQLite/PostgreSQL database
- Stable internet connection

## 🔧 Configuration

### Environment Variables
All configuration is managed through environment variables. See [Environment Setup Guide](docs/environment_setup.md) for detailed instructions.

**Required Variables:**
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_API_ID=your_api_id  
TELEGRAM_API_HASH=your_api_hash
DISCORD_BOT_TOKEN=your_discord_token
ADMIN_USER_IDS=123456789
```

**Optional Variables:**
```env
DATABASE_URL=sqlite:///forwarding_bot.db
LOG_LEVEL=INFO
MAX_PAIRS_PER_WORKER=25
ENABLE_MEDIA_FORWARDING=true
```

## 📱 Usage

### Adding Sessions
Use the unified session management command:
```
/addsession my_session +1234567890
```

The bot will:
1. Register your session
2. Send OTP to your phone
3. Guide you through verification
4. Activate the session for use

### Managing Forwarding Pairs
```
/addpair - Add new forwarding pair
/listpairs - View all pairs
/removepair - Delete a pair
/status - Check system status
```

### Admin Commands
```
/help - Show all commands
/addsession - Add new Telegram session
/sessions - List available sessions  
/changesession - Change pair session
```

## 🏗️ Architecture

### Core Components
- **Message Orchestrator** - Central message flow coordinator
- **Session Manager** - Secure Telegram session handling
- **Database Layer** - SQLAlchemy-based data persistence
- **Admin Interface** - Telegram bot for configuration
- **Environment Loader** - Flexible configuration management

### Platform Handlers
- **Telegram Source** - Receives messages via Telethon
- **Discord Relay** - Forwards through Discord channels
- **Telegram Destination** - Sends to target Telegram chats

### Advanced Features
- **Multi-Session Support** - Handle multiple Telegram accounts
- **Worker Segregation** - Isolated processing groups
- **Health Monitoring** - Continuous session health checks
- **Bulk Operations** - Efficient pair management
- **Security** - Encrypted session storage

## 📚 Documentation

- [Environment Setup Guide](docs/environment_setup.md) - Complete configuration guide
- [Unified Session Guide](docs/unified_session_guide.md) - Session management help
- [Advanced Session Management](docs/advanced_session_management.md) - Technical details

## 🚀 Deployment

### Local Development
Use `.env` file for configuration:
```bash
cp .env.example .env
# Edit .env with your credentials
python3 main.py
```

### Production (Replit)
1. Set environment variables in Replit Secrets
2. Deploy directly - no additional setup needed

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python3", "main.py"]
```

### Heroku
```bash
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set TELEGRAM_API_ID=your_api_id
# ... set all required variables
git push heroku main
```

## 🔒 Security

- All API credentials stored as environment variables
- Session files encrypted with master key
- Admin access controlled by user ID whitelist
- Automatic cleanup of failed authentications
- No sensitive data in version control

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if needed
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

- Check the documentation in `/docs` folder
- Review environment setup guide
- Verify API credentials are correct
- Check logs for specific error messages

## 🎯 Features

✅ **Multi-Platform Forwarding** - Telegram ↔ Discord ↔ Telegram  
✅ **Advanced Session Management** - Multiple Telegram accounts  
✅ **Interactive Setup** - Step-by-step session configuration  
✅ **Environment Variables** - Secure configuration management  
✅ **Health Monitoring** - Automatic session health checks  
✅ **Worker Segregation** - Isolated processing for scalability  
✅ **Media Support** - Forward images, videos, documents  
✅ **Admin Interface** - Complete bot management via Telegram  
✅ **Production Ready** - Supports Docker, Heroku, Replit deployments