from trade_runtime.ingestion.binance_market import BinanceMarketMessageParser
from trade_runtime.ingestion.okx_market import OkxMarketMessageParser


def test_binance_trade_message_maps_to_market_tick():
    parser = BinanceMarketMessageParser()

    event = parser.parse({"s": "BTCUSDT", "c": "65001.2", "q": "2.50"})

    assert event.symbol == "BTCUSDT"
    assert event.price == 65001.2
    assert event.volume == 2.5


def test_binance_ticker_message_prefers_last_price_over_price_change():
    parser = BinanceMarketMessageParser()

    event = parser.parse({"s": "BTCUSDT", "p": "1048.6", "c": "75123.4", "q": "11807865499.84", "v": "22123.1"})

    assert event.symbol == "BTCUSDT"
    assert event.price == 75123.4
    assert event.volume == 11807865499.84


def test_binance_ticker_message_does_not_treat_price_change_as_last_price():
    parser = BinanceMarketMessageParser()

    try:
        parser.parse({"s": "BTCUSDT", "p": "1048.6", "q": "11807865499.84"})
    except ValueError as exc:
        assert str(exc) == "binance_market_last_price_missing"
        return

    raise AssertionError("expected parser to reject Binance ticker payload without close price")


def test_binance_mark_price_message_maps_to_market_tick_when_mark_price_stream_is_primary():
    parser = BinanceMarketMessageParser()

    event = parser.parse({"s": "BTCUSDT", "p": "64980.5", "r": "0.0004", "_market_stream_kind": "mark_price"})

    assert event.symbol == "BTCUSDT"
    assert event.price == 64980.5
    assert event.volume == 0.0


def test_okx_swap_ticker_message_maps_to_market_tick_symbol():
    parser = OkxMarketMessageParser()

    event = parser.parse(
        {
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "last": "65002.1",
                    "vol24h": "321.5",
                    "volCcy24h": "20963176.15",
                    "ts": "1713942900123",
                }
            ]
        }
    )

    assert event.symbol == "BTCUSDT"
    assert event.price == 65002.1
    assert event.volume == 321.5
    assert event.quote_volume == 20963176.15
    assert event.event_time == "1713942900123"
