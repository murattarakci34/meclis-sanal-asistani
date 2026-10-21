"""
Belge / metin / görsel özetleme.
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

import config
from comparator import extract_text_from_upload


def _truncate(text: str, max_chars: int = 28000) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def summarize_text(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("Özetlenecek metin boş.")
    if not config.OPENAI_API_KEY or not config.OPENAI_API_KEY.startswith("sk-"):
        raise ValueError("OPENAI_API_KEY eksik.")

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    payload = _truncate(text)

    system = """Sen TBMM / kamu belgesi özet asistanısın.
Verilen metni Türkçe, net ve kısa özetle.
Uydurma; metinde olmayan bilgi ekleme.
SADECE geçerli JSON döndür:

{
  "kisa_ozet": "2-5 cumlelik ozet",
  "ana_noktalar": ["madde1", "madde2", "madde3"],
  "belge_turu": "kanun teklifi|tutanak|rapor|dilekce|diger",
  "kararlar_veya_sonuclar": ["varsa"],
  "uyarilar": ["opsiyonel"]
}

kisa_ozet zorunlu ve kisa olsun. ana_noktalar en fazla 8 madde.
kararlar_veya_sonuclar yoksa bos liste."""

    resp = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": payload},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "kisa_ozet": raw[:800],
            "ana_noktalar": [],
            "belge_turu": "diger",
            "kararlar_veya_sonuclar": [],
            "uyarilar": ["JSON parse uyarısı"],
        }

    return {
        "kisa_ozet": data.get("kisa_ozet") or "",
        "ana_noktalar": data.get("ana_noktalar") or [],
        "belge_turu": data.get("belge_turu") or "diger",
        "kararlar_veya_sonuclar": data.get("kararlar_veya_sonuclar") or [],
        "uyarilar": data.get("uyarilar") or [],
        "karakter": len(text),
        "disclaimer": (
            "Bu bir yardımcı özetdir; resmî belge yerine geçmez. "
            "Kritik kararlar için orijinal metni kontrol edin."
        ),
    }


def summarize_upload(
    filename: str | None,
    raw: bytes | None,
    pasted: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    text = (pasted or "").strip()

    if filename and raw is not None and filename.strip():
        t, w = extract_text_from_upload(filename, raw)
        warnings.extend(w)
        if t:
            text = t

    if not text:
        raise ValueError("Dosya yükleyin veya metin yapıştırın.")

    result = summarize_text(text)
    result["uyarilar"] = list(dict.fromkeys(warnings + (result.get("uyarilar") or [])))
    return result
