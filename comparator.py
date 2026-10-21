"""
Eski düzenleme vs yeni teklif karşılaştırma motoru.
- Madde bölme + hizalama
- Klasik kelime diff (HTML)
- LLM ile anlamsal özet / tablo / etki notları / uyarılar
"""

from __future__ import annotations

import difflib
import io
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from openai import OpenAI

import config
from document_loader import load_file

_ARTICLE_SPLIT = re.compile(
    r"(?=(?:^|\n)\s*(?:MADDE|Madde|Geçici Madde|GEÇİCİ MADDE|Ek Madde|EK MADDE)\s+\d+)",
    re.MULTILINE,
)
_ARTICLE_TITLE = re.compile(
    r"^\s*((?:GEÇİCİ\s+)?(?:EK\s+)?MADDE|Madde|Geçici Madde|Ek Madde)\s+(\d+[A-Za-z]?)",
    re.IGNORECASE,
)


def extract_text_from_upload(filename: str, raw: bytes) -> tuple[str, list[str]]:
    """Yüklenen dosyadan metin çıkar. (text, warnings)"""
    warnings: list[str] = []
    name = (filename or "dosya.txt").strip() or "dosya.txt"
    suffix = Path(name).suffix.lower() or ".txt"
    if suffix not in {".pdf", ".docx", ".txt", ".md"}:
        warnings.append(f"Desteklenmeyen uzantı ({suffix}); düz metin olarak okunmaya çalışıldı.")
        suffix = ".txt"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)

    try:
        text = load_file(tmp_path) or ""
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass

    text = (text or "").strip()
    if not text:
        warnings.append(f"{name}: metin çıkarılamadı (tarama PDF / boş dosya olabilir).")
    elif len(text) < 80:
        warnings.append(f"{name}: çok kısa metin — OCR veya kopyala-yapıştır gerekebilir.")
    # Bozuk karakter oranı kaba kontrol
    weird = sum(1 for c in text[:2000] if ord(c) < 9)
    if weird > 20:
        warnings.append(f"{name}: metin kalitesi düşük görünebilir.")
    return text, warnings


