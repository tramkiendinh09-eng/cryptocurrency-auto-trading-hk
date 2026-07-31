"""
LLM预算控制模块

实现LLM调用频率限制，包括：
- 单品种每日限制
- 单品种滚动窗口限制
- 全局每日限制

支持预算状态持久化和消费记录。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _parse_datetime(value: Any) -> datetime | None:
    """解析日期时间值

    Args:
        value: 日期时间值

    Returns:
        datetime | None: 解析后的datetime对象
    """
    if isinstance(value, datetime):
        parsed = value
    else:
        normalized = str(value or "").strip()
        if not normalized:
            return None
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_limit(value: Any) -> int | None:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized > 0 else None


def _prune_entries(entries: Any, cutoff: datetime) -> list[str]:
    if not isinstance(entries, list):
        return []
    normalized: list[str] = []
    for item in entries:
        parsed = _parse_datetime(item)
        if parsed is None or parsed < cutoff:
            continue
        normalized.append(parsed.isoformat())
    return normalized


def evaluate_llm_budget(
    *,
    symbol: str,
    llm_budget_policy: dict[str, Any] | None,
    budget_state: dict[str, Any] | None,
    now: Any = None,
    consume: bool = False,
    bypass: bool = False,
) -> dict[str, Any]:
    """评估LLM预算

    检查是否超出LLM调用限制，并可选地消费一次调用。

    Args:
        symbol: 交易品种
        llm_budget_policy: LLM预算策略
        budget_state: 预算状态
        now: 当前时间
        consume: 是否消费一次调用
        bypass: 是否绕过限制

    Returns:
        dict[str, Any]: 评估结果，包含allowed、blocked、usage、state字段
    """
    now_dt = _parse_datetime(now) or datetime.now(timezone.utc)
    policy = llm_budget_policy if isinstance(llm_budget_policy, dict) else {}
    state = budget_state if isinstance(budget_state, dict) else {}

    symbol_dispatches = state.get("symbol_dispatches")
    if not isinstance(symbol_dispatches, dict):
        symbol_dispatches = {}

    daily_cutoff = now_dt - timedelta(days=1)
    # 支持 rollingWindowMinutes (分钟) 和 windowSeconds (秒) 两种配置
    window_minutes = _normalize_limit(policy.get("rollingWindowMinutes"))
    window_seconds = _normalize_limit(policy.get("windowSeconds") or policy.get("window_seconds"))
    if window_minutes is not None:
        window_seconds = window_minutes * 60
    elif window_seconds is None:
        window_seconds = 3600
    window_cutoff = now_dt - timedelta(seconds=window_seconds)

    normalized_symbol_dispatches = {
        str(key): _prune_entries(value, daily_cutoff)
        for key, value in symbol_dispatches.items()
    }
    normalized_global_dispatches = _prune_entries(state.get("global_dispatches"), daily_cutoff)
    symbol_entries = normalized_symbol_dispatches.get(symbol, [])
    symbol_window_entries = [item for item in symbol_entries if (_parse_datetime(item) or now_dt) >= window_cutoff]

    usage = {
        "per_symbol_daily": len(symbol_entries),
        "per_symbol_window": len(symbol_window_entries),
        "global_daily": len(normalized_global_dispatches),
    }
    next_state = {
        "symbol_dispatches": dict(normalized_symbol_dispatches),
        "global_dispatches": list(normalized_global_dispatches),
    }

    if bypass:
        return {
            "allowed": True,
            "blocked": False,
            "reason_code": "bypass",
            "usage": usage,
            "state": next_state,
        }

    per_symbol_daily_limit = _normalize_limit(
        policy.get("perSymbolDailyLimit") or policy.get("per_symbol_daily_limit")
    )
    # 支持 rollingWindowLimit 和 perSymbolWindowLimit 两种配置
    per_symbol_window_limit = _normalize_limit(
        policy.get("rollingWindowLimit") or policy.get("perSymbolWindowLimit") or policy.get("per_symbol_window_limit")
    )
    global_daily_limit = _normalize_limit(
        policy.get("globalDailyLimit") or policy.get("global_daily_limit")
    )

    reason_code = ""
    if per_symbol_window_limit is not None and usage["per_symbol_window"] >= per_symbol_window_limit:
        reason_code = "per_symbol_window_limit_exhausted"
    elif per_symbol_daily_limit is not None and usage["per_symbol_daily"] >= per_symbol_daily_limit:
        reason_code = "per_symbol_daily_limit_exhausted"
    elif global_daily_limit is not None and usage["global_daily"] >= global_daily_limit:
        reason_code = "global_daily_limit_exhausted"

    blocked = bool(reason_code)
    if not blocked and consume:
        current_timestamp = now_dt.isoformat()
        updated_symbol_entries = list(symbol_entries)
        updated_symbol_entries.append(current_timestamp)
        updated_global_dispatches = list(normalized_global_dispatches)
        updated_global_dispatches.append(current_timestamp)
        next_state["symbol_dispatches"][symbol] = updated_symbol_entries
        next_state["global_dispatches"] = updated_global_dispatches
        usage = {
            "per_symbol_daily": len(updated_symbol_entries),
            "per_symbol_window": len(
                [item for item in updated_symbol_entries if (_parse_datetime(item) or now_dt) >= window_cutoff]
            ),
            "global_daily": len(updated_global_dispatches),
        }

    return {
        "allowed": not blocked,
        "blocked": blocked,
        "reason_code": reason_code,
        "usage": usage,
        "state": next_state,
    }
