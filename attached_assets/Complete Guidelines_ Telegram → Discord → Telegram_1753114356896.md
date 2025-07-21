<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# Complete Guidelines: Telegram → Discord → Telegram Forwarding Bot

## Overview

These guidelines detail the design, operation, session management, and administrative practices for a scalable message-forwarding bot that relays messages from Telegram (Source) → Discord (Relay) → Telegram (Destination). The solution is engineered for reliability, extensibility, and total configuration via Telegram bot commands.

## 1. **System Architecture**

- **Message Flow:**
Telegram (source chat, via user session) → Discord relay (webhook/bot) → Telegram (destination chat, via bot).
- **Pair-Based Routing:**
Each forwarding pair defines a unique Telegram source and a Telegram destination, connected by a mapped Discord channel.
- **Modular Workers:**
Groups of 20–30 forwarding pairs are handled by separate worker processes for efficiency and memory safety.
- **No External GUI:**
All control, setup, and monitoring occur through Telegram bot commands.


## 2. **Tech Stack**

| Layer | Technology |
| :-- | :-- |
| Language | Python 3.10+ |
| Telegram Source | Telethon |
| Telegram Destination | python-telegram-bot |
| Discord Relay | discord.py (bot) / requests |
| Data Storage | SQLite3 / Redis / PostgreSQL |
| Async Orchestration | asyncio \& aiomultiprocess |
| Config Management | YAML / TOML / JSON |
| Logging | loguru |
| Supervision (Optional) | systemd / supervisor / PM2 |

## 3. **Directory Structure Example**

```
forwarder-bot/
├── core/                 # Logic for format/relay
├── db/                   # ORM models, session schema
├── handlers/             # Event listeners
├── config/               # .env, YAML
├── admin_bot/            # Telegram admin commands
├── jobs/                 # Cleanup, health schedulers
├── utils/                # Helpers (parsing, emoji)
├── requirements.txt      # Python dependencies
└── README.md             # Documentation
```


## 4. **Message Handling**

- **Formatting \& Preservation:** Retain markdown, HTML, emoji, web previews, polls, replies, and media.
- **Reply Tracing:** Threaded replies are maintained via ID mapping.
- **Edit/Deletion Sync:** Message edits/deletes propagate through the relay.
- **Fallbacks:** Where platform features mismatch (e.g., premium telegram emoji), provide best-effort translation or replacements.


## 5. **Filtering \& Blocking**

- **Keyword Blocking:**
    - Blacklist at global or per-pair level; messages containing blacklisted words/phrases are blocked or redacted.
- **Image/Media Blocking:**
    - Toggle per-pair or global settings to allow/block photos, videos, GIFs, stickers, documents.
- **Header/Footer/Mention Stripping:**
    - Regex-based removal configured by admin.
- **Configuration:**
    - All filter settings and blocks are managed via Telegram bot commands.


## 6. **Admin Controls (Telegram Bot Only)**

| Command | Description |
| :-- | :-- |
| `/addpair` | Add a new forwarding route |
| `/editpair <pair>` | Update settings for a pair |
| `/removepair` | Delete or disable a pair |
| `/listpairs` | List all routing pairs |
| `/blockword` | Add global/pair keyword block |
| `/blockimage` | Block image/media globally or for a pair |
| `/allowimage` | Unblock images/media globally or for a pair |
| `/status` | Current system and worker state |
| `/cleanmem` | Force garbage collection/cleanup |
| `/restartWorker` | Restart select worker processes |
| `/listblocks` | Show all current blocks/filters |
| `/changesession` | Reassign session for pairs (bulk or individual) |

- Only admin-whitelisted Telegram users can perform sensitive operations.


## 7. **Session Management Guidelines**

### **Session Structure \& Mapping**

- Each pair is assigned a specific Telegram session file or identifier.
- Session mappings are stored in secure config (YAML, JSON) or a relational DB.


### **Onboarding \& Assigning Sessions**

- Register new sessions through the Telegram admin bot or dedicated script.
- Authenticate/log new user sessions with Telethon, verifying access to all assigned channels/groups.
- Map one or more pairs to any session—supporting dynamic reassignment.


### **Bulk Session Swapping**

- Bulk reassign sessions using admin bot commands (e.g., `/changesession <session> pair1,pair2,...`).
- Ensure sessions are validated and paired workers are reloaded to apply changes.


### **Session Rotation \& Health**

- Monitor session health (auto-check for expired/missing/limited access).
- On session failure, send alerts and optionally auto-switch affected pairs to a backup session.
- Rotate sessions if required for compliance or to avoid rate limits.


### **Security \& Logging**

- Encrypt all session files/credentials at rest.
- Log session changes, migrations, and management actions.
- Restrict all session and pair management commands to admin users only.


## 8. **Resource, Health, and Memory Management**

- **Sharded Processing:**
Run 20–30 pairs per worker process for stability.
- **Async Cleanup:**
Scheduled garbage collection, RAM cleanup, and stale data removal.
- **Health Checks:**
Lightweight CPU/RAM monitoring, stats accessible via bot commands.
- **Error Logging:**
loguru-based logs, errors/alerts sent to admin via Telegram.


## 9. **Persistence and State Management**

- Store all configuration, session, routing, and blocklists in a secure persistent database.
- Maintain mappings for message IDs (for reply and edit synchronization).
- Clean up expired or obsolete mappings and session info regularly.


## 10. **Security Principles**

- Encrypt tokens, session files, and sensitive config.
- Only owner-approved Telegram user IDs may issue critical commands.
- Limit API rates and monitor for abnormal throughput or abuse.


## 11. **Best Practices**

- Test changes on a single pair before applying in bulk.
- Check session validity and chat permissions when reassigning sessions.
- Add/rotate sessions with minimal downtime by overlapping worker restarts.
- Document and guide all admins via `/help` or similar command.
- Review logs and alerts regularly for operational anomalies.


## 12. **Sample requirements.txt**

```
telethon==1.32.0
python-telegram-bot==20.6
discord.py==2.3.2
requests==2.31.0
SQLAlchemy==2.0.29
aiomultiprocess==0.9.0
apscheduler==3.10.4
loguru==0.7.2
pyyaml==6.0.1
cryptography==42.0.5
python-dotenv==1.0.1
emoji==2.10.0
```


## 13. **Documentation and Support**

- Keep code and configs version-controlled.
- Provide detailed README, including admin command reference, session handling procedures, and troubleshooting guides.
- Ensure all admins are briefed on operational routines and safety procedures.

These guidelines ensure your Telegram → Discord → Telegram bot is resilient, scalable, and fully controllable, supporting robust message handling, resource efficiency, and easy, secure operation from an admin’s perspective.