def split_articles(text: str) -> list[dict[str, str]]:
    """Metni madde bloklarına böler."""
    text = (text or "").strip()
    if not text:
        return []

    parts = _ARTICLE_SPLIT.split(text)
    articles: list[dict[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = _ARTICLE_TITLE.match(part)
        if m:
            label = f"{m.group(1).title()} {m.group(2)}"
            # normalize Madde
            label = re.sub(r"(?i)geçici\s+madde", "Geçici Madde", label)
            label = re.sub(r"(?i)^madde", "Madde", label)
            label = re.sub(r"(?i)^ek\s+madde", "Ek Madde", label)
        else:
            label = f"Bölüm {len(articles) + 1}"
        articles.append({"id": label, "text": part})

    # Madde bulunamadıysa paragraf / uzun blok
    if len(articles) <= 1 and len(text) > 500:
        chunks = re.split(r"\n{2,}", text)
        articles = []
        for i, ch in enumerate(chunks, 1):
            ch = ch.strip()
            if len(ch) < 40:
                continue
            articles.append({"id": f"Paragraf {i}", "text": ch})
    return articles or [{"id": "Tam metin", "text": text}]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def align_articles(
    old_arts: list[dict[str, str]], new_arts: list[dict[str, str]]
) -> list[dict[str, Any]]:
    """Eski-yeni maddeleri id ve benzerlik ile hizalar."""
    used_new: set[int] = set()
    pairs: list[dict[str, Any]] = []

    def best_new(old: dict[str, str]) -> tuple[int | None, float]:
        best_i, best_s = None, 0.0
        for i, nw in enumerate(new_arts):
            if i in used_new:
                continue
            # Aynı madde no
            score = 0.0
            if _norm(old["id"]) == _norm(nw["id"]):
                score = 1.0
            else:
                score = difflib.SequenceMatcher(
                    None, _norm(old["text"])[:800], _norm(nw["text"])[:800]
                ).ratio()
            if score > best_s:
                best_s, best_i = score, i
        return best_i, best_s

    for old in old_arts:
        idx, score = best_new(old)
        if idx is not None and score >= 0.35:
            used_new.add(idx)
            pairs.append(
                {
                    "topic": old["id"],
                    "old_text": old["text"],
                    "new_text": new_arts[idx]["text"],
                    "new_id": new_arts[idx]["id"],
                    "align_score": round(score, 3),
                    "change_type": "degisti" if score < 0.98 else "degismedi",
                }
            )
        else:
            pairs.append(
                {
                    "topic": old["id"],
                    "old_text": old["text"],
                    "new_text": "",
                    "new_id": "",
                    "align_score": 0.0,
                    "change_type": "kaldirildi",
                }
            )

    for i, nw in enumerate(new_arts):
        if i in used_new:
            continue
        pairs.append(
            {
                "topic": nw["id"],
                "old_text": "",
                "new_text": nw["text"],
                "new_id": nw["id"],
                "align_score": 0.0,
                "change_type": "eklendi",
            }
        )
    return pairs


def html_word_diff(old: str, new: str) -> str:
    """Kelime bazlı kırmızı/yeşil diff HTML."""
    old_w = (old or "").split()
    new_w = (new or "").split()
    sm = difflib.SequenceMatcher(None, old_w, new_w)
    parts: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            parts.append(" ".join(old_w[i1:i2]))
        elif tag == "delete":
            parts.append(
                '<span class="diff-del">' + " ".join(old_w[i1:i2]) + "</span>"
            )
        elif tag == "insert":
            parts.append(
                '<span class="diff-ins">' + " ".join(new_w[j1:j2]) + "</span>"
            )
        elif tag == "replace":
            if i1 != i2:
                parts.append(
                    '<span class="diff-del">' + " ".join(old_w[i1:i2]) + "</span>"
                )
            if j1 != j2:
                parts.append(
                    '<span class="diff-ins">' + " ".join(new_w[j1:j2]) + "</span>"
                )
    return " ".join(p for p in parts if p)


def _truncate(s: str, n: int = 2500) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - 1] + "…"


def llm_analyze(pairs: list[dict[str, Any]], old_full: str, new_full: str) -> dict[str, Any]:
    """Structured JSON analiz."""
    if not config.OPENAI_API_KEY or not config.OPENAI_API_KEY.startswith("sk-"):
        raise ValueError("OPENAI_API_KEY eksik.")

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    # LLM'e özet girdi (çok uzun olmasın)
    compact = []
    for p in pairs[:40]:
        compact.append(
            {
                "baslik": p["topic"],
                "tip_oneri": p["change_type"],
                "hizalama": p["align_score"],
                "eski": _truncate(p["old_text"], 1200),
                "yeni": _truncate(p["new_text"], 1200),
            }
        )

    system = """Sen TBMM yasama belgesi karşılaştırma asistanısın.
Verilen eski düzenleme ve yeni teklif parçalarını analiz et.
Kesin hukuki mütalaa verme; değişiklikleri işaretle.
SADECE geçerli JSON döndür (markdown yok).

Şema:
{
  "ozet": ["madde1", "madde2"],
  "tablo": [
    {"konu": "...", "eski": "...", "yeni": "...", "degisim_tipi": "degisti|eklendi|kaldirildi|degismedi"}
  ],
  "etki_notlari": ["..."],
  "uyarilar": ["..."],
  "guven": "yuksek|orta|dusuk"
}
degisim_tipi değerleri Türkçe anahtarlar: degisti, eklendi, kaldirildi, degismedi.
ozet en fazla 8 madde. tablo en fazla 25 satır. etki_notlari kısa olsun."""

    user = json.dumps(
        {
            "eslesmis_parcalar": compact,
            "eski_baslangic": _truncate(old_full, 1500),
            "yeni_baslangic": _truncate(new_full, 1500),
        },
        ensure_ascii=False,
    )

    resp = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "ozet": ["LLM çıktısı çözümlenemedi."],
            "tablo": [],
            "etki_notlari": [],
            "uyarilar": ["JSON parse hatası"],
            "guven": "dusuk",
        }
    return data


