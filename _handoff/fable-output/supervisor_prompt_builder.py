"""Rewritten supervisor prompt builder (task 1 of the hand-off).

Drop-in replacement for `_build_supervisor_prompt` in the decision graph module.

What changed versus the previous inline prompt
-----------------------------------------------
* The instruction block is now two parts:
    1. SUPERVISOR_METHODOLOGY  - what makes an entry worth taking (location,
       regime, reward-to-risk, evidence quality, priority rules). This was
       entirely absent before: the old block mentioned `risk` once and
       `reward`/`stop`/`edge`/`regime`/`overbought`/`extended`/`chase` zero times.
    2. SUPERVISOR_OUTPUT_CONTRACT - the JSON/sizing rules, condensed. Every
       numeric convention the downstream risk gate and order layer depend on
       is preserved verbatim in meaning (keys, action enum, size_hint as an
       equity ratio, exposure = equity * size_hint * leverage_hint,
       min/max_size_hint, integer leverage within min/max_leverage).
* Both constants contain NO literal curly braces. The template renderer
  (`prompting/renderers.py`) substitutes every `{name}` it finds, so a brace
  in prose would be silently deleted. The same text is therefore safe to store
  in `prompt_template.content` (task 3) and the two paths cannot drift apart.
* `_prune_prompt_noise` removes ~10% of the payload that only invites the model
  to reverse-engineer detector internals: the 18-key Wyckoff `config`, the
  WebSocket tuning / doc URL inside `market_api_config`, and the three
  `*_api_config` blocks.
* The "long-term memory is empty" warning no longer tells the model to shrink
  size and confidence. Shrinking size was the exact failure mode in the review
  ("conservative size because RSI 81"). It now tells the model to apply the
  gates strictly and SKIP on ambiguity.
"""

from __future__ import annotations

import json
from typing import Any


# ---------------------------------------------------------------------------
# 1. Methodology: what a good entry looks like. Shared with prompt_template.
#    NO curly braces in this text (see module docstring).
# ---------------------------------------------------------------------------
SUPERVISOR_METHODOLOGY = """ROLE
You are the trading supervisor, the final gate before an order. Sub-agent views, the referee review and wyckoff_shortterm.trade_readiness are inputs, not orders. A Wyckoff "ready" is a candidate, never an entry by itself. Your job is to reject entries with poor location, poor reward-to-risk or the wrong regime, and to leave a working position alone unless it is invalidated.

DECISION PROCEDURE
Run the gates in order. The first failing gate ends the evaluation: SKIP when flat, HOLD when a position exists. A failed gate is never answered with a smaller size.

Gate 1 - Location (the direct fix for the losing trades).
Read wyckoff_shortterm.range_position_pct_24h and range_position_pct_4h when present, otherwise derive them from kline_context.period_summaries (window 240m high_price/low_price) and the 24h high/low in market data. position = (price - low) / (high - low).
- Do not OPEN_LONG or ADD_LONG when the 24h position is at or above 0.80, or price is within 1.0% of the 24h high.
- Do not OPEN_SHORT or ADD_SHORT when the 24h position is at or below 0.20, or price is within 1.0% of the 24h low.
- Momentum confirmation of the same rule: RSI 14 on 15m or 60m at or above 70 blocks new longs; at or below 30 blocks new shorts.
- If wyckoff_shortterm.macro_position_verdict starts with "veto", Gate 1 has failed regardless of anything else.
- A high or low percentile is a reason to SKIP, not a reason to size down.

Gate 2 - Regime.
Classify the symbol as trending only when all three agree: kline_context.ema_trend 60m, the sign of price_change_pct 240m, and the sign of price_change_pct 60m, and additionally the absolute 240m price_change_pct is greater than 1.5 times atr_pct 60m. Anything else is ranging or mean-reverting. Minute-scale moves in this market are mean-reverting on the hourly scale (calibration: price_break hit rate 0.45-0.47 versus a 0.505 baseline), so:
- In a ranging regime a breakout_long or breakdown_short trigger is downgraded one level: ready becomes watch, and watch is not tradeable. Only spring_long or upthrust_short reversals from the range edge, with retest_confirmed true and trading toward the range middle, may be taken.
- In a trending regime breakouts are tradeable only in the direction of the trend, and only after Gate 1 passes. Counter-trend entries require a reversal trigger plus Gate 3 at 3.0 or better.
- State the regime you assigned in summary_reason.

Gate 3 - Reward-to-risk.
risk_pct = absolute(entry - invalidation) / entry * 100, where invalidation is structural: wyckoff_shortterm.invalidation, range_low for longs or range_high for shorts. Never widen it to manufacture a ratio.
reward_pct = distance from entry to the nearest structural target in the trade direction: for longs the 24h high (or the 240m high if higher), for shorts the 24h low (or the 240m low if lower). If price is already at or beyond the target, reward is zero.
Require reward_pct / risk_pct at or above 2.0 and reward_pct at or above 2 times atr_pct 15m. Otherwise SKIP. Write risk_pct, reward_pct and the ratio into summary_reason.

Gate 4 - Evidence quality.
- Volume confirmation comes only from kline_ohlcv bars: the trigger bar quote_volume_ratio must be at or above 1.2. Ticker 24h cumulative volume is not bar confirmation.
- trap_risk must be low. effort_result must not be effort_without_result. retest_confirmed must be true for breakout entries.
- Funding and open interest must not contradict the direction: positive funding with rising OI at a range high is a crowded long, SKIP the long; the mirror applies to shorts.
- market_source_status must be ready and market_tick_staleness_seconds below 60.

Gate 5 - Conflict.
If the referee review, any sub-agent, or the news context names a disqualifier (scheduled event inside the holding window, liquidation cluster just beyond the entry, exchange or data outage), SKIP. Conflicting sub-agent directions with no majority also SKIP.

PRIORITY RULES
- Missing an entry costs nothing; a bad entry costs money. When a gate is ambiguous, the answer is SKIP.
- Never trade a reason you would otherwise write as a caveat. If your summary_reason would contain "reduced size because" followed by RSI, overbought, oversold, extended, chasing, empty memory or weak confirmation, the correct output is SKIP with that reason.
- confidence must reflect the gates, not the Wyckoff confidence number. Any OPEN or ADD requires confidence at or above 60 and all five gates passed. A position that passes all gates gets a full size inside sizing_constraints; there is no half-conviction size.
- Position management is not the problem and must not be over-tuned. When a position exists: CLOSE on a breach of invalidation or a Wyckoff reversal trigger against the position; REDUCE only after a partial target is reached; otherwise HOLD. Do not ADD within 60 minutes of opening, and never ADD when Gate 1 fails for the add price.
- summary_reason must state, in this order: regime, 24h position, risk_pct / reward_pct / ratio, and the gate that decided. For SKIP name the failed gate first."""


# ---------------------------------------------------------------------------
# 2. Output contract: the numeric conventions the risk gate and order layer read.
#    Meaning preserved from the previous prompt; wording condensed.
#    NO curly braces in this text.
# ---------------------------------------------------------------------------
SUPERVISOR_OUTPUT_CONTRACT = """OUTPUT CONTRACT
Return JSON only with exactly these keys: action, side, confidence, size_hint, leverage_hint, holding_window, invalidation, summary_reason.
- action is one of OPEN_LONG, OPEN_SHORT, ADD_LONG, ADD_SHORT, REDUCE, CLOSE, HOLD, SKIP. Never return open, open_position, buy, sell, long, short, wait, none or no_action.
- Flat with no entry passing all gates: SKIP. Flat with an entry passing all gates: OPEN_LONG or OPEN_SHORT. Position exists and no change: HOLD. For HOLD or SKIP set invalidation to no_trade_condition and size_hint to 0.
- side is one of long, short, flat. confidence is an integer 0-100. holding_window is a concrete duration such as 30m-4h, never N/A, none, null, 0 or empty. invalidation is never N/A, none, null or empty.
- Use current_time, current_position_opened_at and current_position_holding_minutes to judge holding duration. If current_position_opened_at is present, opening another position requires all gates plus confidence at or above 70.
- Use agent_messages_json, deliberation_summary and deliberation_referee_review_json as context; the referee is advisory and you make the final decision.
- size_hint is a plain number 0-1: the fraction of account equity committed as margin. Exposure is account_equity * size_hint * leverage_hint, so leverage does increase position size. size_hint is either 0 (SKIP or HOLD) or between sizing_constraints.min_size_hint and max_size_hint; values below the minimum are raised to it, so choose inside the range. No units, symbols, ranges or text in size_hint.
- leverage_hint is a plain integer between sizing_constraints.min_leverage and max_leverage; omit it to use default_leverage. No x, ranges or text.
- Exposure must clear this symbol's exchange minimum notional: at default_leverage that means size_hint of at least min_viable_size_hint, and raising leverage lowers that floor down to min_viable_size_hint_at_max_leverage. An order below the minimum is rejected, which is strictly worse than SKIP. min_order_notional_usdt is per symbol; never carry a size over from another symbol. Fills truncate to a whole multiple of notional_step_usdt; aim at a multiple.
- Choose leverage for the setup, not to satisfy the minimum notional. If the only way to clear the floor is leverage you would not otherwise take, SKIP. If any_size_tradeable is false, SKIP."""


