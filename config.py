import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Telegram API (get on https://my.telegram.org)
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Session Pyrogram (created when we first run)
SESSION_NAME = os.getenv("SESSION_NAME", "checker_session")
SESSION_PATH = Path(__file__).parent / f"{SESSION_NAME}.session"

# Bot for notifications (create through @BotFather)
# Notification get in personal messages with bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Chat ID for notification. Get: write bot /start, then /myid
# Or leave empty — then notifications will go to "Favorite" (Saved Messages)
NOTIFICATION_CHAT_ID = os.getenv("NOTIFICATION_CHAT_ID", "")

# Max messages in cache on chat (to not eat memory)
MAX_CACHED_PER_CHAT = int(os.getenv("MAX_CACHED_PER_CHAT", "1000"))
