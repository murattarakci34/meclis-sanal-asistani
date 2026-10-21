"""
Sohbet geçmişini yerel JSON dosyalarında tutar (veritabanı yok).
Her kullanıcı (cihaz) kendi klasöründe tutulur: sohbetler/<owner_id>/
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHATS_DIR = Path("sohbetler")
_OWNER_RE = re.compile(r"[^a-zA-Z0-9_-]")


def normalize_owner(owner_id: str | None) -> str:
    raw = (owner_id or "").strip()
    safe = _OWNER_RE.sub("", raw)[:64]
    return safe or "anon"


def _user_dir(owner_id: str | None) -> Path:
    return CHATS_DIR / normalize_owner(owner_id)


def _ensure_dir(owner_id: str | None = None) -> Path:
    folder = _user_dir(owner_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(owner_id: str | None, chat_id: str) -> Path:
    # chat_id içinde path traversal olmasın
    cid = _OWNER_RE.sub("", (chat_id or "").strip())[:32]
    return _ensure_dir(owner_id) / f"{cid}.json"


def new_chat_id() -> str:
    return uuid.uuid4().hex[:12]


def create_chat(title: str = "Yeni sohbet", owner_id: str | None = None) -> dict[str, Any]:
    owner = normalize_owner(owner_id)
    chat = {
        "id": new_chat_id(),
        "owner_id": owner,
        "title": title,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "messages": [],
    }
    save_chat(chat, owner_id=owner)
    return chat


def save_chat(chat: dict[str, Any], owner_id: str | None = None) -> None:
    owner = normalize_owner(owner_id or chat.get("owner_id"))
    chat["owner_id"] = owner
    chat["updated_at"] = _now_iso()
    _path(owner, chat["id"]).write_text(
        json.dumps(chat, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_chat(chat_id: str, owner_id: str | None = None) -> dict[str, Any] | None:
    owner = normalize_owner(owner_id)
    path = _path(owner, chat_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    # Klasör zaten kullanıcıya özel; ek güvenlik
    stored = data.get("owner_id")
    if stored and normalize_owner(stored) != owner:
        return None
    return data


def delete_chat(chat_id: str, owner_id: str | None = None) -> None:
    path = _path(owner_id, chat_id)
    if path.exists():
        path.unlink()


def list_chats(owner_id: str | None = None) -> list[dict[str, Any]]:
    """Özet liste: id, title, updated_at, preview — en yeni önce."""
    folder = _ensure_dir(owner_id)
    items: list[dict[str, Any]] = []
    for path in folder.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        msgs = data.get("messages") or []
        preview = ""
        for m in msgs:
            if m.get("role") == "user" and m.get("content"):
                preview = str(m["content"])[:80]
                break
        items.append(
            {
                "id": data.get("id", path.stem),
                "title": data.get("title") or "Yeni sohbet",
                "updated_at": data.get("updated_at") or "",
                "preview": preview,
                "message_count": len(msgs),
            }
        )
    items.sort(key=lambda x: x["updated_at"], reverse=True)
    return items


def search_chats(query: str, owner_id: str | None = None) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    chats = list_chats(owner_id=owner_id)
    if not q:
        return chats
    matched: list[dict[str, Any]] = []
    for summary in chats:
        hay = f"{summary['title']} {summary.get('preview', '')}".lower()
        full = load_chat(summary["id"], owner_id=owner_id)
        if full:
            for m in full.get("messages") or []:
                hay += " " + str(m.get("content", "")).lower()
        if q in hay:
            matched.append(summary)
    return matched


def title_from_message(text: str, max_len: int = 42) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return "Yeni sohbet"
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"
