"""
Meclis Sanal Asistanı — cPanel / Flask sürümü.
Yerelde:  python webapp.py
cPanel:   passenger_wsgi.py üzerinden çalışır.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import chat_store
import config
from document_loader import kaynak_fingerprint
from rag import SourceRAG

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

_rag: SourceRAG | None = None
_kaynak_fp: str = ""
_rag_error: str | None = None


def get_rag() -> SourceRAG:
    global _rag, _kaynak_fp, _rag_error
    fp = kaynak_fingerprint()
    if _rag is None or fp != _kaynak_fp:
        try:
            _rag = SourceRAG()
            _rag.reload()
            _kaynak_fp = fp
            _rag_error = None
        except Exception as exc:  # noqa: BLE001
            _rag_error = str(exc)
            raise
    return _rag


@app.get("/")
def index():
    return render_template(
        "index.html",
        app_name=getattr(config, "APP_NAME", "Meclis Sanal Asistanı"),
    )


@app.get("/api/health")
def health():
    try:
        get_rag()
        ok = True
        err = None
    except Exception as exc:  # noqa: BLE001
        ok = False
        err = str(exc)
    return jsonify({"ok": ok, "error": err})


@app.get("/api/chats")
def list_chats():
    q = request.args.get("q", "")
    chats = [
        c
        for c in chat_store.search_chats(q)
        if c.get("message_count", 0) > 0
    ]
    return jsonify({"chats": chats})


@app.get("/api/chats/<chat_id>")
def get_chat(chat_id: str):
    chat = chat_store.load_chat(chat_id)
    if not chat:
        return jsonify({"error": "not_found"}), 404
    return jsonify(chat)


@app.post("/api/chats")
def new_chat():
    chat = chat_store.create_chat("Yeni sohbet")
    return jsonify(chat)


@app.delete("/api/chats/<chat_id>")
def delete_chat(chat_id: str):
    chat_store.delete_chat(chat_id)
    return jsonify({"ok": True})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    chat_id = data.get("chat_id")

    if not message:
        return jsonify({"error": "empty"}), 400

    if chat_id:
        chat_obj = chat_store.load_chat(chat_id)
        if not chat_obj:
            chat_obj = chat_store.create_chat()
            chat_id = chat_obj["id"]
    else:
        chat_obj = chat_store.create_chat()
        chat_id = chat_obj["id"]

    messages = chat_obj.get("messages") or []
    if not messages:
        chat_obj["title"] = chat_store.title_from_message(message)

    messages.append({"role": "user", "content": message})
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in messages[:-1]
        if m["role"] in ("user", "assistant")
    ]

    try:
        rag = get_rag()
        answer, _ = rag.chat(message, history=history)
    except Exception as exc:  # noqa: BLE001
        answer = f"Hata: {exc}"

    messages.append({"role": "assistant", "content": answer})
    chat_obj["messages"] = messages
    chat_store.save_chat(chat_obj)

    return jsonify(
        {
            "chat_id": chat_id,
            "title": chat_obj.get("title") or "Yeni sohbet",
            "answer": answer,
            "messages": messages,
        }
    )


if __name__ == "__main__":
    # Yerel test
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
