import logging

import pytest

from datetime import datetime, timezone

from feed_adapter.models import UpstreamUnavailableError
from feed_adapter.providers.onchain import OnchainFlowsProvider


def test_onchain_flows_provider_parses_exchange_flow_items_for_requested_symbol():
    html_payload = """
    <html>
      <body>
        <section>
          <h2>Real Time Crypto Alerts Feed</h2>
          <div>BTC</div>
          <div>11:39</div>
          <div>$71.9M</div>
          <div>Coinbase Prime: Hot Wallet -&gt; Unknown wallet</div>
          <div>Movement follows a recent withdrawal pattern.</div>
          <div>Exchange outflow High impact</div>
          <div>ETH</div>
          <div>11:41</div>
          <div>$22.0M</div>
          <div>Unknown wallet -&gt; Binance</div>
          <div>Large ETH deposit into exchange.</div>
          <div>Exchange inflow High impact</div>
          <div>BTC</div>
          <div>11:44</div>
          <div>$9.0M</div>
          <div>Unknown wallet -&gt; Custody wallet</div>
          <div>Internal treasury rebalance.</div>
          <div>Rotation Watchlist</div>
        </section>
      </body>
    </html>
    """.strip()

    provider = OnchainFlowsProvider(
        page_urls=["https://onchain.example/live"],
        fetch_text=lambda url, timeout, user_agent: html_payload,
        current_time_supplier=lambda: datetime(2026, 4, 22, 3, 49, 16, tzinfo=timezone.utc),
    )

    items = provider.fetch("BTCUSDT")

    assert items == [
        {
            "symbol": "BTCUSDT",
            "asset": "BTC",
            "wallet": "Coinbase Prime: Hot Wallet -> Unknown wallet",
            "route": "Coinbase Prime: Hot Wallet -> Unknown wallet",
            "flow": "exchange_outflow",
            "amountUsd": 71900000.0,
            "impact": "high",
            "summary": "Movement follows a recent withdrawal pattern.",
            "source": "onchain.example",
            "event_time": "2026-04-22T03:39:00Z",
        }
    ]


def test_onchain_flows_provider_derives_stable_event_time_from_time_token():
    html_payload = """
    <html>
      <body>
        <section>
          <h2>Real Time Crypto Alerts Feed</h2>
          <div>BTC</div>
          <div>11:39</div>
          <div>$71.9M</div>
          <div>Coinbase Prime: Hot Wallet -&gt; Unknown wallet</div>
          <div>Movement follows a recent withdrawal pattern.</div>
          <div>Exchange outflow High impact</div>
        </section>
      </body>
    </html>
    """.strip()
    current_times = iter(
        [
            datetime(2026, 4, 22, 3, 49, 16, tzinfo=timezone.utc),
            datetime(2026, 4, 22, 3, 50, 10, tzinfo=timezone.utc),
        ]
    )
    provider = OnchainFlowsProvider(
        page_urls=["https://onchain.example/live"],
        fetch_text=lambda url, timeout, user_agent: html_payload,
        current_time_supplier=lambda: next(current_times),
    )

    first = provider.fetch("BTCUSDT")
    second = provider.fetch("BTCUSDT")

    assert first[0]["event_time"] == "2026-04-22T03:39:00Z"
    assert second[0]["event_time"] == "2026-04-22T03:39:00Z"


def test_onchain_flows_provider_filters_events_older_than_freshness_window():
    html_payload = """
    <html>
      <body>
        <section>
          <h2>Real Time Crypto Alerts Feed</h2>
          <div>BTC</div>
          <div>11:39</div>
          <div>$71.9M</div>
          <div>Coinbase Prime: Hot Wallet -&gt; Unknown wallet</div>
          <div>Movement follows a recent withdrawal pattern.</div>
          <div>Exchange outflow High impact</div>
        </section>
      </body>
    </html>
    """.strip()
    provider = OnchainFlowsProvider(
        page_urls=["https://onchain.example/live"],
        fetch_text=lambda url, timeout, user_agent: html_payload,
        current_time_supplier=lambda: datetime(2026, 4, 22, 5, 49, 16, tzinfo=timezone.utc),
        max_age_minutes=5,
    )

    items = provider.fetch("BTCUSDT")

    assert items == []


def test_onchain_flows_provider_raises_upstream_unavailable_when_all_sources_fail():
    provider = OnchainFlowsProvider(
        page_urls=["https://onchain.example/live"],
        fetch_text=lambda url, timeout, user_agent: (_ for _ in ()).throw(RuntimeError("timeout")),
    )

    with pytest.raises(UpstreamUnavailableError, match="onchain_upstream_unavailable"):
        provider.fetch("BTCUSDT")


def test_onchain_flows_provider_logs_summary(caplog):
    html_payload = """
    <html>
      <body>
        <section>
          <h2>Real Time Crypto Alerts Feed</h2>
          <div>BTC</div>
          <div>11:39</div>
          <div>$71.9M</div>
          <div>Coinbase Prime: Hot Wallet -&gt; Unknown wallet</div>
          <div>Movement follows a recent withdrawal pattern.</div>
          <div>Exchange outflow High impact</div>
          <div>ETH</div>
          <div>11:41</div>
          <div>$22.0M</div>
          <div>Unknown wallet -&gt; Binance</div>
          <div>Large ETH deposit into exchange.</div>
          <div>Exchange inflow High impact</div>
        </section>
      </body>
    </html>
    """.strip()

    provider = OnchainFlowsProvider(
        page_urls=["https://onchain.example/live"],
        fetch_text=lambda url, timeout, user_agent: html_payload,
        current_time_supplier=lambda: datetime(2026, 4, 22, 3, 49, 16, tzinfo=timezone.utc),
    )

    with caplog.at_level(logging.INFO):
        items = provider.fetch("BTCUSDT")

    assert len(items) == 1
    assert "provider=onchain" in caplog.text
    assert "url=https://onchain.example/live" in caplog.text
    assert "symbol=BTCUSDT" in caplog.text
    assert "raw_candidates=2" in caplog.text
    assert "symbol_filtered=1" in caplog.text
    assert "flow_filtered=0" in caplog.text
    assert "returned_items=1" in caplog.text
