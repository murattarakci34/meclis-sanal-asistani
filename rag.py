"""
Kaynak belgeler + gerekirse internet araması ile cevap üretir.
Veritabanı yok — belgeler bellekte.
"""

from __future__ import annotations

import math
import re
from typing import Any

from openai import OpenAI

import config
from document_loader import load_all_documents
from web_search import format_web_results, search_web


SYSTEM_PROMPT = """Sen yardımcı bir asistanısın. Türkçe, doğal ve net cevap ver.

Öncelik sırası:
1) "BELGE BİLGİSİ" bölümünde soruya uygun bilgi varsa onu kullan.
2) Belgede yoksa veya yetersizse "İNTERNET BİLGİSİ" bölümünü kullan.
3) İkisinde de yoksa kısaca "Bilmiyorum, bunu bulamadım." de. Uydurma.

Dosya adı, "kaynak", "belge parçası" gibi teknik ifadeler kullanma.
İnternetten cevap verirken abartılı kaynak listesi dökme; gerekirse kısaca belirt."""


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class SourceRAG:
    def __init__(self) -> None:
        if not config.OPENAI_API_KEY or not config.OPENAI_API_KEY.startswith("sk-"):
            raise ValueError(
                "OPENAI_API_KEY eksik. Yerelde .env dosyasına, Render'da Environment Variables'a ekle."
            )
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.chunks: list[dict[str, Any]] = []

    def reload(self) -> int:
        documents = load_all_documents()
        raw_chunks: list[dict[str, str]] = []
        for doc in documents:
            for piece in _chunk_text(doc["text"], config.CHUNK_SIZE, config.CHUNK_OVERLAP):
                raw_chunks.append({"source": doc["source"], "text": piece})

        self.chunks = []
        if not raw_chunks:
            return 0

        texts = [c["text"] for c in raw_chunks]
        embeddings = self._embed_batch(texts)
        for chunk, emb in zip(raw_chunks, embeddings):
            self.chunks.append(
                {"source": chunk["source"], "text": chunk["text"], "embedding": emb}
            )
        return len(self.chunks)

    def _embed_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        all_emb: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = self.client.embeddings.create(
                model=config.EMBEDDING_MODEL,
                input=batch,
            )
            ordered = sorted(resp.data, key=lambda d: d.index)
            all_emb.extend([d.embedding for d in ordered])
        return all_emb

    def retrieve(
        self, query: str, top_k: int | None = None
    ) -> list[tuple[float, dict[str, Any]]]:
        if not self.chunks:
            return []
        k = top_k or config.TOP_K
        q_emb = self._embed_batch([query])[0]
        scored = [(_cosine(q_emb, c["embedding"]), c) for c in self.chunks]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:k]

    def build_doc_context(self, retrieved: list[tuple[float, dict[str, Any]]]) -> str:
        parts = []
        for i, (_score, c) in enumerate(retrieved, 1):
            parts.append(f"[{i}]\n{c['text']}")
        return "\n\n---\n\n".join(parts)

    def chat(
        self,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[str, list[str]]:
        scored = self.retrieve(user_message)
        min_score = getattr(config, "MIN_DOC_SCORE", 0.28)
        relevant = [(s, c) for s, c in scored if s >= min_score]
        sources = sorted({c["source"] for _, c in relevant})

        doc_block = self.build_doc_context(relevant) if relevant else ""
        # Genel sorular için her zaman internet; belgede yoksa oradan cevaplar
        web_block = format_web_results(search_web(user_message, max_results=5))

        context_parts: list[str] = []
        if doc_block:
            context_parts.append(f"BELGE BİLGİSİ:\n{doc_block}")
        else:
            context_parts.append("BELGE BİLGİSİ: (bu soru için uygun belge parçası yok)")
        if web_block:
            context_parts.append(f"İNTERNET BİLGİSİ:\n{web_block}")
        else:
            context_parts.append(
                "İNTERNET BİLGİSİ: (arama sonucu yok)\n"
                "Genel bilginle yardımcı ol; emin değilsen bilmediğini söyle."
            )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": "\n\n".join(context_parts),
            },
        ]
        if history:
            messages.extend(history[-8:])
        messages.append({"role": "user", "content": user_message})

        resp = self.client.chat.completions.create(
            model=config.CHAT_MODEL,
            messages=messages,
            temperature=0.3,
        )
        answer = resp.choices[0].message.content or ""
        return answer, sources
