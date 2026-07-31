def _required_text(item: dict, key: str, error_code: str) -> str:
    value = str(item.get(key) or "").strip()
    if not value:
        raise ValueError(error_code)
    return value


def _optional_event_time(item: dict) -> str:
    for key in ("event_time", "publishedAt", "published_at", "timestamp", "ts", "createdAt", "created_at"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


class NewsFeedAdapter:
    stale_after_seconds = 0

    def normalize(self, item: dict) -> dict:
        symbol = _required_text(item, "symbol", "news_symbol_required")
        headline = _required_text(item, "headline", "news_headline_required")
        event = {
            "event_type": "news",
            "symbol": symbol,
            "exchange": "external",
            "headline": headline,
        }
        source = str(item.get("source") or "").strip()
        if source:
            event["source"] = source
        event_time = _optional_event_time(item)
        if event_time:
            event["event_time"] = event_time
        if "score" in item:
            event["score"] = item["score"]
        return event
