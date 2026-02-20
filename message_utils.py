from dataclasses import dataclass, field
from typing import Any, Optional

from pyrogram.types import Message


def _get_sender_name(msg: Message) -> str:
    """Name sander."""
    if msg.from_user:
        name = msg.from_user.first_name or ""
        if msg.from_user.last_name:
            name += f" {msg.from_user.last_name}"
        return name or msg.from_user.username or str(msg.from_user.id)
    if msg.sender_chat:
        return msg.sender_chat.title or "Channel"
    return "Unknown"


def _get_chat_name(msg: Message) -> str:
    """Name of chats."""
    if msg.chat.title:
        return msg.chat.title
    if msg.chat.first_name:
        name = msg.chat.first_name
        if msg.chat.last_name:
            name += f" {msg.chat.last_name}"
        return name
    return str(msg.chat.id)


def describe_message(msg: Message) -> str:
    """Short description of messages for all tips"""
    parts: list[str] = []

    if msg.text:
        text = msg.text
        if len(text) > 500:
            text = text[:500] + "..."
        parts.append(text.replace("\n", " "))

    if msg.caption:
        cap = msg.caption
        if len(cap) > 300:
            cap = cap[:300] + "..."
        parts.append(f"[подпись: {cap}]")

    if msg.photo:
        parts.append("[📷 Фото]")
    if msg.video:
        parts.append("[🎬 Видео]")
    if msg.video_note:
        parts.append("[📹 Видеосообщение]")
    if msg.voice:
        parts.append("[🎤 Голосовое]")
    if msg.audio:
        title = getattr(msg.audio, "title", None) or "Аудио"
        parts.append(f"[🎵 {title}]")
    if msg.document:
        name = getattr(msg.document, "file_name", None) or "Документ"
        parts.append(f"[📎 {name}]")
    if msg.sticker:
        emoji = getattr(msg.sticker, "emoji", None) or ""
        parts.append(f"[Стикер {emoji}]")
    if msg.animation:
        parts.append("[GIF]")
    if msg.poll:
        parts.append(f"[Опрос: {msg.poll.question}]")
    if msg.contact:
        parts.append(f"[Контак: {msg.contact.first_name}]")
    if msg.location:
        parts.append("[📍 Геолокация]")
    if msg.venue:
        parts.append(f"[📍 Место: {msg.venue.title}]")
    if msg.dice:
        parts.append(f"[Кости: {msg.dice.emoji}]")

    if not parts:
        return "[пустое сообщение]"
    return " | ".join(parts)


def _get_media_file_id(msg: Message) -> tuple[str | None, str]:
    """
    Возвращает (file_id, media_type) для медиа-сообщений.
    media_type: photo, video, document, voice, video_note, audio, sticker, animation
    """
    if msg.photo:
        return (msg.photo.file_id, "photo")
    if msg.video:
        return (msg.video.file_id, "video")
    if msg.document:
        return (msg.document.file_id, "document")
    if msg.voice:
        return (msg.voice.file_id, "voice")
    if msg.video_note:
        return (msg.video_note.file_id, "video_note")
    if msg.audio:
        return (msg.audio.file_id, "audio")
    if msg.sticker:
        return (msg.sticker.file_id, "sticker")
    if msg.animation:
        return (msg.animation.file_id, "animation")
    return (None, "")


@dataclass
class CachedMessage:
    """Cashed message for search when we deleted/edit"""
    message_id: int
    chat_id: int
    sender_name: str
    chat_name: str
    content: str
    date: Any  # datetime
    media_file_id: str | None = None
    media_type: str = ""

    @classmethod
    def from_message(cls, msg: Message) -> "CachedMessage":
        file_id, media_type = _get_media_file_id(msg)
        return cls(
            message_id=msg.id,
            chat_id=msg.chat.id,
            sender_name=_get_sender_name(msg),
            chat_name=_get_chat_name(msg),
            content=describe_message(msg),
            date=msg.date,
            media_file_id=file_id,
            media_type=media_type,
        )


class MessageCache:
    """Cache messages for restore when we deleted/edit"""

    def __init__(self, max_per_chat: int = 1000):
        # (chat_id, message_id) -> CachedMessage
        self._cache: dict[tuple[int, int], CachedMessage] = {}
        self._order: list[tuple[int, int]] = []
        self._max_per_chat: dict[int, int] = {}
        self.max_per_chat = max_per_chat

    def _key(self, chat_id: int, message_id: int) -> tuple[int, int]:
        return (chat_id, message_id)

    def put(self, msg: Message) -> None:
        key = self._key(msg.chat.id, msg.id)
        self._cache[key] = CachedMessage.from_message(msg)
        self._order.append(key)
        self._max_per_chat[msg.chat.id] = self._max_per_chat.get(msg.chat.id, 0) + 1

        # Limit on chat: deleted old
        while self._max_per_chat.get(msg.chat.id, 0) > self.max_per_chat and self._order:
            old_key = self._order.pop(0)
            if old_key in self._cache:
                del self._cache[old_key]
                cid = old_key[0]
                self._max_per_chat[cid] = max(0, self._max_per_chat.get(cid, 1) - 1)

    def get(self, chat_id: int, message_id: int) -> Optional[CachedMessage]:
        return self._cache.get(self._key(chat_id, message_id))

    def pop(self, chat_id: int, message_id: int) -> Optional[CachedMessage]:
        key = self._key(chat_id, message_id)
        val = self._cache.pop(key, None)
        if val and key in self._order:
            try:
                self._order.remove(key)
            except ValueError:
                pass
        return val

    def get_many(self, chat_id: int, message_ids: list[int]) -> list[CachedMessage]:
        result = []
        for mid in message_ids:
            m = self.get(chat_id, mid)
            if m:
                result.append(m)
        return result

    def find_and_pop_by_message_id(self, message_id: int) -> list[CachedMessage]:
        """
        Находит и удаляет из кэша сообщения с данным message_id (по всем чатам).
        Нужно для UpdateDeleteMessages, где Telegram не передаёт chat_id.
        """
        found = []
        keys_to_remove = []
        for (cid, mid), cached in self._cache.items():
            if mid == message_id:
                found.append(cached)
                keys_to_remove.append((cid, mid))
        for key in keys_to_remove:
            self._cache.pop(key, None)
            if key in self._order:
                try:
                    self._order.remove(key)
                except ValueError:
                    pass
            cid = key[0]
            self._max_per_chat[cid] = max(0, self._max_per_chat.get(cid, 1) - 1)
        return found