# Keys the model does not need and that invite it to second-guess internals.
_WYCKOFF_NOISE_KEYS = ("config",)
_MARKET_API_NOISE_KEYS = (
    "ws_base_url",
    "ws_path",
    "ws_stream_name_template",
    "ws_combined_enabled",
    "ws_symbol_lowercase",
    "ws_ping_interval_seconds",
    "ws_pong_timeout_seconds",
    "ws_connection_ttl_hours",
    "ws_max_streams_per_connection",
    "ws_control_messages_per_second",
    "doc_reference_url",
    "id",
    "version_no",
    "priority",
)
_STRATEGY_CONTEXT_NOISE_KEYS = ("news_api_config", "onchain_api_config", "social_api_config", "market_data_config")


def _prune_prompt_noise(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the prompt payload without detector/transport internals.

    Everything removed here is either constant across decisions or describes
    plumbing (WebSocket tuning, API row ids). None of it is read back by the
    parser, the risk gate or trigger_policy, so removing it cannot break the
    downstream contract. It shaves roughly 1.6k characters per prompt.
    """
    pruned = json.loads(json.dumps(payload, ensure_ascii=False, default=str))

    def strip_wyckoff(block: Any) -> None:
        if isinstance(block, dict):
            for key in _WYCKOFF_NOISE_KEYS:
                block.pop(key, None)

    strip_wyckoff(pruned.get("wyckoff_shortterm"))
    kline_context = pruned.get("kline_context")
    if isinstance(kline_context, dict):
        strip_wyckoff(kline_context.get("wyckoff_shortterm"))

    strategy_context = pruned.get("strategy_context")
    if isinstance(strategy_context, dict):
        for key in _STRATEGY_CONTEXT_NOISE_KEYS:
            strategy_context.pop(key, None)
        market_api_config = strategy_context.get("market_api_config")
        if isinstance(market_api_config, dict):
            for key in _MARKET_API_NOISE_KEYS:
                market_api_config.pop(key, None)
    return pruned


def _memory_warning(long_term_items: list[Any]) -> str:
    if long_term_items:
        return ""
    # Old text asked the model to "lower confidence and size_hint". That is the
    # anti-pattern the review found on every losing entry. Ask for stricter
    # gating instead.
    return (
        "\n\nNOTE: long-term memory is empty, so there is no historical evidence about this "
        "symbol's false-breakout rate or your own past errors. Do not compensate by shrinking "
        "size or confidence. Compensate by applying Gates 1-5 strictly and returning SKIP on any "
        "ambiguity. A smaller bad entry is still a bad entry.\n"
    )


def _build_supervisor_prompt(state: "DecisionState", ai_model_config: dict) -> str:  # noqa: F821 - type lives in caller module
    runtime_config = state.get("runtime_config") or {}
    if not isinstance(runtime_config, dict):
        runtime_config = {}
    prompt_short_term_memory = build_prompt_short_term_memory(state)  # noqa: F821
    prompt_long_term_memory = build_prompt_long_term_memory(state)  # noqa: F821
    prompt_memory_usage = build_prompt_memory_usage(  # noqa: F821
        state,
        short_term_memory=prompt_short_term_memory,
        long_term_memory=prompt_long_term_memory,
    )
    prompt_payload = {
        "symbol": state.get("symbol"),
        "exchange": state.get("exchange"),
        "mode": state.get("mode"),
        "event_strength": state.get("event_strength"),
        "account_equity": state.get("account_equity", 0.0),
        "daily_pnl": state.get("daily_pnl", 0.0),
        "current_position_side": state.get("current_position_side", "flat"),
        "current_position_quantity": state.get("current_position_quantity", 0.0),
        "current_position_notional": state.get("current_position_notional", 0.0),
        "current_position_opened_at": state.get("current_position_opened_at"),
        "current_time": resolve_prompt_current_time(state),  # noqa: F821
        "current_position_holding_minutes": resolve_current_position_holding_minutes(state),  # noqa: F821
        "risk_limits": {
            "max_position_ratio": runtime_config.get("max_position_ratio"),
            "max_daily_loss": runtime_config.get("max_daily_loss"),
            "max_consecutive_failures": runtime_config.get("max_consecutive_failures"),
            "live_order_requires_healthy_account": runtime_config.get("live_order_requires_healthy_account"),
        },
        "sizing_constraints": _sizing_constraints(state, runtime_config),  # noqa: F821
        "strategy_context": build_prompt_strategy_context(state),  # noqa: F821
        **_market_evidence(state),  # noqa: F821
        "agent_messages_json": json.dumps(
            state.get("agent_messages") or [], ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str
        ),
        "deliberation_summary": str(state.get("deliberation_summary") or "").strip(),
        "deliberation_referee_review_json": json.dumps(
            state.get("deliberation_referee_review") or {},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            default=str,
        ),
        "views": {
            "market_view": state.get("market_view") or {},
            "news_view": state.get("news_view") or {},
            "onchain_view": state.get("onchain_view") or {},
            "social_view": state.get("social_view") or {},
        },
        "short_term_memory": prompt_short_term_memory,
        "long_term_memory": prompt_long_term_memory,
        "memory_usage": prompt_memory_usage,
    }
    prompt_payload = _prune_prompt_noise(prompt_payload)

    previous_supervisor_decisions_json = json.dumps(
        state.get("recent_supervisor_decisions")
        or ((prompt_short_term_memory.get("supervisor_decision") or {}).get("items") or []),
        ensure_ascii=False,
        default=str,
    )
    long_term_memory = state.get("long_term_memory") or {}
    long_term_items = long_term_memory.get("items") or []

    return (
        f"{SUPERVISOR_METHODOLOGY}\n\n"
        f"{SUPERVISOR_OUTPUT_CONTRACT}\n\n"
        f"PREVIOUS SUPERVISOR DECISIONS\n{previous_supervisor_decisions_json}\n"
        f"LONG-TERM EXPERIENCE MEMORY\n{json.dumps(prompt_long_term_memory, ensure_ascii=False, default=str)}\n"
        f"MEMORY USAGE\n{json.dumps(prompt_memory_usage, ensure_ascii=False, default=str)}\n"
        f"DECISION CONTEXT\n{json.dumps(prompt_payload, ensure_ascii=False)}"
        f"{_memory_warning(long_term_items)}"
    )


if __name__ == "__main__":
    # Quick self-check: no braces in template-bound text, and the keyword
    # coverage the review complained about is now present.
    for name, text in (("METHODOLOGY", SUPERVISOR_METHODOLOGY), ("CONTRACT", SUPERVISOR_OUTPUT_CONTRACT)):
        assert "{" not in text and "}" not in text, f"{name} contains braces; renderer would eat them"
    combined = (SUPERVISOR_METHODOLOGY + SUPERVISOR_OUTPUT_CONTRACT).lower()
    for word in ("risk", "reward", "regime", "overbought", "extended", "chas", "invalidation", "edge"):
        print(f"{word:12s} {combined.count(word)}")
    print("methodology chars:", len(SUPERVISOR_METHODOLOGY), "contract chars:", len(SUPERVISOR_OUTPUT_CONTRACT))
