from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from trade_runtime.prompting.render_context_builder import (
    build_agent_render_context,
    build_supervisor_render_context,
)
from trade_runtime.prompting.renderers import VARIABLE_PATTERN, render_template


_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_prompt_templates_from_sql(path: Path) -> dict[str, dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    templates: dict[str, dict[str, object]] = {}
    for match in re.finditer(r"INSERT INTO `prompt_template` VALUES \((.*)\);", text):
        row = ast.literal_eval(f"({match.group(1)})")
        templates[row[2]] = {
            "content": row[3],
            "variables": json.loads(row[4]),
        }
    return templates


def _load_sql_prompt_templates() -> dict[str, dict[str, object]]:
    return _load_prompt_templates_from_sql(_REPO_ROOT / "sql" / "ai_trading.sql")


def _representative_state() -> dict[str, object]:
    current_time = "2026-05-08T10:00:00+00:00"
    bars = [
        {
            "open_time": f"2026-05-08T{8 + index // 4:02d}:{(index % 4) * 15:02d}:00+00:00",
            "open": 99000.0 + index * 10,
            "high": 99120.0 + index * 10,
            "low": 98880.0 + index * 10,
            "close": 98950.0 + index * 10,
            "quote_volume": 1200000.0 + index * 10000,
        }
        for index in range(8)
    ]
    position_risk_context = {
        "side": "long",
        "quantity": 0.2,
        "entry_price": 100000.0,
        "current_price": 98800.0,
        "price_source": "mark_price",
        "trade_tick_stale": True,
        "pnl_pct": -1.2,
        "adverse_move_pct": 1.2,
        "peak_unrealized_pnl_pct": 0.4,
        "profit_giveback_pct": 0.4,
    }
    feature_snapshot = {
        "symbol": "BTCUSDT",
        "price_change_pct": -0.8,
        "mark_price": 98800.0,
        "latest_kline_close": 98750.0,
        "latest_trade_price": 100000.0,
        "stale_trade_price": 100000.0,
        "trade_tick_status": "stale",
        "market_tick_staleness_seconds": 240.0,
        "position_risk_context": position_risk_context,
        "wyckoff_15m_bars": {
            "required_15m_bars": 8,
            "provided_15m_bars": 8,
            "bars": bars,
        },
        "kline_period_summaries": [
            {
                "window": "15m",
                "source": "kline_ohlcv",
                "sample_count": 8,
                "price_change_pct": -0.5,
                "quote_volume_ratio": 1.4,
            }
        ],
        "kline_volume_price_signals": ["15m:price_down_volume_expands"],
        "wyckoff_shortterm": {
            "phase": "markdown",
            "entry_bias": "bearish",
            "trade_readiness": "ready",
        },
    }
    return {
        "trace_id": "trace-sql-template-render",
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "live",
        "event_strength": "position_risk",
        "current_position_side": "long",
        "current_position_quantity": 0.2,
        "current_position_notional": 19760.0,
        "current_position_opened_at": "2026-05-08T09:20:00+00:00",
        "current_time": current_time,
        "account_equity": 50000.0,
        "daily_pnl": -200.0,
        "runtime_config": {
            "max_position_ratio": 0.25,
            "max_daily_loss": 1000.0,
            "max_consecutive_failures": 3,
            "live_order_requires_healthy_account": True,
        },
        "strategy_context": {
            "strategy_config": {
                "promptQuality": {
                    "recentNewsTtlSeconds": 7200,
                    "recentOnchainTtlSeconds": 7200,
                }
            }
        },
        "feature_snapshot": feature_snapshot,
        "event_bundle": [
            {
                "event_type": "market_tick",
                "symbol": "BTCUSDT",
                "price": 100000.0,
                "event_time": "2026-05-08T09:56:00+00:00",
            },
            {
                "event_type": "mark_price",
                "symbol": "BTCUSDT",
                "price": 98800.0,
                "event_time": current_time,
            },
            {
                "event_type": "market_metric",
                "latest_trade_price": 100000.0,
                "stale_trade_price": 100000.0,
                "trade_tick_status": "stale",
                "market_tick_staleness_seconds": 240.0,
                "latest_kline_close": 98750.0,
                "mark_price": 98800.0,
            },
            {
                "event_type": "position_risk",
                "severity": "close",
                "action": "REVIEW",
                "reason": "adverse_move_close",
                "current_price": 98800.0,
                "event_time": current_time,
            },
            {
                "event_type": "news",
                "headline": "Fresh ETF inflow slows",
                "score": -0.6,
                "event_time": "2026-05-08T09:55:00+00:00",
            },
            {
                "event_type": "news",
                "headline": "Fresh ETF inflow slows",
                "score": -0.6,
                "event_time": "2026-05-08T09:56:00+00:00",
            },
            {
                "event_type": "news",
                "headline": "Old macro headline",
                "score": -0.2,
                "event_time": "2026-05-08T06:30:00+00:00",
            },
            {
                "event_type": "onchain",
                "txHash": "0xfresh",
                "flow": "exchange_inflow",
                "amountUsd": 2500000.0,
                "event_time": "2026-05-08T09:50:00+00:00",
            },
            {
                "event_type": "onchain",
                "txHash": "0xfresh",
                "flow": "exchange_inflow",
                "amountUsd": 2500000.0,
                "event_time": "2026-05-08T09:51:00+00:00",
            },
            {
                "event_type": "onchain",
                "txHash": "0xold",
                "flow": "exchange_outflow",
                "amountUsd": 100000.0,
                "event_time": "2026-05-08T06:30:00+00:00",
            },
        ],
        "short_term_memory": {"ttl_policy": {"market": 3600, "news": 7200, "onchain": 7200}},
        "recent_supervisor_decisions": [
            {
                "action": "HOLD",
                "side": "short",
                "confidence": 58,
                "size_hint": 0,
                "leverage_hint": 1,
                "holding_window": "15m-240m",
                "invalidation": "range_break_above_2210",
                "summary_reason": "hold_range_short",
            },
            {
                "action": "SKIP",
                "side": "flat",
                "confidence": 41,
                "size_hint": 0,
                "leverage_hint": 1,
                "holding_window": "15m-240m",
                "invalidation": "no_trade_condition",
                "summary_reason": "wait_for_breakout",
            },
        ],
        "long_term_memory": {"items": []},
        "memory_usage": {"used_memory_ids": []},
        "market_view": {"bias": "bearish"},
        "news_view": {"bias": "bearish"},
        "onchain_view": {"bias": "bearish"},
        "social_view": {"bias": "neutral"},
    }


def _placeholder_names(content: str) -> set[str]:
    return {
        key.strip()
        for key in VARIABLE_PATTERN.findall(content)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip())
    }


