import asyncio
import sys


if sys.version_info >= (3, 10):
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client

from config import (
    API_HASH,
    API_ID,
    BOT_TOKEN,
    MAX_CACHED_PER_CHAT,
    NOTIFICATION_CHAT_ID,
    SESSION_NAME,
    SESSION_PATH,
)
from handlers import create_handlers
from message_utils import MessageCache


def main() -> None:
    if not API_ID or not API_HASH:
        print("Add API_ID and API_HASH in .env (get: https://my.telegram.org)")
        sys.exit(1)

    use_saved = not (BOT_TOKEN and NOTIFICATION_CHAT_ID)
    if use_saved:
        print("Bot/chat_id not specified — notifications send in 'Favorite'")
    else:
        print("Notifications will be in private messages with Bot ")

    cache = MessageCache(max_per_chat=MAX_CACHED_PER_CHAT)
    handlers = create_handlers(cache, use_saved_messages=use_saved)

    app = Client(
        SESSION_NAME,
        api_id=API_ID,
        api_hash=API_HASH,
        workdir=str(SESSION_PATH.parent),
    )

    for h in handlers:
        app.add_handler(h)

    print("Loading... (Ctrl+C for exit)")
    app.run()


if __name__ == "__main__":
    main()
