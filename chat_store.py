"""
Sohbet geçmişini yerel JSON dosyalarında tutar (veritabanı yok).
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHATS_DIR = Path("sohbetler")


def _ensure_dir() -> None:
    CHATS_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(chat_id: str) -> Path:
    return CHATS_DIR / f"{chat_id}.json"


def new_chat_id() -> str:
    return uuid.uuid4().hex[:12]


def create_chat(title: str = "Yeni sohbet") -> dict[str, Any]:
    _ensure_dir()
    chat = {
        "id": new_chat_id(),
        "title": title,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "messages": [],
    }
    save_chat(chat)
    return chat


def save_chat(chat: dict[str, Any]) -> None:
    _ensure_dir()
    chat["updated_at"] = _now_iso()
    _path(chat["id"]).write_text(
        json.dumps(chat, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_chat(chat_id: str) -> dict[str, Any] | None:
    path = _path(chat_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def delete_chat(chat_id: str) -> None:
    path = _path(chat_id)
    if path.exists():
        path.unlink()


def list_chats() -> list[dict[str, Any]]:
    """Özet liste: id, title, updated_at, preview — en yeni önce."""
    _ensure_dir()
    items: list[dict[str, Any]] = []
    for path in CHATS_DIR.glob("*.json"):
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


def search_chats(query: str) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    chats = list_chats()
    if not q:
        return chats
    matched: list[dict[str, Any]] = []
    for summary in chats:
        hay = f"{summary['title']} {summary.get('preview', '')}".lower()
        full = load_chat(summary["id"])
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
