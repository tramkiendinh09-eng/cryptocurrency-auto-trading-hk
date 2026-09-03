from __future__ import annotations

import re


# 交易标的 → 新闻里可能出现的说法。
#
# 缺一条的代价不是"少一点新闻"，而是这个标的**永远拿不到新闻**：
# keywords_for_symbol 找不到映射时会退化成用标的名本身去搜，于是
# NVDAUSDT 就是去正文里找 "nvdausdt" 这个词 —— 没有任何一篇报道会
# 出现这个字符串。实测在补全之前，12 个在跑的标的里有 10 个新闻条目
# 恒为 0，其中包括全部 6 个半导体标的。
#
# 短票代（mu / wdc / sndk / sk）单独出现的歧义太大，一律只用公司名；
# 只有本身就足够独特的（nvda / xrp / bnb / doge）才保留代号写法。
DEFAULT_SYMBOL_KEYWORDS = {
    # 加密
    "BTCUSDT": ["btc", "bitcoin"],
    "ETHUSDT": ["eth", "ethereum"],
    "SOLUSDT": ["sol", "solana"],
    "XRPUSDT": ["xrp", "ripple"],
    "DOGEUSDT": ["doge", "dogecoin"],
    "BNBUSDT": ["bnb", "binance coin"],
    # "binance" 单独一个词会命中所有交易所新闻，不能用
    "SUIUSDT": ["sui network", "sui blockchain"],
    # 半导体 / 存储
    "NVDAUSDT": ["nvidia", "nvda"],
    "SAMSUNGUSDT": ["samsung"],
    "SKHYNIXUSDT": ["sk hynix", "hynix"],
    "MUUSDT": ["micron"],
    "WDCUSDT": ["western digital"],
    "SNDKUSDT": ["sandisk"],
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
