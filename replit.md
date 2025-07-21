# Telegram → Discord → Telegram Forwarding Bot

## Overview

This is a complete Python-based message forwarding bot that creates a bridge between Telegram and Discord platforms. The system receives messages from Telegram source chats (via user sessions), relays them through Discord channels, and then forwards them to Telegram destination chats. The bot operates on a pair-based routing system where each forwarding pair defines a unique connection between a Telegram source, Discord channel, and Telegram destination.

**Current Status:** Fully implemented and ready for deployment - awaiting API credentials configuration for testing.

## User Preferences

Preferred communication style: Simple, everyday language.

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
- **SessionManager**: Manages encrypted Telegram user session storage and authentication
- **Database**: SQLAlchemy models for forwarding pairs, message mappings, and session data

### Administrative System

- **AdminHandler**: Main admin bot interface using python-telegram-bot
- **AdminCommands**: Implementation of administrative commands for pair management
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
- **Worker Processes**: Groups of 20-30 forwarding pairs handled by separate processes
- **Session Isolation**: Each Telegram user session runs in isolated context

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
- Modular worker design allows horizontal scaling
- Database connection pooling for high-throughput scenarios
- Async/await patterns throughout for efficient resource utilization
- Memory-safe process isolation for large-scale deployments