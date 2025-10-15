# Configuration file for Link Bypass Bot

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your actual bot token from @BotFather

# Authorized chats and topics (add chat IDs and topic IDs here)
AUTHORIZED_CHATS = [
    # Example: 123456789,  # Replace with actual chat IDs
]

AUTHORIZED_TOPICS = [
    # Example: 123,  # Replace with actual topic IDs
]

# URL shorteners supported for bypassing
SHORTENERS = [
    'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly', 'is.gd', 'buff.ly',
    'adf.ly', 'shorte.st', 'linkshrink.net', 'short.pe', 'v.gd', 'cutt.ly',
    'tiny.cc', 'rebrand.ly', 'bl.ink', 'linklyhq.com', 'rotf.lol', 'shorturl.at',
    'ouo.io', 'linkvertise.com', 'magy.io', 'exe.io', 'sub2unlock.com'
]

# Bot settings
MAX_BYPASS_DEPTH = 5  # Maximum depth for nested shortener detection
REQUEST_TIMEOUT = 30  # Timeout for HTTP requests in seconds (increased for advanced bypass)
MAX_CONCURRENT_REQUESTS = 5  # Maximum concurrent bypass requests (reduced for stability)
SELENIUM_TIMEOUT = 60  # Timeout for Selenium operations in seconds
MAX_WAIT_TIME = 30  # Maximum wait time for sites with timers

# Advanced bypass settings
ENABLE_CLOUDFLARE_BYPASS = True
ENABLE_SELENIUM_BYPASS = True
ENABLE_HEADLESS_BROWSER = True
BROWSER_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Logging configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'