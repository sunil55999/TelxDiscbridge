
# Telegram ↔ Discord ↔ Telegram Forwarding Bot - Project Structure

## Overview

This project is a sophisticated message forwarding bot that creates a bridge between Telegram channels/chats, Discord channels, and destination Telegram chats. The system uses a **per-pair bot token architecture** with advanced session management to handle multiple forwarding pairs efficiently and securely.

## Message Flow Architecture

```
Telegram Source Chat → Discord Channel → Telegram Destination Chat
     (via User Session)   (via Bot/Webhook)    (via Dedicated Bot Token)
```

**Key Components:**
- **Source**: Telegram user sessions (Telethon) monitor source chats
- **Relay**: Discord bot/webhooks forward messages through Discord channels  
- **Destination**: Individual bot tokens send messages to destination Telegram chats

## Directory Structure

```
forwarder-bot/
├── 📁 admin_bot/              # Administrative interface & commands
├── 📁 attached_assets/        # Documentation & reference materials
├── 📁 config/                 # Configuration management
├── 📁 core/                   # Core business logic
├── 📁 docs/                   # User documentation
├── 📁 handlers/               # Event handlers
├── 📁 sessions/               # Encrypted session storage
├── 📁 tests/                  # Test suites
├── 📁 utils/                  # Utility functions
├── 📄 main.py                 # Application entry point
├── 📄 config.yaml             # Default configuration
├── 📄 .env.example            # Environment variables template
└── 📄 requirements files      # Dependencies
```

## Core Architecture Components

### 1. **Message Orchestrator** (`core/message_orchestrator.py`)
- **Role**: Central coordinator managing message flow
- **Functions**:
  - Coordinates between all platform handlers
  - Manages message callbacks and routing
  - Handles health monitoring and cleanup
  - Provides system statistics and connectivity testing

### 2. **Telegram Source** (`core/telegram_source.py`) 
- **Role**: Monitors Telegram source chats using user sessions
- **Functions**:
  - Manages multiple Telegram user clients (Telethon)
  - Handles new messages, edits, and deletions
  - Applies message filtering and formatting
  - Routes messages to Discord relay

### 3. **Discord Relay** (`core/discord_relay.py`)
- **Role**: Bridges messages through Discord channels
- **Functions**:
  - Sends formatted messages to Discord channels
  - Handles media, embeds, and polls
  - Supports both bot and webhook methods
  - Manages Discord channel permissions

### 4. **Telegram Destination** (`core/telegram_destination.py`)
- **Role**: Delivers messages to destination Telegram chats
- **Functions**:
  - Uses dedicated bot tokens per forwarding pair
  - Handles all message types (text, media, stickers, polls)
  - Manages bot token validation and permissions
  - Supports message editing and deletion sync

## Session Management System

### **Basic Session Manager** (`core/session_manager.py`)
- Encrypted storage of Telegram user sessions
- Session authentication and validation
- OTP verification handling
- Session lifecycle management

### **Advanced Session Manager** (`core/advanced_session_manager.py`)
- Multi-session health monitoring
- Worker group segregation (20-30 pairs per session)
- Bulk operations and session reassignment
- Automatic failover and load balancing

## Administrative System

### **Admin Handler** (`admin_bot/admin_handler.py`)
- Central admin bot interface
- Command routing and validation
- Permission checking and security
- Error handling and notifications

### **Command Categories**

#### **Core Commands** (`admin_bot/commands.py`)
- `/start` - Initialize and check status
- `/help` - Comprehensive help system
- `/status` - System health and statistics

#### **Pair Management** (`admin_bot/enhanced_commands.py`)
- `/addpair` - Create forwarding pairs (wizard)
- `/createpair` - Enhanced pair creation with bot selection
- `/listpairs` - View all active pairs
- `/removepair` - Delete forwarding pairs
- `/validatebot` - Check bot token validity

#### **Session Management** (`admin_bot/unified_session_commands.py`)
- `/addsession` - Unified session creation workflow
- `/sessions` - List sessions with health status
- `/changesession` - Reassign pairs between sessions
- `/sessionhealth` - Detailed health monitoring

#### **Filtering System** (`admin_bot/filter_commands.py`)
- `/blockword` / `/unblockword` - Keyword filtering
- `/blockimages` / `/allowimages` - Media filtering
- `/stripheaders` / `/keepheaders` - Header/footer removal
- `/filterconfig` - Advanced filtering configuration

## Data Management

### **Database Layer** (`core/database.py`)
- **Models**:
  - `ForwardingPair` - Pair configuration and settings
  - `SessionModel` - User session metadata
  - `MessageMapping` - Message ID relationships
  - `BotToken` - Dedicated bot token storage
  - `FilterRule` - Filtering configuration

