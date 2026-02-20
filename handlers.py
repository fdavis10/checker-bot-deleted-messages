from pathlib import Path

from pyrogram import Client
from pyrogram.handlers import DeletedMessagesHandler, EditedMessageHandler, MessageHandler
from pyrogram.types import Message

from message_utils import CachedMessage, MessageCache, describe_message
from notifier import (
    format_notification_delete,
    format_notification_edit,
    send_notification,
)

MEDIA_SEND_METHODS = {
    "photo": "send_photo",
    "video": "send_video",
    "document": "send_document",
    "voice": "send_voice",
    "video_note": "send_video_note",
    "audio": "send_audio",
    "sticker": "send_sticker",
    "animation": "send_animation",
}


def create_handlers(cache: MessageCache, use_saved_messages: bool = False):
    """Create handlers. use_saved_messages=True — send in 'Favorite' through app."""

    async def on_message(client: Client, msg: Message) -> None:
        if not msg.chat or not msg.from_user and not msg.sender_chat:
            return
        if msg.outgoing:
            return
        cache.put(msg)

    async def _send(client: Client, text: str, cached: CachedMessage | None = None) -> None:
        file_id = cached.media_file_id if cached else None
        media_type = cached.media_type if cached else ""
        sent = False

        if file_id and media_type and media_type in MEDIA_SEND_METHODS:
            if use_saved_messages and client:
                try:
                    method = getattr(client, MEDIA_SEND_METHODS[media_type])
                    await method("me", file_id, caption=text, parse_mode="html")
                    sent = True
                except Exception:
                    pass
            if not sent:
                path = await client.download_media(file_id, in_memory=False)
                if path:
                    try:
                        sent = await send_notification(text, media_path=str(path), media_type=media_type)
                    finally:
                        Path(path).unlink(missing_ok=True)
        if not sent:
            if use_saved_messages and client:
                try:
                    await client.send_message("me", text, parse_mode="html")
                except Exception:
                    await send_notification(text)
            else:
                await send_notification(text)

    async def on_edited(client: Client, msg: Message) -> None:
        if not msg.chat:
            return
        if msg.outgoing:
            return

        old = cache.get(msg.chat.id, msg.id)
        new_content = describe_message(msg)

        if old:
            old_content = old.content
            cached_for_media = old
        else:
            old_content = "[content not saved in cache]"
            cached_for_media = None

        chat_name = msg.chat.title or (msg.chat.first_name or "") or str(msg.chat.id)
        sender = (msg.from_user and (msg.from_user.first_name or msg.from_user.username)) or (
            msg.sender_chat and msg.sender_chat.title
        ) or "?"

        text = format_notification_edit(chat_name, sender, old_content, new_content)
        await _send(client, text, cached_for_media)
        cache.put(msg)

    async def on_deleted(client: Client, messages: list[Message]) -> None:
        for msg in messages:
            msg_id = msg.id

            if msg.chat:
                chat_id = msg.chat.id
                cached = cache.pop(chat_id, msg_id)
            else:
                cached_list = cache.find_and_pop_by_message_id(msg_id)
                cached = cached_list[0] if cached_list else None

            if cached:
                content = cached.content
                sender_name = cached.sender_name
                chat_name = cached.chat_name
                cached_for_media = cached
            else:
                content = "[содержимое не в кэше]"
                chat_name = msg.chat.title or str(msg.chat.id) if msg.chat else "?"
                sender_name = "?"
                if msg.from_user:
                    sender_name = msg.from_user.first_name or msg.from_user.username or "?"
                elif msg.sender_chat:
                    sender_name = msg.sender_chat.title or "?"
                cached_for_media = None

            text = format_notification_delete(chat_name, sender_name, content)
            await _send(client, text, cached_for_media)

            if not msg.chat and cached_list:
                for c in cached_list[1:]:
                    text = format_notification_delete(c.chat_name, c.sender_name, c.content)
                    await _send(client, text, c)

    return [
        MessageHandler(on_message),
        EditedMessageHandler(on_edited),
        DeletedMessagesHandler(on_deleted),
    ]
