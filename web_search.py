"""
Basit internet araması (DuckDuckGo) — ekstra API key gerekmez.
"""

from __future__ import annotations


def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """
    [{title, href, body}, ...] döner. Hata olursa boş liste.
    """
    q = (query or "").strip()
    if not q:
        return []
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # eski paket adı
        except ImportError:
            print("[uyarı] ddgs/duckduckgo-search yüklü değil.")
            return []

    results: list[dict[str, str]] = []
    try:
        with DDGS() as ddgs:
            for item in ddgs.text(q, region="tr-tr", max_results=max_results):
                results.append(
                    {
                        "title": str(item.get("title") or ""),
                        "href": str(item.get("href") or ""),
                        "body": str(item.get("body") or ""),
                    }
                )
    except Exception as exc:  # noqa: BLE001
        print(f"[uyarı] web araması başarısız: {exc}")
    return results


def format_web_results(results: list[dict[str, str]]) -> str:
    if not results:
        return ""
    parts: list[str] = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[{i}] {r['title']}\n{r['body']}\nURL: {r['href']}"
        )
    return "\n\n".join(parts)
