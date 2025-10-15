# Link Bypass Bot

An advanced Telegram bot for bypassing URL shorteners with high-speed async processing and nested shortener support.

## Features

- **Fastest Async Processing**: Uses aiohttp for lightning-fast HTTP requests
- **LoopBypass V1**: Automatically detects and bypasses nested shorteners recursively
- **Simultaneous Bypass**: Processes multiple URLs in a single message concurrently
- **Authorization System**: Supports authorized chats and topics only
- **Speed Enhancers**: Includes caching and concurrent request limiting
- **Comprehensive Logging**: Detailed logging for monitoring and debugging

## Supported Shorteners

- bit.ly
- tinyurl.com
- goo.gl
- t.co
- ow.ly
- is.gd
- buff.ly
- adf.ly
- shorte.st
- linkshrink.net
- short.pe
- v.gd
- cutt.ly
- tiny.cc
- rebrand.ly
- bl.ink
- linklyhq.com
- rotf.lol
- shorturl.at
- ouo.io
- linkvertise.com
- magy.io
- exe.io
- sub2unlock.com

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Bot**:
   - Edit `config.py` and replace `BOT_TOKEN` with your bot token from @BotFather
   - Add authorized chat IDs to `AUTHORIZED_CHATS`
   - Add authorized topic IDs to `AUTHORIZED_TOPICS`

3. **Run the Bot**:
   ```bash
   python bot.py
   ```

## Usage

1. Add the bot to your Telegram group or channel
2. Send URLs from supported shorteners
3. The bot will automatically bypass them and reply with the direct links

## Commands

- `/start` - Welcome message
- `/help` - Show help information

## Configuration

All settings can be modified in `config.py`:

- `BOT_TOKEN`: Your Telegram bot token
- `AUTHORIZED_CHATS`: List of authorized chat IDs
- `AUTHORIZED_TOPICS`: List of authorized topic IDs
- `SHORTENERS`: List of supported URL shorteners
- `MAX_BYPASS_DEPTH`: Maximum recursion depth for nested shorteners
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds
- `MAX_CONCURRENT_REQUESTS`: Maximum concurrent bypass requests
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FORMAT`: Logging format string

## Architecture

- **Async Processing**: All HTTP requests are handled asynchronously for maximum speed
- **Caching**: Bypassed URLs are cached to avoid redundant requests
- **Semaphore Limiting**: Concurrent requests are limited to prevent overwhelming servers
- **Error Handling**: Comprehensive error handling with detailed logging
- **Recursive Bypass**: LoopBypass V1 detects nested shorteners and bypasses them recursively

## License

This project is open source. Feel free to modify and distribute.