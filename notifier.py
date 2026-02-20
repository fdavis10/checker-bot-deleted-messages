import asyncio
from typing import Optional

import httpx

from config import BOT_TOKEN, NOTIFICATION_CHAT_ID


async def send_notification(text: str, media_path: str | None = None, media_type: str = "") -> bool:
    """
    Send notification. If media_path set, sends as photo/video/document via Bot API.
    """
    if not BOT_TOKEN or not NOTIFICATION_CHAT_ID:
        return False

    chat_id = NOTIFICATION_CHAT_ID.strip()
    api = f"https://api.telegram.org/bot{BOT_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if media_path and media_type in ("photo", "video", "document", "voice", "video_note", "audio", "animation", "sticker"):
                method = {"photo": "sendPhoto", "video": "sendVideo", "document": "sendDocument",
                         "voice": "sendVoice", "video_note": "sendVideoNote", "audio": "sendAudio",
                         "animation": "sendAnimation", "sticker": "sendSticker"}[media_type]
                url = f"{api}/{method}"
                field = "photo" if media_type == "photo" else media_type
                with open(media_path, "rb") as f:
                    files = {field: f}
                    data = {"chat_id": chat_id}
                    if media_type != "sticker":
                        data["caption"] = text
                        data["parse_mode"] = "HTML"
                    r = await client.post(url, data=data, files=files)
                if media_type == "sticker" and r.is_success and text:
                    await client.post(f"{api}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
            else:
                r = await client.post(
                    f"{api}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )
            return r.is_success
    except Exception:
        return False


def format_notification_edit(
    chat_name: str,
    sender_name: str,
    old_content: str,
    new_content: str,
) -> str:
    """Formatting message when edited"""
    return (
        f"✏️ <b>Редактирование сообщения</b>\n"
        f"💬 Чат: <b>{_esc(chat_name)}</b>\n"
        f"👤 От: <b>{_esc(sender_name)}</b>\n\n"
        f"📝 <b>Было:</b>\n<pre>{_esc(old_content)}</pre>\n\n"
        f"📝 <b>Стало:</b>\n<pre>{_esc(new_content)}</pre>"
    )


def format_notification_delete(
    chat_name: str,
    sender_name: str,
    content: str,
) -> str:
    """Formatin message when deleted"""
    return (
        f"🗑️ <b>Удалённое сообщение</b>\n"
        f"💬 Чат: <b>{_esc(chat_name)}</b>\n"
        f"👤 От: <b>{_esc(sender_name)}</b>\n\n"
        f"📝 <b>Содержимое:</b>\n<pre>{_esc(content)}</pre>"
    )


def _esc(s: str) -> str:
    """Shields HTML."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
