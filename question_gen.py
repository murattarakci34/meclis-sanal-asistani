"""
Belgeden komisyon / eğitim tarzı hazırlık soruları üretir.
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

import config
from comparator import extract_text_from_upload

MODES = {
    "komisyon": "Komisyon üyelerinin oturumda sorabileceği tarzda sorular",
    "hukuki": "Hukuki / teknik tutarlılık ve uygulama soruları",
    "politika": "Politika etkisi, kapsam ve toplumsal sonuç soruları",
    "egitim": "Yeni personel eğitimi için anlama / kontrol soruları",
    "basin": "Basın veya vatandaşın sorabileceği sade sorular",
}


def _truncate(text: str, max_chars: int = 28000) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def generate_questions(text: str, mode: str = "komisyon", count: int = 10) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("Soru üretmek için metin gerekli.")
    if not config.OPENAI_API_KEY or not config.OPENAI_API_KEY.startswith("sk-"):
        raise ValueError("OPENAI_API_KEY eksik.")

    mode = mode if mode in MODES else "komisyon"
    count = max(5, min(int(count or 10), 15))
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    system = f"""Sen TBMM hazırlık / eğitim asistanısın.
Verilen belgeye DAYALI sorular üret. Metinde olmayan konular uydurma.
Mod: {MODES[mode]}
Cevap yazma; sadece soru üret.
SADECE geçerli JSON:

{{
  "belge_turu": "kanun teklifi|tutanak|rapor|gerekce|diger",
  "mod": "{mode}",
  "sorular": [
    {{
      "soru": "...",
      "kategori": "kapsam|mali|hukuki|uygulama|risk|surec|diger",
      "neden_onemli": "1 cumle",
      "metinde_ipucu": "hangi bolume bakilmali"
    }}
  ],
  "uyarilar": []
}}

Tam {count} soru üret. Sorular birbirini tekrarlamasın.
Hazırlık / eğitim içindir; karar veya siyasi yönlendirme yapma."""

    resp = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": _truncate(text)},
        ],
        temperature=0.35,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "belge_turu": "diger",
            "mod": mode,
            "sorular": [],
            "uyarilar": ["JSON parse uyarısı"],
        }

    sorular = data.get("sorular") or []
    # normalize
    clean = []
    for s in sorular[:count]:
        if not isinstance(s, dict):
            continue
        q = str(s.get("soru") or "").strip()
        if not q:
            continue
        clean.append(
            {
                "soru": q,
                "kategori": str(s.get("kategori") or "diger"),
                "neden_onemli": str(s.get("neden_onemli") or ""),
                "metinde_ipucu": str(s.get("metinde_ipucu") or ""),
            }
        )

    return {
        "belge_turu": data.get("belge_turu") or "diger",
        "mod": mode,
        "mod_aciklama": MODES[mode],
        "sorular": clean,
        "uyarilar": data.get("uyarilar") or [],
        "karakter": len(text),
        "disclaimer": (
            "Bu sorular eğitim ve hazırlık amaçlıdır; resmî gündem veya karar değildir. "
            "Metinde olmayan konulara dayanmamalıdır — çıktıyı belgeyle doğrulayın."
        ),
    }


def generate_from_upload(
    filename: str | None,
    raw: bytes | None,
    pasted: str,
    mode: str = "komisyon",
    count: int = 10,
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

    result = generate_questions(text, mode=mode, count=count)
    result["uyarilar"] = list(dict.fromkeys(warnings + (result.get("uyarilar") or [])))
    return result
