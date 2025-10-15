import asyncio
import logging
import random
import re
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse

import aiohttp
import cloudscraper
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    AUTHORIZED_CHATS,
    AUTHORIZED_TOPICS,
    BOT_TOKEN,
    BROWSER_USER_AGENT,
    ENABLE_CLOUDFLARE_BYPASS,
    ENABLE_HEADLESS_BROWSER,
    ENABLE_SELENIUM_BYPASS,
    LOG_FORMAT,
    LOG_LEVEL,
    MAX_BYPASS_DEPTH,
    MAX_CONCURRENT_REQUESTS,
    REQUEST_TIMEOUT,
    SELENIUM_DOMAINS,
    SELENIUM_DRIVER_PATH,
    SELENIUM_TIMEOUT,
    SHORTENERS,
    USER_AGENTS,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL.upper()))

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(console_handler)

# Create file handler
file_handler = RotatingFileHandler("bot.log", maxBytes=1024 * 1024 * 5, backupCount=2)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(file_handler)


# Cache for bypassed URLs
url_cache = {}
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

def get_random_user_agent():
    """Get a random user agent from the list."""
    return random.choice(USER_AGENTS)

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
    url_pattern = r'https?://(?:[-\w\]+)(?:[:\]d+)?(?:/(?:[\w/_.])*(?:\[(?:[\w&=%.])*)?(?:#(?:\w*))?)?'
    return re.findall(url_pattern, text)

async def selenium_bypass(url: str) -> str:
    """Bypass URL using Selenium."""
    logger.info(f"Attempting Selenium bypass for: {url}")
    options = Options()
    if ENABLE_HEADLESS_BROWSER:
        options.add_argument("--headless")
    options.add_argument(f"user-agent={get_random_user_agent()}")

    driver = None
    try:
        if SELENIUM_DRIVER_PATH:
            service = Service(SELENIUM_DRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        driver.get(url)
        await asyncio.sleep(SELENIUM_TIMEOUT)
        final_url = driver.current_url
        logger.info(f"Selenium bypass successful for: {url}, final URL: {final_url}")
        return final_url
    except WebDriverException as e:
        logger.error(f"Selenium bypass failed for {url}: {e}")
        return url
    finally:
        if driver:
            driver.quit()

async def bypass_url(session: aiohttp.ClientSession, url: str) -> str:
    """Bypass URL shortener with advanced techniques."""
    async with semaphore:
        if url in url_cache:
            logger.info(f"Returning cached URL for: {url}")
            return url_cache[url]

        original_url = url
        current_url = url

        for i in range(MAX_BYPASS_DEPTH):
            logger.info(f"Bypass attempt #{i + 1} for: {current_url}")
            try:
                domain = urlparse(current_url).netloc
                headers = {"User-Agent": get_random_user_agent()}

                if ENABLE_SELENIUM_BYPASS and any(domain in d for d in SELENIUM_DOMAINS):
                    current_url = await selenium_bypass(current_url)
                    continue

                if ENABLE_CLOUDFLARE_BYPASS:
                    logger.info("Using cloudscraper for bypass")
                    scraper = cloudscraper.create_scraper()
                    response = await asyncio.to_thread(scraper.get, current_url, allow_redirects=False, timeout=REQUEST_TIMEOUT)
                else:
                    logger.info("Using aiohttp for bypass")
                    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                    async with session.get(current_url, allow_redirects=False, timeout=timeout, headers=headers) as resp:
                        response = resp
                        response.raise_for_status()

                if response.status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if location:
                        current_url = location
                        if not current_url.startswith("http"):
                            current_url = f"https://{current_url}" if not current_url.startswith("//") else f"https:{current_url}"
                        logger.info(f"Redirected to: {current_url}")
                        if any(shortener in current_url for shortener in SHORTENERS):
                            continue
                        else:
                            break
                    else:
                        logger.warning("Redirect status with no Location header")
                        break
                elif response.status == 200:
                    if any(shortener in current_url for shortener in SHORTENERS):
                        logger.info("Attempting to find redirect in page content")
                        soup = BeautifulSoup(response.text, "html.parser")
                        meta_refresh = soup.find("meta", attrs={"http-equiv": "refresh"})
                        if meta_refresh:
                            match = re.search(r"url=(.*)", meta_refresh["content"], re.IGNORECASE)
                            if match:
                                current_url = match.group(1)
                                logger.info(f"Found meta refresh redirect: {current_url}")
                                continue
                        script_tags = soup.find_all("script")
                        for script in script_tags:
                            if script.string:
                                match = re.search(r'(?:window\.location|location\.href)\s*=\s*["\']([^"\']+)["\']', script.string, re.IGNORECASE)
                                if match:
                                    current_url = match.group(1)
                                    logger.info(f"Found JavaScript redirect: {current_url}")
                                    break
                        else:
                            logger.info("No redirect found in page content")
                            break
                    else:
                        break
                else:
                    logger.warning(f"Unhandled status code: {response.status}")
                    break
            except Exception as e:
                logger.error(f"Error bypassing {current_url}", exc_info=True)
                break

        logger.info(f"Final URL for {original_url}: {current_url}")
        url_cache[original_url] = current_url
        return current_url

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming messages."""
    try:
        if not await is_authorized(update):
            return

        text = update.effective_message.text
        if not text:
            return

        urls = await extract_urls(text)
        if not urls:
            return

        async with aiohttp.ClientSession() as session:
            tasks = [bypass_url(session, url) for url in urls]
            bypassed_urls = await asyncio.gather(*tasks, return_exceptions=True)

        response_lines = []
        for original, bypassed in zip(urls, bypassed_urls):
            if isinstance(bypassed, Exception):
                response_lines.append(f"❌ Failed to bypass: {original}")
                logger.error(f"Failed to bypass {original}", exc_info=bypassed)
            elif bypassed != original:
                response_lines.append(f"🔗 {original}\n✅ {bypassed}")
            else:
                response_lines.append(f"ℹ️ Already bypassed or not a shortener: {original}")

        if response_lines:
            response = "\n\n".join(response_lines)
            await update.effective_message.reply_text(response)
    except Exception as e:
        logger.error("An error occurred in process_message", exc_info=True)
        await update.effective_message.reply_text("An unexpected error occurred. Please try again later.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)


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
        "• Supports nested shorteners, Cloudflare, and JavaScript challenges\n\n"
        "Supported shorteners:\n" + "\n".join(f"• {s}" for s in SHORTENERS)
    )
    await update.effective_message.reply_text(help_text)

def main() -> None:
    """Start the bot."""
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

        # Register the error handler
        application.add_error_handler(error_handler)

        logger.info("Bot started successfully")
        application.run_polling()
    except Exception as e:
        logger.critical("Failed to start the bot", exc_info=True)

if __name__ == "__main__":
    main()