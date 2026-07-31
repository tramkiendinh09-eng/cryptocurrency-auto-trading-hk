def _required_text(item: dict, key: str, error_code: str) -> str:
    value = str(item.get(key) or "").strip()
    if not value:
        raise ValueError(error_code)
    return value


def _optional_event_time(item: dict) -> str:
    for key in ("event_time", "createdAt", "created_at", "publishedAt", "published_at", "timestamp", "ts"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


class SocialFeedAdapter:
    stale_after_seconds = 30 * 60

    def normalize(self, item: dict) -> dict:
        symbol = _required_text(item, "symbol", "social_symbol_required")
        if "score" not in item or item.get("score") in (None, ""):
            raise ValueError("social_score_required")
        event = {
            "event_type": "social",
            "symbol": symbol,
            "exchange": "external",
            "score": item["score"],
        }
        source = str(item.get("source") or "").strip()
        if source:
            event["source"] = source
        author = str(item.get("author") or "").strip()
        if author:
            event["author"] = author
        headline = str(item.get("headline") or "").strip()
        if headline:
            event["headline"] = headline
        event_time = _optional_event_time(item)
        if event_time:
            event["event_time"] = event_time
        return event
