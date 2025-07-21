# Telegram → Discord → Telegram Forwarding Bot

## Overview

This is a complete Python-based message forwarding bot that creates a bridge between Telegram and Discord platforms. The system receives messages from Telegram source chats (via user sessions), relays them through Discord channels, and then forwards them to Telegram destination chats. The bot operates on a pair-based routing system where each forwarding pair defines a unique connection between a Telegram source, Discord channel, and Telegram destination.

**Current Status:** Successfully migrated to Replit environment and fully operational. All API credentials configured and bot components running successfully.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

**July 21, 2025 - Advanced Multiple Session Support Implemented**
✓ Enhanced database schema with comprehensive session metadata (health, priority, capacity, worker assignments)
✓ Implemented AdvancedSessionManager with sophisticated session lifecycle management
✓ Added worker segregation system - each 20-30 pairs run in isolated worker groups
✓ Created bulk session reassignment functionality with capacity validation and health checks
✓ Implemented continuous health monitoring system with 5-minute interval checks
✓ Added 13 new admin commands for complete session management
✓ Created comprehensive test suite and documentation for session management
✓ Integrated security features with admin whitelist and encrypted session storage
✓ Added automatic worker rebalancing and cleanup processes
✓ Implemented optimal session selection algorithm for new pair assignments
✓ Fixed OTP verification process with real Telegram authentication
✓ Simplified session registration and authentication workflow
✓ Added step-by-step session help guide with `/sessionhelp` command
✓ Improved error handling and user guidance for authentication issues

## System Architecture

The application follows a modular, asynchronous architecture built around Python's asyncio framework. The system is designed to handle multiple forwarding pairs efficiently using worker processes and provides administrative control through Telegram bot commands.

### Core Architecture Components

1. **Message Orchestrator**: Central coordinator that manages the flow between all platform handlers
2. **Platform Handlers**: Separate modules for Telegram source (Telethon), Discord relay (discord.py), and Telegram destination (python-telegram-bot)
3. **Session Management**: Secure handling of Telegram user sessions with encryption
4. **Database Layer**: SQLAlchemy-based data persistence for forwarding pairs and message mappings
5. **Admin Interface**: Telegram bot for configuration and monitoring

## Key Components

### Core Modules

- **MessageOrchestrator**: Coordinates message flow between all platforms
- **TelegramSource**: Handles incoming messages from Telegram using Telethon user sessions
- **DiscordRelay**: Manages Discord bot/webhook interactions for message relay
- **TelegramDestination**: Sends messages to destination Telegram chats using bot API
- **SessionManager**: Basic encrypted Telegram user session storage and authentication
- **AdvancedSessionManager**: Sophisticated multi-session management with health monitoring, worker segregation, and bulk operations
- **Database**: Enhanced SQLAlchemy models with comprehensive session metadata, health tracking, and worker assignments

### Administrative System

- **AdminHandler**: Enhanced admin bot interface with support for advanced session management
- **AdminCommands**: Basic administrative commands for pair management
- **EnhancedAdminCommands**: Advanced session management commands (13 new commands including registration, authentication, health monitoring, bulk operations)
- **Configuration Management**: YAML/environment-based settings with validation

### Utility Systems

- **MessageFormatter**: Handles cross-platform message formatting and media conversion
- **MessageFilter**: Content filtering system with keyword blocking and spam detection
- **EncryptionManager**: Secure encryption/decryption for sensitive session data
- **Logger**: Structured logging with file rotation and multiple output levels

## Data Flow

1. **Telegram Source → Discord**:
   - Telethon client receives messages from source chats
   - MessageFormatter converts Telegram message format to Discord-compatible format
   - MessageFilter applies content filtering rules
   - DiscordRelay sends message to mapped Discord channel

2. **Discord → Telegram Destination**:
   - Discord bot monitors for new messages in relay channels
   - MessageOrchestrator processes Discord messages
   - TelegramDestination sends formatted message to destination Telegram chat
   - Database stores message ID mappings for reply threading

3. **Administrative Control**:
   - Admin commands received via Telegram bot
   - Database operations for pair management
   - Session management for user authentication
   - Real-time status monitoring and configuration updates

## External Dependencies

### Platform APIs
- **Telegram Bot API**: For destination message sending and admin interface
- **Telegram MTProto API**: For source message receiving via Telethon
- **Discord Bot API**: For relay channel message handling

### Database
- **SQLAlchemy**: ORM for database operations
- **SQLite/PostgreSQL**: Data persistence layer
- **Async database support**: For non-blocking database operations

### Security & Utilities
- **Cryptography**: For session data encryption
- **Loguru**: Advanced logging with rotation and formatting
- **YAML/TOML**: Configuration file parsing

## Deployment Strategy

### Process Architecture
- **Main Process**: Coordinates all components and handles admin interface
- **Advanced Session Manager**: Manages multiple Telegram user sessions with health monitoring
- **Worker Groups**: Automated groups of 20-30 forwarding pairs per session with process isolation
- **Health Monitoring Loops**: Background processes for session health checks (5-min intervals), cleanup (hourly), and worker management (3-min intervals)
- **Session Isolation**: Each Telegram user session runs in isolated worker groups with automatic failover

### Configuration Management
- Environment variables for sensitive data (tokens, API keys)
- YAML configuration files for operational settings
- Encrypted session storage with master key encryption

### Monitoring & Maintenance
- Structured logging with multiple output levels (console, file, error-only)
- Health check endpoints for process monitoring
- Automatic session cleanup and database maintenance
- Process supervision support (systemd/supervisor/PM2)

### Scalability Considerations
- **Advanced Worker Segregation**: Automatic worker group creation and management for each session
- **Dynamic Load Balancing**: Intelligent pair distribution and worker rebalancing
- **Health-based Routing**: Optimal session selection algorithm for new pair assignments
- **Bulk Operations**: Efficient bulk reassignment of pairs between sessions
- **Capacity Management**: Configurable limits per session with automatic enforcement
- **Database connection pooling** for high-throughput scenarios
- **Async/await patterns** throughout for efficient resource utilization
- **Memory-safe process isolation** for large-scale deployments supporting hundreds of forwarding pairs across dozens of sessions