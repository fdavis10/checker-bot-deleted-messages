import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not BOT_TOKEN:
    print("Add BOT_TOKEN in .env")
    sys.exit(1)


async def main():
    import httpx

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    print("Write bot any message (example /start), then enter 'Enter' here...")
    input()

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        data = r.json()
    if not data.get("ok"):
        print("Ошибка:", data)
        return
    results = data.get("result", [])
    if not results:
        print("Not updates. Check, what wrote bot.")
        return
    last = results[-1]
    msg = last.get("message") or last.get("edited_message")
    if not msg:
        print("Couldn't extract the message")
        return
    chat_id = msg.get("chat", {}).get("id")
    print(f"\Yout NOTIFICATION_CHAT_ID: {chat_id}")
    print("Add in .env: NOTIFICATION_CHAT_ID=" + str(chat_id))


if __name__ == "__main__":
    asyncio.run(main())
