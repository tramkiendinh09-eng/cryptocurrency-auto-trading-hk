from trade_runtime.contracts.events import MarketTickEvent


class OkxMarketMessageParser:
    def _normalize_symbol(self, inst_id: str) -> str:
        parts = [part for part in inst_id.split("-") if part and part != "SWAP"]
        return "".join(parts)

    def parse(self, payload: dict) -> MarketTickEvent:
        data = payload["data"][0]
        quote_volume = data.get("volCcyQuote24h") or data.get("volCcy24h") or data.get("turnover") or "0"
        return MarketTickEvent(
            symbol=self._normalize_symbol(data["instId"]),
            exchange="okx",
            price=float(data["last"]),
            volume=float(data["vol24h"]),
            quote_volume=float(quote_volume or 0.0),
            event_time=str(data.get("ts") or data.get("event_time") or ""),
        )
