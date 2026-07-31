from trade_runtime.ingestion.okx_rest import OkxRestMarketClient


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_okx_rest_client_fetches_and_normalizes_public_market_data(monkeypatch):
    captured = []

    payloads = {
        "/api/v5/market/ticker": {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "last": "65000.5",
                    "vol24h": "100.25",
                    "volCcyQuote24h": "6510000.0",
                    "ts": "1714460000000",
                }
            ],
        },
        "/api/v5/public/mark-price": {
            "code": "0",
            "data": [{"instId": "BTC-USDT-SWAP", "markPx": "65010.5", "ts": "1714460001000"}],
        },
        "/api/v5/public/funding-rate": {
            "code": "0",
            "data": [{"instId": "BTC-USDT-SWAP", "fundingRate": "0.0001", "ts": "1714460002000"}],
        },
        "/api/v5/public/open-interest": {
            "code": "0",
            "data": [{"instId": "BTC-USDT-SWAP", "oi": "12345.6", "oiCcy": "12.3", "ts": "1714460003000"}],
        },
        "/api/v5/market/candles": {
            "code": "0",
            "data": [
                ["1714460000000", "65000", "65100", "64900", "65050", "10", "10.0", "650500", "1"],
                ["1714459940000", "64900", "65000", "64850", "65000", "8", "8.0", "520000", "1"],
            ],
        },
    }

    def fake_get(url, params=None, timeout=None):
        path = url.replace("https://www.okx.com", "")
        captured.append((path, params, timeout))
        return DummyResponse(payloads[path])

    monkeypatch.setattr("trade_runtime.ingestion.okx_rest.requests.get", fake_get)

    client = OkxRestMarketClient(timeout=7)

    ticker = client.fetch_ticker("BTCUSDT")
    mark = client.fetch_mark_price("BTCUSDT")
    funding = client.fetch_funding_rate("BTCUSDT")
    oi = client.fetch_open_interest("BTCUSDT")
    candles = client.fetch_candles("BTCUSDT", interval="1m", limit=2)

    assert ticker["event_type"] == "market_tick"
    assert ticker["symbol"] == "BTCUSDT"
    assert ticker["price"] == 65000.5
    assert ticker["volume"] == 100.25
    assert ticker["quote_volume"] == 6510000.0
    assert mark == {
        "event_type": "mark_price",
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "price": 65010.5,
        "event_time": "1714460001000",
    }
    assert funding["funding_rate"] == 0.0001
    assert oi["open_interest"] == 12345.6
    assert candles[0]["event_type"] == "market_kline"
    assert candles[0]["interval"] == "1m"
    assert candles[0]["close"] == 65050.0
    assert candles[0]["quote_volume"] == 650500.0
    assert captured[0] == ("/api/v5/market/ticker", {"instId": "BTC-USDT-SWAP"}, 7)