def compare_texts(old_text: str, new_text: str) -> dict[str, Any]:
    warnings: list[str] = []
    old_text = (old_text or "").strip()
    new_text = (new_text or "").strip()
    if not old_text or not new_text:
        raise ValueError("Eski ve yeni metinlerin ikisi de gerekli.")

    old_arts = split_articles(old_text)
    new_arts = split_articles(new_text)
    if len(old_arts) == 1 and old_arts[0]["id"] == "Tam metin":
        warnings.append("Eski metinde net madde başlığı bulunamadı; paragraf bazlı karşılaştırıldı.")
    if len(new_arts) == 1 and new_arts[0]["id"] == "Tam metin":
        warnings.append("Yeni metinde net madde başlığı bulunamadı; paragraf bazlı karşılaştırıldı.")

    pairs = align_articles(old_arts, new_arts)
    low_align = [p for p in pairs if 0 < p["align_score"] < 0.5 and p["change_type"] == "degisti"]
    if low_align:
        warnings.append(
            f"{len(low_align)} parça düşük hizalama skoruyla eşleşti; elle kontrol edin."
        )

    # Diff panelleri (değişen / eklenen / silinen)
    diffs = []
    for p in pairs:
        if p["change_type"] == "degismedi":
            continue
        diffs.append(
            {
                "topic": p["topic"],
                "change_type": p["change_type"],
                "align_score": p["align_score"],
                "html": html_word_diff(p["old_text"], p["new_text"]),
                "old_preview": _truncate(p["old_text"], 400),
                "new_preview": _truncate(p["new_text"], 400),
            }
        )

    analysis = llm_analyze(pairs, old_text, new_text)
    # Uyarıları birleştir
    all_warn = list(warnings) + list(analysis.get("uyarilar") or [])
    # Tekrarları temizle
    seen = set()
    uniq_warn = []
    for w in all_warn:
        if w and w not in seen:
            seen.add(w)
            uniq_warn.append(w)

    # Tablo boşsa pairs'ten üret
    tablo = analysis.get("tablo") or []
    if not tablo:
        tip_map = {
            "degisti": "degisti",
            "eklendi": "eklendi",
            "kaldirildi": "kaldirildi",
            "degismedi": "degismedi",
        }
        for p in pairs:
            if p["change_type"] == "degismedi":
                continue
            tablo.append(
                {
                    "konu": p["topic"],
                    "eski": _truncate(p["old_text"], 180),
                    "yeni": _truncate(p["new_text"], 180),
                    "degisim_tipi": tip_map.get(p["change_type"], p["change_type"]),
                }
            )

    return {
        "ozet": analysis.get("ozet") or [],
        "tablo": tablo,
        "etki_notlari": analysis.get("etki_notlari") or [],
        "uyarilar": uniq_warn,
        "guven": analysis.get("guven") or "orta",
        "diffs": diffs[:30],
        "istatistik": {
            "eski_parca": len(old_arts),
            "yeni_parca": len(new_arts),
            "eslesen": len([p for p in pairs if p["change_type"] in ("degisti", "degismedi")]),
            "eklenen": len([p for p in pairs if p["change_type"] == "eklendi"]),
            "kaldirilan": len([p for p in pairs if p["change_type"] == "kaldirildi"]),
            "degisen": len([p for p in pairs if p["change_type"] == "degisti"]),
        },
        "disclaimer": (
            "Bu araç yardımcı analiz üretir; resmî hukuki mütalaa veya kesin yorum değildir. "
            "Sonuçları yetkili personel doğrulamalıdır."
        ),
    }
