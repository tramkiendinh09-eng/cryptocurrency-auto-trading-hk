from trade_runtime.config import RuntimeBootstrap, RuntimeMarketApiConfig
from trade_runtime.source_config_client import SourceConfigClient


def test_source_config_client_returns_market_api_config_from_bootstrap():
    bootstrap = RuntimeBootstrap(
        marketApiConfig=RuntimeMarketApiConfig(
            id=91,
            transportType="WEBSOCKET",
            vendorCode="BINANCE",
            marketScope="FUTURES",
            wsBaseUrl="wss://fstream.binance.com",
            wsPath="/stream",
            wsStreamNameTemplate="{symbol_lower}@ticker",
            wsCombinedEnabled=True,
            wsSymbolLowercase=True,
            wsConnectionTtlHours=24,
        )
    )

    resolved = SourceConfigClient(bootstrap).resolve_market_api_config(symbol="BTCUSDT", exchange="binance")

    assert resolved is not None
    assert resolved.id == 91
    assert resolved.market_scope == "FUTURES"
    assert resolved.transport_type == "WEBSOCKET"
    assert resolved.ws_path == "/stream"


def test_source_config_client_returns_none_for_disabled_market_api_config():
    bootstrap = RuntimeBootstrap(
        marketApiConfig=RuntimeMarketApiConfig(
            id=91,
            transportType="WEBSOCKET",
            vendorCode="BINANCE",
            enabled="0",
        )
    )

    resolved = SourceConfigClient(bootstrap).resolve_market_api_config(symbol="BTCUSDT", exchange="binance")

    assert resolved is None


def test_source_config_client_returns_none_when_symbol_not_in_apply_symbols():
    bootstrap = RuntimeBootstrap(
        marketApiConfig=RuntimeMarketApiConfig(
            id=91,
            transportType="WEBSOCKET",
            vendorCode="BINANCE",
            enabled="1",
            applySymbols='["ETHUSDT","SOLUSDT"]',
        )
    )

    resolved = SourceConfigClient(bootstrap).resolve_market_api_config(symbol="BTCUSDT", exchange="binance")

    assert resolved is None


def test_source_config_client_returns_none_when_exchange_does_not_match_symbol_scope():
    bootstrap = RuntimeBootstrap(
        symbolScope={"symbol": "BTCUSDT", "exchangeCode": "okx"},
        marketApiConfig=RuntimeMarketApiConfig(
            id=91,
            transportType="WEBSOCKET",
            vendorCode="BINANCE",
            enabled="1",
        ),
    )

    resolved = SourceConfigClient(bootstrap).resolve_market_api_config(symbol="BTCUSDT", exchange="binance")

    assert resolved is None
