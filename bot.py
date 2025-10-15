import asyncio
import logging
import re

import aiohttp
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import (
    AUTHORIZED_CHATS,
    AUTHORIZED_TOPICS,
    BOT_TOKEN,
    LOG_FORMAT,
    LOG_LEVEL,
    MAX_CONCURRENT_REQUESTS,
    SHORTENERS,
)

# Configure logging
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL.upper())
)
logger = logging.getLogger(__name__)

# Cache for bypassed URLs
url_cache = {}
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

async def is_authorized(update: Update) -> bool:
    """Check if the chat/topic is authorized."""
    chat_id = update.effective_chat.id
    if chat_id in AUTHORIZED_CHATS:
        return True
    if update.effective_message and update.effective_message.message_thread_id:
        topic_id = update.effective_message.message_thread_id
        if topic_id in AUTHORIZED_TOPICS:
            return True
    return False

async def extract_urls(text: str) -> list:
    """Extract URLs from text."""
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?'
    return re.findall(url_pattern, text)

async def bypass_url(session: aiohttp.ClientSession, url: str) -> str:
    """Bypass URL shortener with recursive checking for nested shorteners."""
    async with semaphore:
        if url in url_cache:
            return url_cache[url]

        original_url = url
        current_url = url

        for _ in range(MAX_BYPASS_DEPTH):
            try:
                timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                async with session.get(current_url, allow_redirects=False, timeout=timeout) as response:
                    if response.status in (301, 302, 303, 307, 308):
                        location = response.headers.get('Location')
                        if location:
                            current_url = location
                            if not current_url.startswith('http'):
                                current_url = f"https://{current_url}" if not current_url.startswith('//') else f"https:{current_url}"
                            # Check if the new URL is another shortener
                            if any(shortener in current_url for shortener in SHORTENERS):
                                continue
                            else:
                                break
                        else:
                            break
                    elif response.status == 200:
                        # Check if the current URL is a shortener
                        if any(shortener in current_url for shortener in SHORTENERS):
                            # Try to get the real content URL
                            try:
                                text = await response.text()
                                # Simple regex to find redirect URLs in HTML
                                redirect_match = re.search(r'(?:window\.location|location\.href)\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE)
                                if redirect_match:
                                    current_url = redirect_match.group(1)
                                    if not current_url.startswith('http'):
                                        current_url = f"https://{current_url}" if not current_url.startswith('//') else f"https:{current_url}"
                                    continue
                            except:
                                pass
                        break
                    else:
                        break
            except Exception as e:
                logger.error(f"Error bypassing {current_url}: {e}")
                break

        url_cache[original_url] = current_url
        return current_url

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming messages."""
    if not await is_authorized(update):
        return

    text = update.effective_message.text
    if not text:
        return

    urls = await extract_urls(text)
    if not urls:
        return

    # Process URLs simultaneously
    async with aiohttp.ClientSession() as session:
        tasks = [bypass_url(session, url) for url in urls]
        bypassed_urls = await asyncio.gather(*tasks, return_exceptions=True)

    # Prepare response
    response_lines = []
    for original, bypassed in zip(urls, bypassed_urls):
        if isinstance(bypassed, Exception):
            response_lines.append(f"❌ Failed to bypass: {original}")
        elif bypassed != original:
            response_lines.append(f"🔗 {original}\n✅ {bypassed}")
        else:
            response_lines.append(f"ℹ️ Already bypassed or not a shortener: {original}")

    if response_lines:
        response = "\n\n".join(response_lines)
        await update.effective_message.reply_text(response)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.effective_message.reply_text(
        "Welcome to Link Bypass Bot!\n\n"
        "Send me URLs from supported shorteners and I'll bypass them for you.\n\n"
        "Supported shorteners: " + ", ".join(SHORTENERS)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "Link Bypass Bot Help:\n\n"
        "• Send URLs from supported shorteners\n"
        "• The bot will automatically bypass them\n"
        "• Supports nested shorteners (LoopBypass V1)\n"
        "• Processes multiple URLs simultaneously\n\n"
        "Supported shorteners:\n" + "\n".join(f"• {s}" for s in SHORTENERS)
    )
    await update.effective_message.reply_text(help_text)

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()