- **Operations**:
  - CRUD operations for all models
  - Message mapping tracking
  - Health status persistence
  - Audit logging

### **Bot Token Manager** (`core/bot_token_manager.py`)
- Per-pair bot token architecture
- Token validation and health checks
- Automatic token rotation support
- Permission verification

## Message Processing Pipeline

### **1. Message Reception**
```python
Telegram Source → Message Formatter → Message Filter → Discord Relay
```

### **2. Message Formatting** (`core/message_formatter.py`)
- Cross-platform format conversion
- Media handling and optimization
- Reply thread preservation
- Emoji and special character handling

### **3. Message Filtering** (`core/message_filter.py`)
- Keyword blacklisting (global and per-pair)
- Media type filtering
- Header/footer/mention stripping
- Custom filtering rules

### **4. Message Delivery**
```python
Discord Relay → Telegram Destination → Database Mapping Storage
```

## Security & Monitoring

### **Alert System** (`core/alert_system.py`)
- Real-time error monitoring
- Admin notifications with cooldowns
- System health alerts
- Memory and resource monitoring

### **Security Features**
- Encrypted session storage (`utils/encryption.py`)
- Admin access control whitelist
- Token validation and sanitization
- API rate limit compliance

## Configuration Management

### **Settings System** (`config/settings.py`)
- Environment variable parsing
- YAML configuration support
- Production deployment compatibility
- Secure credential handling

### **Environment Loader** (`config/env_loader.py`)
- Type-safe environment variable loading
- Development/production environment detection
- Fallback configuration support

## Command Flow Examples

### **Creating a Forwarding Pair**
```
User: /createpair
Bot: Shows interactive wizard
↓
Bot: Validates Telegram source access
↓
Bot: Creates/validates Discord webhook
↓
Bot: Assigns optimal session
↓
Bot: Validates bot token
↓
Bot: Creates database entry
↓
Bot: Confirms pair creation
```

### **Session Management**
```
User: /addsession my_session +1234567890
Bot: Validates input
↓
Bot: Registers session in database
↓
Bot: Sends OTP to phone
↓
Bot: Shows interactive buttons
↓
User: Clicks "Enter OTP Code"
↓
User: Sends verification code
↓
Bot: Authenticates with Telegram
↓
Bot: Encrypts and stores session
```

## Worker Architecture

### **Process Isolation**
- Each 20-30 forwarding pairs run in isolated worker groups
- Session-based worker segregation prevents cascade failures
- Automatic worker rebalancing and cleanup

### **Health Monitoring**
- **Session Health**: 5-minute intervals
- **Worker Health**: 3-minute intervals  
- **System Cleanup**: Hourly maintenance
- **Database Cleanup**: Daily old data removal

## Integration Points

### **Component Communication**
```python
# Message flow callbacks
TelegramSource.set_message_callback(orchestrator.handle_telegram_message)
DiscordRelay.set_message_callback(orchestrator.handle_discord_message)

# Health monitoring
AdvancedSessionManager → AlertSystem → AdminHandler
```

### **Database Relationships**
```sql
ForwardingPair ← session_name → SessionModel
ForwardingPair ← pair_id → MessageMapping
ForwardingPair ← pair_id → BotToken
```

## Scalability Features

### **Advanced Session Management**
- Dynamic session assignment based on health and capacity
- Bulk pair reassignment between sessions
- Automatic load balancing across sessions
- Session health-based routing

### **Performance Optimizations**
- Asynchronous message processing
- Connection pooling and caching
- Memory leak prevention
- Garbage collection optimization

## Error Handling & Recovery

### **Resilience Patterns**
- Circuit breaker pattern for external API calls
- Exponential backoff for failed operations
- Graceful degradation for partial failures
- Automatic retry with jitter

### **Monitoring & Alerting**
- Comprehensive error logging with context
- Real-time admin notifications
- Health check endpoints
- Performance metrics collection

## Development Workflow

### **Adding New Commands**
1. Define command in appropriate command module
2. Register handler in `AdminHandler`
3. Add help documentation in `ComprehensiveHelp`
4. Implement validation and error handling
5. Add tests and update documentation

### **Extending Message Types**
1. Update `MessageFormatter` for new type
2. Modify Discord and Telegram handlers
3. Update database schema if needed
4. Add filtering support
5. Test cross-platform compatibility

## Production Deployment

### **Environment Setup**
- Environment variables for sensitive data
- YAML configuration for operational settings
- Encrypted session storage with master key
- Process supervision (systemd/supervisor/PM2)

### **Monitoring**
- Health check endpoints
- System resource monitoring  
- Error rate tracking
- Performance metrics

This architecture ensures reliable, scalable, and secure message forwarding with comprehensive administrative control through Telegram bot commands.
