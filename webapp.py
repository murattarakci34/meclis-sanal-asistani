"""
Meclis Sanal Asistanı — cPanel / Flask / Render sürümü.
Yerelde:  python webapp.py
"""

from __future__ import annotations

import os
import re
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
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB

_rag: SourceRAG | None = None
_kaynak_fp: str = ""
_rag_error: str | None = None

_CLIENT_RE = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")


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


def client_id_from_request() -> str | None:
    cid = (request.headers.get("X-Client-Id") or "").strip()
    if not cid and request.is_json:
        data = request.get_json(silent=True) or {}
        cid = str(data.get("client_id") or "").strip()
    if not cid:
        cid = (request.args.get("client_id") or "").strip()
    if not _CLIENT_RE.match(cid):
        return None
    return cid


def require_client() -> tuple[str | None, tuple | None]:
    cid = client_id_from_request()
    if not cid:
        return None, (jsonify({"error": "client_id_required"}), 400)
    return cid, None


@app.get("/")
def index():
    return render_template(
        "index.html",
        app_name=getattr(config, "APP_NAME", "Meclis Sanal Asistanı"),
    )


@app.get("/karsilastirma")
def karsilastirma_page():
    return render_template(
        "karsilastirma.html",
        app_name=getattr(config, "APP_NAME", "Meclis Sanal Asistanı"),
    )


@app.post("/api/compare")
def api_compare():
    """Eski düzenleme vs yeni teklif karşılaştırma."""
    import comparator

    warnings: list[str] = []
    old_text = (request.form.get("old_text") or "").strip()
    new_text = (request.form.get("new_text") or "").strip()

    old_f = request.files.get("old_file")
    new_f = request.files.get("new_file")

    try:
        if old_f and old_f.filename:
            t, w = comparator.extract_text_from_upload(
                old_f.filename, old_f.read()
            )
            warnings.extend(w)
            if t:
                old_text = t
        if new_f and new_f.filename:
            t, w = comparator.extract_text_from_upload(
                new_f.filename, new_f.read()
            )
            warnings.extend(w)
            if t:
                new_text = t

        if not old_text or not new_text:
            return (
                jsonify(
                    {
                        "error": "Eski ve yeni metin gerekli (dosya yükleyin veya yapıştırın)."
                    }
                ),
                400,
            )

        result = comparator.compare_texts(old_text, new_text)
        # Dosya uyarılarını öne ekle
        result["uyarilar"] = list(dict.fromkeys(warnings + (result.get("uyarilar") or [])))
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Karşılaştırma hatası: {exc}"}), 500


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
    owner, err = require_client()
    if err:
        return err
    q = request.args.get("q", "")
    chats = [
        c
        for c in chat_store.search_chats(q, owner_id=owner)
        if c.get("message_count", 0) > 0
    ]
    return jsonify({"chats": chats})


@app.get("/api/chats/<chat_id>")
def get_chat(chat_id: str):
    owner, err = require_client()
    if err:
        return err
    chat = chat_store.load_chat(chat_id, owner_id=owner)
    if not chat:
        return jsonify({"error": "not_found"}), 404
    return jsonify(chat)


@app.post("/api/chats")
def new_chat():
    owner, err = require_client()
    if err:
        return err
    chat = chat_store.create_chat("Yeni sohbet", owner_id=owner)
    return jsonify(chat)


@app.delete("/api/chats/<chat_id>")
def delete_chat(chat_id: str):
    owner, err = require_client()
    if err:
        return err
    chat_store.delete_chat(chat_id, owner_id=owner)
    return jsonify({"ok": True})


@app.post("/api/chat")
def chat():
    owner, err = require_client()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    chat_id = data.get("chat_id")

    if not message:
        return jsonify({"error": "empty"}), 400

    if chat_id:
        chat_obj = chat_store.load_chat(str(chat_id), owner_id=owner)
        if not chat_obj:
            chat_obj = chat_store.create_chat(owner_id=owner)
            chat_id = chat_obj["id"]
    else:
        chat_obj = chat_store.create_chat(owner_id=owner)
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
    chat_store.save_chat(chat_obj, owner_id=owner)

    return jsonify(
        {
            "chat_id": chat_id,
            "title": chat_obj.get("title") or "Yeni sohbet",
            "answer": answer,
            "messages": messages,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
