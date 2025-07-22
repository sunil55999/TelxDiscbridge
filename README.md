# TelxDiscbridge

TelxDiscbridge is a powerful and flexible bot for forwarding messages between Telegram and Discord. It supports message forwarding in both directions, including replies, edits, and deletions. It also includes a number of other features, such as:

*   Per-pair and global message filtering
*   Image and keyword filtering
*   Secure session and token management
*   A comprehensive set of admin commands for managing the bot

## Features

*   **Telegram → Discord → Telegram Forwarding:** Forward messages between Telegram and Discord in both directions.
*   **Reply Preservation:** Replies are preserved when messages are forwarded.
*   **Message Edits and Deletions:** Message edits and deletions are synced between platforms.
*   **Discord Webhooks:** Uses Discord webhooks for more reliable message forwarding.
*   **Per-Pair and Global Filtering:** Filter messages based on keywords, file types, and more.
*   **Secure Session and Token Management:** Encrypts session and token data to keep your accounts secure.
*   **Admin Commands:** A comprehensive set of admin commands for managing the bot.

## Requirements

The following environment variables are required to run the bot:

*   `TELEGRAM_API_ID`: Your Telegram API ID.
*   `TELEGRAM_API_HASH`: Your Telegram API hash.
*   `TELEGRAM_BOT_TOKEN`: The token for your Telegram admin bot.
*   `DISCORD_BOT_TOKEN`: The token for your Discord bot.
*   `ENCRYPTION_KEY`: A secret key for encrypting session and token data. You can generate one using the `cryptography` library.
*   `ADMIN_USER_IDS`: A comma-separated list of Telegram user IDs that are authorized to use the admin commands.

## Setup

1.  Clone the repository:
    ```
    git clone https://github.com/your-username/telxdiscbridge.git
    ```
2.  Install the required dependencies:
    ```
    pip install -r requirements.txt
    ```
3.  Set the required environment variables.
4.  Run the bot:
    ```
    python main.py
    ```

## Usage

The bot is managed through a set of admin commands that can be sent to the Telegram admin bot. The following commands are available:

*   `/addpair`: Start the interactive pair creation wizard.
*   `/removepair <pair_id>`: Remove a forwarding pair.
*   `/listpairs`: List all forwarding pairs.
*   `/addsession <name> <phone>`: Add a new Telegram session.
*   `/sessions`: List all available sessions.
*   `/addbot <name> <token>`: Add a new bot token.
*   `/listbots`: List all available bot tokens.
*   `/removebot <name>`: Remove a bot token.
*   `/blockword <word>`: Block a word globally.
*   `/unblockword <word>`: Unblock a word.
*   `/blockimage <hash>`: Block an image by its perceptual hash.
*   `/showfilters`: Show the current filter settings.
*   `/status`: Show the current status of the bot.
*   `/help`: Show a list of all available commands.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