def test_market_render_context_falls_back_to_mark_price_before_stale_trade_price():
    state = _representative_state()

    context = build_agent_render_context(state, agent_code="market_agent", rule_view={})
    market_context = json.loads(context["market_context_json"])

    assert market_context["latest_price"] == 98800.0
    assert market_context["effective_price"] == 98800.0
    assert market_context["effective_price_source"] == "mark_price"
    assert market_context["latest_trade_price"] == 100000.0
    assert market_context["stale_trade_price"] == 100000.0
    assert market_context["trade_tick_status"] == "stale"


def test_sql_prompt_templates_render_new_quality_fields_without_empty_values():
    templates = _load_sql_prompt_templates()
    state = _representative_state()
    contexts = {
        "trade.supervisor.v1": build_supervisor_render_context(state),
        "trade.supervisor.fallback": build_supervisor_render_context(state),
        "trade.market.v1": build_agent_render_context(state, agent_code="market_agent", rule_view={"risk": "strict"}),
        "trade.news.v1": build_agent_render_context(state, agent_code="news_agent", rule_view={"risk": "strict"}),
        "trade.onchain.v1": build_agent_render_context(state, agent_code="onchain_agent", rule_view={"risk": "strict"}),
    }

    rendered = {}
    for code, context in contexts.items():
        content = str(templates[code]["content"])
        variables = set(templates[code]["variables"])
        placeholders = _placeholder_names(content)
        assert placeholders <= set(context)
        assert variables <= set(context)
        for variable in placeholders:
            assert f"{{{variable}}}" not in render_template({"content": content}, context)
        rendered[code] = render_template({"content": content}, context)
        assert not re.search(r"\?{4,}", rendered[code])

    supervisor_prompt = rendered["trade.supervisor.v1"]
    fallback_prompt = rendered["trade.supervisor.fallback"]
    market_prompt = rendered["trade.market.v1"]
    news_prompt = rendered["trade.news.v1"]
    onchain_prompt = rendered["trade.onchain.v1"]

    for prompt in (supervisor_prompt, fallback_prompt, market_prompt):
        assert "Position risk context:" in prompt
        assert '"current_price": 98800.0' in prompt
        assert '"adverse_move_pct": 1.2' in prompt
        assert '"provided_15m_bars": 8' in prompt
        assert '"required_15m_bars": 8' in prompt
        assert '"trade_tick_status": "stale"' in prompt
        assert '"effective_price_source": "mark_price"' in prompt

    for prompt in (supervisor_prompt, fallback_prompt, news_prompt):
        assert '"stale_items_filtered": 1' in prompt
        assert '"duplicate_items_filtered": 1' in prompt

    for prompt in (supervisor_prompt, fallback_prompt, onchain_prompt):
        assert '"total_inflow_usd": 2500000.0' in prompt
        assert '"duplicate_items_filtered": 1' in prompt

    for prompt in (supervisor_prompt, fallback_prompt):
        assert "《上次决策记录》" in prompt
        assert '"action": "HOLD"' in prompt
        assert '"summary_reason": "wait_for_breakout"' in prompt


def test_online_sql_supervisor_templates_keep_previous_supervisor_decisions_section():
    sql_paths = [
        _REPO_ROOT / "sql" / "ai_trading_online.sql",
        _REPO_ROOT / "feed-adapter" / "ai_trading_online.sql",
    ]

    for path in sql_paths:
        templates = _load_prompt_templates_from_sql(path)
        for template_code in ("trade.supervisor.v1", "trade.supervisor.fallback"):
            template = templates[template_code]
            assert "previous_supervisor_decisions_json" in template["content"], str(path)
            assert "previous_supervisor_decisions_json" in template["variables"], str(path)
