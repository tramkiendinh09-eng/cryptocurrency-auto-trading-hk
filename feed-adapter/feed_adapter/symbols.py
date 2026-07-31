from __future__ import annotations

import re


DEFAULT_SYMBOL_KEYWORDS = {
    "BTCUSDT": ["btc", "bitcoin"],
    "ETHUSDT": ["eth", "ethereum"],
    "SOLUSDT": ["sol", "solana"],
}


def keywords_for_symbol(symbol: str) -> list[str]:
    normalized = str(symbol or "").strip().upper()
    return list(DEFAULT_SYMBOL_KEYWORDS.get(normalized, [normalized.lower()]))


def matches_symbol(symbol: str, *parts: str) -> bool:
    haystack = " ".join(str(part or "") for part in parts).strip().lower()
    if not haystack:
        return False
    for keyword in keywords_for_symbol(symbol):
        escaped = re.escape(keyword)
        if re.search(rf"\b(?:no|not|without)\s+{escaped}\b", haystack):
            continue
        if re.search(rf"\b{escaped}\b", haystack):
            return True
    return False
