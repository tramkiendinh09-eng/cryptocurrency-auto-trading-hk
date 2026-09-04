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


# 板块级新闻：不点名任何公司，却对整个板块重大。
#
# 「US announces new chip export controls」对 6 个半导体标的全都是重大消息，
# 但一个公司名都不提，于是被 matches_symbol 整条过滤掉。实测一条芯片政策
# 查询返回 32 条，只有 4 条（12%）能命中公司名；补上板块短语后升到 15 条（47%）。
#
# 短语必须足够具体。单个 "chip" 会命中薯片、赌场筹码和一切科技报道，
# 加进来等于把这道过滤取消掉——这和 _EVENT_KEYWORDS 里不收 chip/memory
# 泛称是同一条理由。
DEFAULT_SECTOR_KEYWORDS = {
    "semiconductor": [
        "chip tariff", "semiconductor tariff",
        "chip export", "semiconductor export", "export control",
        "chip ban", "chip sanction", "semiconductor sanction",
        "chips act", "chip subsidy",
        "memory chip", "chipmaker", "semiconductor industry",
        "chip supply", "semiconductor supply", "ai chip",
    ],
}

# 标的属于哪个板块。加密标的不归任何板块：加密新闻本来就会点名币种，
# 而「监管」「ETF」这类泛词跨币种通用，按板块广播只会制造噪声。
SYMBOL_SECTORS = {
    "NVDAUSDT": "semiconductor",
    "MUUSDT": "semiconductor",
    "SKHYNIXUSDT": "semiconductor",
    "SAMSUNGUSDT": "semiconductor",
    "WDCUSDT": "semiconductor",
    "SNDKUSDT": "semiconductor",
}


def sector_keywords_for_symbol(symbol: str) -> list[str]:
    sector = SYMBOL_SECTORS.get(str(symbol or "").strip().upper())
    return list(DEFAULT_SECTOR_KEYWORDS.get(sector, [])) if sector else []


def keywords_for_symbol(symbol: str) -> list[str]:
    normalized = str(symbol or "").strip().upper()
    return list(DEFAULT_SYMBOL_KEYWORDS.get(normalized, [normalized.lower()]))


def _contains_keyword(haystack: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        escaped = re.escape(keyword)
        if re.search(rf"\b(?:no|not|without)\s+{escaped}\b", haystack):
            continue
        if re.search(rf"\b{escaped}\b", haystack):
            return True
    return False


def matches_symbol(symbol: str, *parts: str) -> bool:
    """这篇报道和这个标的有关吗。

    两条路：点名了这家公司，或者命中了这个标的所属板块的政策级短语。
    后者是为「不点名任何公司却对整个板块重大」的新闻准备的——芯片关税、
    出口管制这类消息正是驱动半导体标的的第一变量，却从不提公司名。
    """
    haystack = " ".join(str(part or "") for part in parts).strip().lower()
    if not haystack:
        return False
    if _contains_keyword(haystack, keywords_for_symbol(symbol)):
        return True
    return _contains_keyword(haystack, sector_keywords_for_symbol(symbol))
