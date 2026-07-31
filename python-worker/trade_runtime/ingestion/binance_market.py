from trade_runtime.contracts.events import MarketTickEvent


class BinanceMarketMessageParser:
    def _stream_kind(self, payload: dict) -> str:
        normalized = str(payload.get("_market_stream_kind") or payload.get("e") or "").strip().lower()
        if normalized in {"mark_price", "markpriceupdate"}:
            return "mark_price"
        return normalized

    def parse(self, payload: dict) -> MarketTickEvent:
        stream_kind = self._stream_kind(payload)
        raw_price = payload.get("c")
        if stream_kind == "mark_price" and raw_price in (None, ""):
            raw_price = payload.get("p")
        if raw_price in (None, ""):
            raw_price = payload.get("lastPrice")
        if raw_price in (None, ""):
            raw_price = payload.get("price")
        if raw_price in (None, ""):
            raise ValueError("binance_market_last_price_missing")
        raw_volume = payload.get("q")
        if raw_volume in (None, ""):
            raw_volume = payload.get("quoteVolume")
        return MarketTickEvent(
            symbol=payload["s"],
            exchange="binance",
            price=float(raw_price),
            volume=float(raw_volume or 0.0),
            quote_volume=float(raw_volume or 0.0),
            event_time=str(payload.get("E") or payload.get("event_time") or ""),
        )
