def _build_supervisor_prompt(state: DecisionState, ai_model_config: dict) -> str:
    runtime_config = state.get("runtime_config") or {}
    if not isinstance(runtime_config, dict):
        runtime_config = {}
    prompt_short_term_memory = build_prompt_short_term_memory(state)
    prompt_long_term_memory = build_prompt_long_term_memory(state)
    prompt_memory_usage = build_prompt_memory_usage(
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
        "current_time": resolve_prompt_current_time(state),
        "current_position_holding_minutes": resolve_current_position_holding_minutes(state),
        "risk_limits": {
            "max_position_ratio": runtime_config.get("max_position_ratio"),
            "max_daily_loss": runtime_config.get("max_daily_loss"),
            "max_consecutive_failures": runtime_config.get("max_consecutive_failures"),
            "live_order_requires_healthy_account": runtime_config.get("live_order_requires_healthy_account"),
        },
        # 可下仓位的真实区间。不给这一段，模型只能猜，而它猜出来的
        # size_hint 已经被证实低到交易所不接。
        "sizing_constraints": _sizing_constraints(state, runtime_config),
        "strategy_context": build_prompt_strategy_context(state),
        # The instruction block below tells the model to base its volume-price and
        # Wyckoff judgement on kline_context.period_summaries. Until now this
        # payload carried no market data at all — only the sub-agents' prose
        # views — so the supervisor was asked to confirm an entry from evidence it
        # had never been shown, and correctly answered SKIP every single time
        # (71 of 71 LLM decisions in this deployment). The rich context is already
        # assembled for the template path; the fallback prompt needs it just as
        # much.
        **_market_evidence(state),
        "agent_messages_json": json.dumps(state.get("agent_messages") or [], ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str),
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
    previous_supervisor_decisions_json = json.dumps(
        state.get("recent_supervisor_decisions")
        or ((prompt_short_term_memory.get("supervisor_decision") or {}).get("items") or []),
        ensure_ascii=False,
        default=str,
    )
    # 检查长期记忆是否为空，添加警告提示
    long_term_memory = state.get("long_term_memory") or {}
    long_term_items = long_term_memory.get("items") or []
    memory_warning = ""
    if not long_term_items:
        memory_warning = (
            "\n\n⚠️ 警告：长期记忆为空，系统无法参考历史交易经验。\n"
            "这可能导致：\n"
            "1. 重复犯相同的错误（如识别假突破）\n"
            "2. 无法根据历史表现调整风险偏好\n"
            "3. 缺少决策连续性\n\n"
            "建议：请更加谨慎，降低confidence和size_hint，避免在不确定的市场条件下开仓。\n"
            "如果这是新系统，请确保记忆整合任务正在运行。\n"
        )

    return (
        "You are the trading supervisor. "
        "Return JSON only with keys action, side, confidence, size_hint, leverage_hint, holding_window, invalidation, summary_reason. "
        "Allowed action values only: OPEN_LONG, OPEN_SHORT, ADD_LONG, ADD_SHORT, REDUCE, CLOSE, HOLD, SKIP. "
        "Do not return open, open_position, buy, sell, long, short, wait, none, or no_action. "
        "If current position is flat and there is no confirmed entry, use SKIP. "
        "If current position is flat and entry is confirmed, use OPEN_LONG or OPEN_SHORT. "
        "If a position exists and you want no change, use HOLD. "
        "For HOLD or SKIP, set invalidation to no_trade_condition. "
        "If current_position_opened_at is present, opening a new position requires strong confirmation. "
        "Use current_time and current_position_holding_minutes together with current_position_opened_at to judge holding duration. "
        "After a position is opened, avoid frequent ADD_LONG, ADD_SHORT, REDUCE, or CLOSE. "
        "If the current position was opened recently and no invalidation or risk event is present, prefer HOLD. "
        "Use agent_messages_json, deliberation_summary, and deliberation_referee_review_json as decision context. "
        "The referee review is advisory only; you must make the final decision. "
        "Use side in {long, short, flat}. "
        "confidence must be an integer from 0 to 100. "
        "holding_window must be a concrete duration like 15m-4h; never return N/A, none, null, 0, or empty. "
        "invalidation must never be N/A, none, null, or empty. "
        "For volume-price and Wyckoff judgment, prioritize kline_context.period_summaries with source=kline_ohlcv, "
        "quote_volume_sum, quote_volume_ratio, and volume_price_signals; do not treat ticker 24h cumulative volume as bar volume confirmation. "
        "size_hint must be a plain numeric account-equity ratio from 0 to 1, such as 0.08; "
        "do not include BTC, USDT, percent signs, units, ranges, or explanatory text in size_hint. "
        "leverage_hint must be a plain integer, such as 8; "
        "do not include x, ranges, or explanatory text in leverage_hint. "
        "Read sizing_constraints before choosing size_hint and leverage_hint. "
        "size_hint is the fraction of account equity committed as margin; exposure is "
        "account_equity * size_hint * leverage_hint, so leverage does increase position "
        "size. size_hint must be either 0 (with SKIP or HOLD) or between min_size_hint "
        "and max_size_hint, which cap margin, not exposure. Values below min_size_hint are "
        "raised to it, so pick within the range rather than under it. Exposure must also clear the exchange minimum "
        "notional: at default_leverage that means size_hint of at least "
        "min_viable_size_hint, and raising leverage_hint lowers that floor down to "
        "min_viable_size_hint_at_max_leverage. An order below the minimum notional is "
        "rejected outright, so it is strictly worse than SKIP. min_order_notional_usdt is "
        "this symbol's own floor, not a shared one — symbols differ by more than 4x, so "
        "never carry a size over from another symbol. Fills truncate down to a whole "
        "multiple of notional_step_usdt, so exposure landing just under a step is paid "
        "for in margin but never opened; aim at a multiple. leverage_hint must be an "
        "integer between min_leverage and max_leverage; omit it to use default_leverage. "
        "Values below min_leverage are raised to it, so pick within the range rather "
        "than under it. Choose leverage for the setup, not to satisfy the minimum "
        "notional — if the only way to clear the floor is leverage you would not "
        "otherwise take, return SKIP. "
        "If any_size_tradeable is false, no position is possible at this equity even at "
        "max_leverage: return SKIP.\n"
        f"《上次决策记录》\n{previous_supervisor_decisions_json}\n"
        f"Long-term experience memory\n{json.dumps(prompt_long_term_memory, ensure_ascii=False, default=str)}\n"
        f"Memory usage\n{json.dumps(prompt_memory_usage, ensure_ascii=False, default=str)}\n"
        f"{json.dumps(prompt_payload, ensure_ascii=False)}"
        f"{memory_warning}"
    )


def _parse_recent_supervisor_decision_payload(item: object) -> dict | None:
