def _required_text(item: dict, key: str, error_code: str) -> str:
    value = str(item.get(key) or "").strip()
    if not value:
        raise ValueError(error_code)
    return value


def _optional_event_time(item: dict) -> str:
    for key in ("event_time", "timestamp", "ts", "publishedAt", "published_at", "createdAt", "created_at"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


class OnchainFeedAdapter:
    stale_after_seconds = 30 * 60

    def normalize(self, item: dict) -> dict:
        symbol = _required_text(item, "symbol", "onchain_symbol_required")
        wallet = _required_text(item, "wallet", "onchain_wallet_required")
        flow = _required_text(item, "flow", "onchain_flow_required").lower()
        event = {
            "event_type": "onchain",
            "symbol": symbol,
            "exchange": "external",
            "wallet": wallet,
            "flow": flow,
        }
        source = str(item.get("source") or "").strip()
        if source:
            event["source"] = source
        event_time = _optional_event_time(item)
        if event_time:
            event["event_time"] = event_time
        if "amountUsd" in item:
            event["amountUsd"] = item["amountUsd"]
        for key in ("asset", "impact", "route", "summary", "from_entity", "to_entity"):
            value = item.get(key)
            if value not in (None, ""):
                event[key] = value
        return event
