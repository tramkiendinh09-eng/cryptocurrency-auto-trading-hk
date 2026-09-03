"""
主管Agent节点模块 - 交易决策的最终决策者

实现交易决策的主管节点，负责汇总各专业Agent的观点并做出最终决策。

主管Agent的角色:
- 作为决策流程的"最终决策者"
- 汇总市场、新闻、链上、社交四个专业Agent的观点
- 调用LLM生成结构化决策
- 处理AI调用失败情况(fail-open或fail-closed)

决策输出结构(SupervisorDecision):
- action: 动作类型
  - OPEN_LONG: 开多仓
  - OPEN_SHORT: 开空仓
  - ADD_LONG: 加多仓
  - ADD_SHORT: 加空仓
  - REDUCE: 减仓
  - CLOSE: 平仓
  - HOLD: 持有当前仓位
  - SKIP: 跳过，不操作
- side: 方向(long/short/flat)
- confidence: 信心度(0-100)
- size_hint: 仓位大小建议(0-1，相对于账户权益)
- leverage_hint: 杠杆建议
- holding_window: 预期持仓时间窗口
- invalidation: 失效条件
- summary_reason: 决策原因摘要

工作流程:
```
1. 检查是否允许LLM分发
       │
       ▼
2. 解析AI模型配置和提示模板
       │
       ▼
3. 构建主管提示(包含所有Agent观点)
       │
       ▼
4. 调用LLM生成决策
       │
       ├─► 成功: 解析并规范化决策
       │
       └─► 失败:
              ├─► fail-closed: 返回SKIP决策
              └─► fail-open: 根据Agent观点投票生成决策
```

仓位状态处理:
- flat(无仓位): 只能OPEN或SKIP
- long(多仓): 可以HOLD、ADD_LONG、REDUCE、CLOSE
- short(空仓): 可以HOLD、ADD_SHORT、REDUCE、CLOSE
"""

import json
import math
import os
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from trade_runtime.decision.agent_profile_resolver import resolve_agent_execution_config
from trade_runtime.decision.dispatch import (
    build_suppression_reason_codes,
    derive_dispatch_mode,
    llm_dispatch_allowed,
    resolve_active_specialists,
)
from trade_runtime.decision.llm_agent_runner import record_llm_error
from trade_runtime.decision.models import SupervisorDecision
from trade_runtime.decision.sizing import (
    DEFAULT_LEVERAGE,
    MIN_LEVERAGE,
    leverage_ceiling,
    min_viable_size_hint,
    venue_order_floor,
)
from trade_runtime.decision.output_parsers import parse_json_object_content
from trade_runtime.decision.state import DecisionState
from trade_runtime.decision.timestamps import stamp_state_timestamp
from trade_runtime.prompting.prompt_template_registry import resolve_prompt_template_registry
from trade_runtime.prompting.render_context_builder import (
    build_prompt_long_term_memory,
    build_prompt_memory_usage,
    build_prompt_short_term_memory,
    build_prompt_strategy_context,
    build_supervisor_render_context,
    resolve_current_position_holding_minutes,
    resolve_prompt_current_time,
    synchronize_prompt_memory_state,
)
from trade_runtime.prompting.renderers import render_template

_RECENT_SUPERVISOR_DECISION_LIMIT = 2
_RECENT_SUPERVISOR_DECISION_TTL_SECONDS = 7200
_RECENT_SUPERVISOR_DECISION_DATABASE_TZ = ZoneInfo("Asia/Shanghai")
_RECENT_SUPERVISOR_DECISION_FETCH_CAP = 30


def _is_enabled_flag(value: object, default: bool = True) -> bool:
    """检查是否为启用标志

    Args:
        value: 标志值
        default: 默认值

    Returns:
        bool: 是否启用
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "disabled"}:
        return False
    return default


def _resolve_ai_model_config(state: DecisionState) -> dict:
    strategy_context = state.get("strategy_context") or {}
    if not isinstance(strategy_context, dict):
        return {}
    ai_model_config = strategy_context.get("ai_model_config") or {}
    return ai_model_config if isinstance(ai_model_config, dict) else {}


def _is_ai_model_available(ai_model_config: dict, model_id: int | None = None) -> bool:
    if model_id is not None:
        return True
    if not ai_model_config:
        return True
    model_identifier = str(ai_model_config.get("model_code") or ai_model_config.get("model_key") or "").strip()
    if not model_identifier:
        return False
    return _is_enabled_flag(ai_model_config.get("is_enabled"), default=True)



_SUPERVISOR_POLICY_MODES = {"EVENT_GATED", "RULE_ONLY", "LLM_ALLOWED", "NO_DISPATCH"}


def _resolve_supervisor_policy_mode(state: DecisionState) -> str:
    policy = state.get("supervisor_policy")
    if not isinstance(policy, dict):
        strategy_context = state.get("strategy_context") or {}
        if isinstance(strategy_context, dict):
            policy = strategy_context.get("supervisor_policy") or strategy_context.get("supervisorPolicy")
    if not isinstance(policy, dict):
        policy = {}
    normalized = str(
        policy.get("enabledWhen")
        or policy.get("enabled_when")
        or policy.get("mode")
        or ""
    ).strip().upper()
    return normalized if normalized in _SUPERVISOR_POLICY_MODES else "LLM_ALLOWED"


def _supervisor_stage_enabled(state: DecisionState) -> bool:
    policy_mode = _resolve_supervisor_policy_mode(state)
    dispatch_mode = derive_dispatch_mode(state)
    if policy_mode == "NO_DISPATCH" or dispatch_mode == "NO_DISPATCH":
        return False
    if policy_mode == "LLM_ALLOWED":
        return llm_dispatch_allowed(state)
    return dispatch_mode in {"RULE_ONLY", "LLM_ALLOWED"}


def _build_model_unavailable_decision(ai_model_config: dict) -> SupervisorDecision:
    return SupervisorDecision(
        action="SKIP",
        side="flat",
        confidence=0,
        size_hint=0.0,
        summary_reason="ai_model_unavailable",
        model_code=str(ai_model_config.get("model_code") or "").strip(),
        model_provider=str(ai_model_config.get("provider") or "").strip(),
    )


def _resolved_model_code(ai_model_config: dict, prompt_metadata: dict | None = None) -> str:
    metadata = prompt_metadata or {}
    return str(metadata.get("model_code") or ai_model_config.get("model_code") or "").strip()


def _resolved_model_provider(ai_model_config: dict, prompt_metadata: dict | None = None) -> str:
    metadata = prompt_metadata or {}
    return str(metadata.get("model_provider") or ai_model_config.get("provider") or "").strip()


def _build_ai_fail_closed_decision(
    ai_model_config: dict,
    prompt_metadata: dict | None = None,
) -> SupervisorDecision:
    return SupervisorDecision(
        action="SKIP",
        side="flat",
        confidence=0,
        size_hint=0.0,
        summary_reason="ai_model_call_failed_fail_closed",
        model_code=_resolved_model_code(ai_model_config, prompt_metadata),
        model_provider=_resolved_model_provider(ai_model_config, prompt_metadata),
    )


def _supervisor_ai_fail_open_enabled(state: DecisionState) -> bool:
    runtime_config = state.get("runtime_config") or {}
    if not isinstance(runtime_config, dict):
        return False
    effective_mode = str(state.get("effective_mode") or state.get("mode") or "").strip().lower()
    if effective_mode not in {"paper", "shadow", ""}:
        return False
    runtime_flags = runtime_config.get("runtime_flags")
    if not isinstance(runtime_flags, dict):
        runtime_flags = {}
    runtime_flags_json = runtime_config.get("runtime_flags_json") or runtime_config.get("runtimeFlagsJson")
    if isinstance(runtime_flags_json, str) and runtime_flags_json.strip():
        try:
            parsed_runtime_flags = json.loads(runtime_flags_json)
        except json.JSONDecodeError:
            parsed_runtime_flags = {}
        if isinstance(parsed_runtime_flags, dict):
            runtime_flags = {**parsed_runtime_flags, **runtime_flags}
    for flag_value in (
        runtime_config.get("supervisor_ai_fail_open"),
        runtime_config.get("supervisorAiFailOpen"),
        runtime_flags.get("supervisorAiFailOpen"),
        runtime_flags.get("supervisor_ai_fail_open"),
    ):
        if flag_value is not None:
            return _is_enabled_flag(flag_value, default=False)
    return False


def _collect_views(state: DecisionState) -> list[dict]:
    return [
        state.get("market_view", {}),
        state.get("news_view", {}),
        state.get("onchain_view", {}),
        state.get("social_view", {}),
    ]


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _has_active_position(state: DecisionState) -> bool:
    return float(state.get("current_position_quantity", 0.0) or 0.0) > 0


def _max_position_ratio(state: DecisionState) -> float:
    runtime_config = state.get("runtime_config") or {}
    if not isinstance(runtime_config, dict):
        return 1.0
    return max(0.0, min(1.0, _safe_float(runtime_config.get("max_position_ratio"), 1.0)))


def _remaining_position_headroom(state: DecisionState) -> float:
    account_equity = _safe_float(state.get("account_equity"), 0.0)
    if account_equity <= 0:
        return 0.0
    current_position_notional = max(0.0, _safe_float(state.get("current_position_notional"), 0.0))
    return max(0.0, _max_position_ratio(state) - (current_position_notional / account_equity))


def _clamp_size_hint(state: DecisionState, decision_payload: dict) -> dict:
    payload = dict(decision_payload or {})
    action = str(payload.get("action") or "").strip().upper()
    side = str(payload.get("side") or "").strip().lower()
    size_hint = max(0.0, _safe_float(payload.get("size_hint"), 0.0))
    if action in {"OPEN_LONG", "OPEN_SHORT"}:
        payload["size_hint"] = min(size_hint, _max_position_ratio(state))
        return payload
    if action in {"ADD_LONG", "ADD_SHORT"}:
        payload["size_hint"] = min(size_hint, _remaining_position_headroom(state))
        if payload["size_hint"] <= 0:
            payload["action"] = "HOLD"
            payload["side"] = side or ("long" if action == "ADD_LONG" else "short")
        return payload
    if action == "CLOSE":
        payload["size_hint"] = 1.0
        return payload
    payload["size_hint"] = min(size_hint, 1.0)
    return payload



def _normalize_position_side(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"long", "buy", "bullish"}:
        return "long"
    if normalized in {"short", "sell", "bearish"}:
        return "short"
    if normalized in {"flat", "hold", "skip", "none", "no_action", "neutral", ""}:
        return "flat"
    return normalized


def _current_position_side(state: DecisionState) -> str:
    side = _normalize_position_side(state.get("current_position_side", "flat"))
    return side if side in {"long", "short"} and _has_active_position(state) else "flat"


def _target_action_side(action: str, side: str) -> str:
    if action.endswith("_LONG"):
        return "long"
    if action.endswith("_SHORT"):
        return "short"
    return side if side in {"long", "short"} else "flat"


def _open_action_for_side(side: str) -> str:
    if side == "short":
        return "OPEN_SHORT"
    return "OPEN_LONG" if side == "long" else "SKIP"


def _add_action_for_side(side: str) -> str:
    if side == "short":
        return "ADD_SHORT"
    return "ADD_LONG" if side == "long" else "HOLD"


def _first_number(value: object, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
    if match is None:
        return default
    try:
        return float(match.group(0))
    except (TypeError, ValueError):
        return default


def _extract_numeric_level(value: object) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
    if match is None:
        return None
    try:
        return float(match.group(0))
    except (TypeError, ValueError):
        return None


def _numeric_size_hint(value: object) -> float:
    if value in (None, "") or isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if 0.0 <= numeric <= 1.0 else 0.0
    for match in re.finditer(r"[-+]?\d+(?:\.\d+)?", str(value)):
        try:
            numeric = float(match.group(0))
        except (TypeError, ValueError):
            continue
        if 0.0 <= numeric <= 1.0:
            return numeric
    return 0.0


def _numeric_leverage_hint(value: object) -> int:
    return max(0, int(_first_number(value, 3.0)))


def _is_placeholder_text(value: object, *, zero_is_placeholder: bool = False) -> bool:
    normalized = str(value or "").strip().lower().replace("\\", "/")
    if normalized in {"", "n/a", "na", "none", "null", "nil", "-", "--", "unknown"}:
        return True
    if zero_is_placeholder and normalized in {"0", "0m", "0h", "0d"}:
        return True
    return False


def _normalize_holding_window(value: object) -> str:
    normalized = str(value or "").strip()
    if _is_placeholder_text(normalized, zero_is_placeholder=True):
        return "15m-4h"
    return normalized


def _normalize_invalidation(value: object, *, action: str) -> str:
    normalized = str(value or "").strip()
    if not _is_placeholder_text(normalized):
        return normalized
    if action in {"HOLD", "SKIP"}:
        return "no_trade_condition"
    return "model_not_provided"


def _normalize_model_decision_payload(state: DecisionState, decision_payload: dict) -> dict:
    payload = dict(decision_payload or {})
    raw_action = str(payload.get("action") or "").strip()
    action_key = raw_action.lower().replace("-", "_").replace(" ", "_")
    side = _normalize_position_side(payload.get("side"))
    current_side = _current_position_side(state)
    has_position = current_side in {"long", "short"}

    canonical_actions = {
        "OPEN_LONG",
        "OPEN_SHORT",
        "ADD_LONG",
        "ADD_SHORT",
        "REDUCE",
        "CLOSE",
        "HOLD",
        "SKIP",
        "NO_ACTION",
        "BLOCKED",
    }
    action = raw_action.upper() if raw_action.upper() in canonical_actions else ""

    if action_key in {"close_long", "close_short", "reduce_long", "reduce_short"}:
        side = "long" if action_key.endswith("_long") else "short"
        action = "CLOSE" if action_key.startswith("close") else "REDUCE"
    elif not action:
        if action_key in {"hold", "wait", "observe", "no_action", "none", "skip"}:
            action = "HOLD" if has_position else "SKIP"
        elif action_key in {"close", "exit", "liquidate"}:
            action = "CLOSE" if has_position else "SKIP"
        elif action_key in {"reduce", "trim", "decrease"}:
            action = "REDUCE" if has_position else "SKIP"
        elif action_key == "adjust":
            if has_position and side in {"long", "short"} and side != current_side:
                action = "REDUCE"
            elif has_position:
                action = "HOLD"
            else:
                action = _open_action_for_side(side)
        elif action_key in {"increase", "add", "scale_in"}:
            if has_position and side == current_side:
                action = "HOLD"
            elif has_position and side in {"long", "short"}:
                action = "CLOSE"
            else:
                action = _open_action_for_side(side)
        elif action_key in {"enter", "open", "buy", "sell", "long", "short"}:
            if action_key in {"buy", "long"}:
                side = "long"
            if action_key in {"sell", "short"}:
                side = "short"
            if has_position and side == current_side:
                action = "HOLD"
            elif has_position and side in {"long", "short"}:
                action = "CLOSE"
            else:
                action = _open_action_for_side(side)
        else:
            action = "HOLD" if has_position else "SKIP"

    if action == "NO_ACTION":
        action = "HOLD" if has_position else "SKIP"
    if action == "BLOCKED":
        action = "SKIP"

    if action in {"OPEN_LONG", "OPEN_SHORT"}:
        target_side = _target_action_side(action, side)
        if has_position and target_side == current_side:
            action = "HOLD"
            side = current_side
        elif has_position and target_side in {"long", "short"}:
            action = "CLOSE"
            side = current_side
        else:
            side = target_side
    elif action in {"ADD_LONG", "ADD_SHORT"}:
        target_side = _target_action_side(action, side)
        if has_position and target_side == current_side:
            side = target_side
        elif has_position and target_side in {"long", "short"}:
            action = "CLOSE"
            side = current_side
        else:
            action = _open_action_for_side(target_side)
            side = target_side
    elif action in {"REDUCE", "CLOSE"}:
        if has_position:
            side = current_side
        else:
            action = "SKIP"
            side = "flat"
    elif action == "HOLD":
        side = current_side if has_position else side if side in {"long", "short"} else "flat"
    else:
        action = "SKIP"
        side = "flat"

    payload["action"] = action
    payload["side"] = side
    payload["confidence"] = int(_first_number(payload.get("confidence"), 0.0))
    payload["leverage_hint"] = _numeric_leverage_hint(payload.get("leverage_hint", 3))
    payload["size_hint"] = _numeric_size_hint(payload.get("size_hint"))
    if action in {"HOLD", "SKIP"}:
        payload["size_hint"] = 0.0
    elif action == "CLOSE":
        payload["size_hint"] = 1.0
    elif action == "REDUCE" and payload.get("size_hint") in (None, ""):
        payload["size_hint"] = 0.5
    return payload


def _current_market_price(state: DecisionState) -> float:
    feature_snapshot = state.get("feature_snapshot") or {}
    if isinstance(feature_snapshot, dict):
        position_context = feature_snapshot.get("position_risk_context") or {}
        if isinstance(position_context, dict):
            current_price = _safe_float(position_context.get("current_price"), 0.0)
            if current_price > 0:
                return current_price
        for key in ("effective_price", "latest_price", "price"):
            current_price = _safe_float(feature_snapshot.get(key), 0.0)
            if current_price > 0:
                return current_price
    events = state.get("event_bundle")
    if isinstance(events, list):
        for event in reversed(events):
            if not isinstance(event, dict):
                continue
            current_price = _safe_float(event.get("effective_price") or event.get("price"), 0.0)
            if current_price > 0:
                return current_price
    return 0.0


def _has_opposing_consensus(state: DecisionState, position_side: str) -> bool:
    views = [view for view in _collect_views(state) if isinstance(view, dict)]
    bullish_views = [view for view in views if str(view.get("bias") or "").strip().lower() == "bullish"]
    bearish_views = [view for view in views if str(view.get("bias") or "").strip().lower() == "bearish"]
    if position_side == "long":
        opposing_views = bearish_views
        aligned_views = bullish_views
    elif position_side == "short":
        opposing_views = bullish_views
        aligned_views = bearish_views
    else:
        return False
    opposing_score = sum(int(view.get("confidence", 0) or 0) for view in opposing_views)
    aligned_score = sum(int(view.get("confidence", 0) or 0) for view in aligned_views)
    return len(opposing_views) >= 2 and opposing_score > aligned_score


def _invalidation_breached(state: DecisionState, *, position_side: str, invalidation: object) -> bool:
    invalidation_text = str(invalidation or "").strip()
    if _is_placeholder_text(invalidation_text):
        return False
    invalidation_level = _extract_numeric_level(invalidation_text)
    current_price = _current_market_price(state)
    if invalidation_level is None or current_price <= 0:
        return False
    normalized = invalidation_text.lower()
    if position_side == "long":
        downward_tokens = ("below", "under", "break below", "lose", "lost", "跌破", "失守")
        return any(token in normalized for token in downward_tokens) and current_price <= invalidation_level
    if position_side == "short":
        upward_tokens = ("above", "over", "break above", "breakout above", "突破", "站上")
        return any(token in normalized for token in upward_tokens) and current_price >= invalidation_level
    return False


def _apply_exit_escalation(state: DecisionState, decision_payload: dict) -> dict:
    payload = dict(decision_payload or {})
    current_side = _current_position_side(state)
    action = str(payload.get("action") or "").strip().upper()
    if action != "REDUCE" or current_side not in {"long", "short"}:
        state.pop("supervisor_exit_escalation", None)
        return payload

    position_risk_result = state.get("position_risk_result") or {}
    risk_severity = str(position_risk_result.get("severity") or "").strip().lower()
    risk_reason = str(position_risk_result.get("reason") or "").strip().lower()
    opposing_consensus = _has_opposing_consensus(state, current_side)
    escalation_reason = ""
    if risk_severity == "close":
        escalation_reason = "position_risk_close"
    elif opposing_consensus and _invalidation_breached(
        state,
        position_side=current_side,
        invalidation=payload.get("invalidation"),
    ):
        escalation_reason = "invalidation_breached"
    elif opposing_consensus and risk_reason == "structure_reversal":
        escalation_reason = "structure_reversal"

    if not escalation_reason:
        state.pop("supervisor_exit_escalation", None)
        return payload

    payload["action"] = "CLOSE"
    payload["side"] = current_side
    payload["size_hint"] = 1.0
    summary_reason = str(payload.get("summary_reason") or "").strip()
    payload["summary_reason"] = (
        f"{summary_reason}; escalated_close:{escalation_reason}"
        if summary_reason
        else f"escalated_close:{escalation_reason}"
    )
    state["supervisor_exit_escalation"] = {"action": "CLOSE", "reason": escalation_reason}
    return payload

def _ordered_specialist_views(state: DecisionState) -> list[tuple[str, dict]]:
    views_by_agent = {
        "market_agent": state.get("market_view"),
        "news_agent": state.get("news_view"),
        "social_agent": state.get("social_view"),
        "onchain_agent": state.get("onchain_view"),
    }
    default_order = {
        "market_agent": 1_000,
        "news_agent": 1_001,
        "social_agent": 1_002,
        "onchain_agent": 1_003,
    }
    ranked: dict[str, int] = {}
    agent_profiles = state.get("agent_profiles")
    if isinstance(agent_profiles, list):
        for profile in agent_profiles:
            if not isinstance(profile, dict):
                continue
            agent_code = str(profile.get("agent_code") or "").strip().lower()
            if agent_code not in views_by_agent:
                continue
            try:
                ranked[agent_code] = int(profile.get("speak_order") or default_order[agent_code])
            except (TypeError, ValueError):
                ranked[agent_code] = default_order[agent_code]
    return sorted(views_by_agent.items(), key=lambda item: ranked.get(item[0], default_order[item[0]]))


def _specialist_handoff_messages(state: DecisionState) -> list[dict]:
    messages = state.get("agent_messages")
    active_specialists = set(resolve_active_specialists(state))
    specialist_agent_codes = {"market_agent", "news_agent", "onchain_agent", "social_agent"}
    existing_messages = [
        item
        for item in (messages if isinstance(messages, list) else [])
        if isinstance(item, dict)
        and (
            str(item.get("speaker_agent") or "").strip().lower() not in specialist_agent_codes
            or str(item.get("speaker_agent") or "").strip().lower() in active_specialists
        )
        and (
            str(item.get("target_agent") or "").strip().lower() not in specialist_agent_codes
            or str(item.get("target_agent") or "").strip().lower() in active_specialists
        )
    ]
    existing_speakers = {
        str(item.get("speaker_agent") or "").strip().lower()
        for item in existing_messages
        if isinstance(item, dict)
        and str(item.get("speaker_agent") or "").strip().lower() in specialist_agent_codes
    }
    handoff_messages: list[dict] = []
    for agent_code, view in _ordered_specialist_views(state):
        if agent_code not in active_specialists:
            continue
        if agent_code in existing_speakers:
            continue
        if not isinstance(view, dict) or not view:
            continue
        content_payload = dict(view)
        content_payload.setdefault("agent_code", agent_code)
        handoff_messages.append(
            {
                "round_no": 0,
                "speaker_agent": agent_code,
                "target_agent": "supervisor_agent",
                "message_type": "conclusion",
                "template_code": str(view.get("template_code") or "").strip(),
                "model_code": str(view.get("model_code") or "").strip(),
                "content": content_payload,
                "summary_text": str(view.get("reason") or "").strip(),
            }
        )
    return existing_messages + handoff_messages


def _market_evidence(state: DecisionState) -> dict:
    """Market blocks the supervisor prompt explicitly asks the model to use.

    Sourced from build_supervisor_render_context so the fallback prompt and the
    template path describe the same market.
    """
    try:
        context = build_supervisor_render_context(state)
    except Exception:
        return {}
    if not isinstance(context, dict):
        return {}
    # The builder hands the market bundle over as a JSON *string* under
    # market_context_json; kline_context and derivatives_context live inside it,
    # not at the top level.
    raw = context.get("market_context_json")
    bundle = raw
    if isinstance(raw, str):
        try:
            bundle = json.loads(raw)
        except (TypeError, ValueError):
            return {}
    if not isinstance(bundle, dict):
        return {}
    evidence = {}
    for key in (
        "kline_context",
        "derivatives_context",
        "liquidation_context",
        "wyckoff_shortterm",
        "volume_price_signals",
        "period_summaries",
        "trade_tick_status",
        "market_tick_staleness_seconds",
    ):
        value = bundle.get(key)
        if value not in (None, {}, [], ""):
            evidence[key] = value
    status = context.get("market_source_status")
    if status:
        evidence["market_source_status"] = status
    return evidence


# 交易所对单笔委托的最小名义价值。币安 U 本位合约多数交易对是 5 USDT，
# 个别是 20。给不出准确值时宁可取大：报小了会让模型开出必然被拒的单子。
_MIN_ORDER_NOTIONAL_USDT = float(
    os.getenv("TRADE_RUNTIME_MIN_ORDER_NOTIONAL_USDT", "5") or 5
)


def _sizing_constraints(state: DecisionState, runtime_config: dict) -> dict:
    """算出这一刻、这个标的真正可下的仓位区间。

    口径与 decision/sizing.py 完全一致（同一份实现），否则模型会按一个
    区间给值、风控和下单却按另一个算，出现"照着提示给的数反而被拒"。

    杠杆在这里是有用的：size_hint 是动用多少权益作为保证金，敞口是它乘
    杠杆，所以杠杆越高、能满足交易所最小下单额的 size_hint 下界越低。

    最小下单额必须按标的取。此前这里用的是一个全局常量 5 USDT，而实测
    ETH 的真实下限是 21.6——模型照着 5 给 ETH 定了 10 和 15 USDT 两单，
    建好、发出、被交易所过滤器静默拒掉，两次有效信号就这么没了。
    """
    equity = _safe_float(state.get("account_equity"), 0.0)
    max_ratio = _safe_float(runtime_config.get("max_position_ratio"), 0.0)
    ceiling = leverage_ceiling(runtime_config)
    default_leverage = min(DEFAULT_LEVERAGE, ceiling)
    floor_leverage = min(MIN_LEVERAGE, ceiling)

    price = _current_market_price(state)
    min_notional, notional_step, notional_source = venue_order_floor(
        state.get("symbol") or "",
        price,
        _MIN_ORDER_NOTIONAL_USDT,
    )

    # 下界按默认杠杆给：模型可以自己抬到 ceiling，那只会让下界更低。
    min_size_hint = min_viable_size_hint(equity, default_leverage, min_notional)
    floor_at_max_leverage = min_viable_size_hint(equity, ceiling, min_notional)

    tradeable = (
        floor_at_max_leverage is not None
        and max_ratio > 0
        and floor_at_max_leverage <= max_ratio
    )
    return {
        "account_equity": equity,
        "order_notional_formula": "account_equity * size_hint * leverage",
        "margin_formula": "account_equity * size_hint",
        "leverage_scales_exposure": True,
        "default_leverage": int(default_leverage),
        # 低于这个倍数的 leverage_hint 会被抬上来，所以直接告诉模型区间，
        # 免得它给出一个会被悄悄改掉的值。
        "min_leverage": int(floor_leverage),
        "max_leverage": int(ceiling),
        "min_order_notional_usdt": round(min_notional, 4),
        # 这个下限是这个标的自己的，不是全局值——各标的能差四倍以上。
        "min_order_notional_symbol": state.get("symbol") or None,
        "min_order_notional_source": notional_source,
        # 成交数量按步进向下截断，所以下单额落在步进整数倍上才不浪费保证金。
        "notional_step_usdt": round(notional_step, 4) if notional_step > 0 else None,
        "min_viable_size_hint": min_size_hint,
        "min_viable_size_hint_at_max_leverage": floor_at_max_leverage,
        "max_size_hint": max_ratio or None,
        "any_size_tradeable": bool(tradeable),
    }


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
        "size_hint must be a plain numeric account-equity ratio from 0 to 1, for example 0.02; "
        "do not include BTC, USDT, percent signs, units, ranges, or explanatory text in size_hint. "
        "leverage_hint must be a plain integer, for example 2; "
        "do not include x, ranges, or explanatory text in leverage_hint. "
        "Read sizing_constraints before choosing size_hint and leverage_hint. "
        "size_hint is the fraction of account equity committed as margin; exposure is "
        "account_equity * size_hint * leverage_hint, so leverage does increase position "
        "size. size_hint must be either 0 (with SKIP or HOLD) or at most max_size_hint, "
        "which caps margin, not exposure. Exposure must also clear the exchange minimum "
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
    if not isinstance(item, dict):
        return None
    for key in ("contentJson", "content_json", "content"):
        value = item.get(key)
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, str):
            payload = parse_json_object_content(value)
            if isinstance(payload, dict):
                return payload
    if item.get("action") is not None:
        return dict(item)
    return None


def _parse_recent_supervisor_decision_timestamp(
    value: object,
    *,
    default_timezone: timezone | ZoneInfo = timezone.utc,
) -> datetime | None:
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
        return parsed.replace(tzinfo=default_timezone)
    return parsed


def _resolve_recent_supervisor_decision_ttl_seconds(state: DecisionState) -> int:
    short_term_memory = state.get("short_term_memory") or {}
    if not isinstance(short_term_memory, dict):
        return _RECENT_SUPERVISOR_DECISION_TTL_SECONDS
    bucket = short_term_memory.get("supervisor_decision") or {}
    if isinstance(bucket, dict):
        try:
            return max(int(float(bucket.get("window_seconds"))), 1)
        except (TypeError, ValueError):
            pass
    ttl_policy = short_term_memory.get("ttl_policy") or {}
    if isinstance(ttl_policy, dict):
        try:
            return max(int(float(ttl_policy.get("supervisor_decision"))), 1)
        except (TypeError, ValueError):
            pass
    return _RECENT_SUPERVISOR_DECISION_TTL_SECONDS


def _is_recent_supervisor_decision_item_fresh(
    item: dict,
    *,
    current_time: datetime | None,
    ttl_seconds: int | None,
) -> bool:
    if current_time is None or ttl_seconds is None or ttl_seconds <= 0:
        return True
    observed_at = _parse_recent_supervisor_decision_timestamp(
        item.get("createdAt") or item.get("created_at") or item.get("timestamp") or item.get("event_time"),
        default_timezone=_RECENT_SUPERVISOR_DECISION_DATABASE_TZ,
    )
    if observed_at is None:
        return True
    age_seconds = (current_time - observed_at).total_seconds()
    return 0 <= age_seconds <= ttl_seconds


def _normalize_recent_supervisor_decisions(
    items: object,
    *,
    limit: int = _RECENT_SUPERVISOR_DECISION_LIMIT,
    exclude_trace_id: str = "",
    current_time: datetime | None = None,
    ttl_seconds: int | None = None,
    enforce_freshness: bool = True,
    state: DecisionState | None = None,
) -> list[dict]:
    if not isinstance(items, list):
        return []
    normalized: list[dict] = []
    normalized_exclude_trace_id = str(exclude_trace_id or "").strip()
    for item in items:
        if not isinstance(item, dict):
            continue
        item_trace_id = str(item.get("traceId") or item.get("trace_id") or item.get("traceId") or "").strip()
        if normalized_exclude_trace_id and item_trace_id == normalized_exclude_trace_id:
            continue
        if enforce_freshness and not _is_recent_supervisor_decision_item_fresh(
            item,
            current_time=current_time,
            ttl_seconds=ttl_seconds,
        ):
            continue
        payload = _parse_recent_supervisor_decision_payload(item)
        if not isinstance(payload, dict) or not payload:
            continue
        canonical = _canonicalize_recent_supervisor_decision_payload(state, payload)
        # Skip SKIP/HOLD decisions with no meaningful content (RULE_ONLY fallback)
        action = canonical.get("action", "")
        if action in {"SKIP", "HOLD"} and not canonical.get("summary_reason") and canonical.get("confidence", 0) == 0:
            continue
        # Keep other decisions (OPEN_*, CLOSE, ADD_*, REDUCE) even if no summary_reason
        normalized.append(canonical)
        if len(normalized) >= max(int(limit or 0), 1):
            break
    return normalized


def _canonicalize_recent_supervisor_decision_payload(
    state: DecisionState | None,
    payload: dict,
) -> dict:
    normalized_input = dict(payload or {})
    if normalized_input.get("leverage_hint") in (None, ""):
        normalized_input["leverage_hint"] = 1
    normalized = _normalize_model_decision_payload(state or {}, normalized_input)
    action = str(normalized.get("action") or "SKIP").strip().upper() or "SKIP"
    summary_reason = str(payload.get("summary_reason") or normalized.get("summary_reason") or "").strip()

    # 从 action 推断 side（如果 payload 中没有 side）
    side = str(normalized.get("side") or "").strip()
    if not side or side == "flat":
        if "LONG" in action:
            side = "long"
        elif "SHORT" in action:
            side = "short"
        else:
            side = "flat"

    result = {
        "action": action,
        "side": side,
        "confidence": int(normalized.get("confidence") or 0),
        "size_hint": float(normalized.get("size_hint") or 0.0),
        "leverage_hint": int(normalized.get("leverage_hint") or 1),
        "holding_window": _normalize_holding_window(payload.get("holding_window")),
        "invalidation": _normalize_invalidation(payload.get("invalidation"), action=action),
        "summary_reason": summary_reason,
    }
    for extra_key in ("model_code", "model_provider"):
        extra_value = str(payload.get(extra_key) or "").strip()
        if extra_value:
            result[extra_key] = extra_value
    return result


def _recent_supervisor_decisions_from_short_term_memory(
    state: DecisionState,
    *,
    limit: int = _RECENT_SUPERVISOR_DECISION_LIMIT,
) -> list[dict]:
    short_term_memory = state.get("short_term_memory") or {}
    if not isinstance(short_term_memory, dict):
        return []
    bucket = short_term_memory.get("supervisor_decision") or {}
    if not isinstance(bucket, dict):
        return []
    items = bucket.get("items")
    if not isinstance(items, list):
        return []
    current_time = _parse_recent_supervisor_decision_timestamp(
        resolve_prompt_current_time(state),
        default_timezone=timezone.utc,
    )
    return _normalize_recent_supervisor_decisions(
        list(reversed(items)),
        limit=limit,
        exclude_trace_id=str(state.get("trace_id") or "").strip(),
        current_time=current_time,
        ttl_seconds=_resolve_recent_supervisor_decision_ttl_seconds(state),
        state=state,
    )


def _hydrate_recent_supervisor_decisions(
    state: DecisionState,
    *,
    limit: int = _RECENT_SUPERVISOR_DECISION_LIMIT,
) -> None:
    current_time = _parse_recent_supervisor_decision_timestamp(
        resolve_prompt_current_time(state),
        default_timezone=timezone.utc,
    )
    ttl_seconds = _resolve_recent_supervisor_decision_ttl_seconds(state)
    existing = _normalize_recent_supervisor_decisions(
        state.get("recent_supervisor_decisions"),
        limit=limit,
        current_time=current_time,
        ttl_seconds=ttl_seconds,
        state=state,
    )
    if existing:
        state["recent_supervisor_decisions"] = existing
        return
    callback_client = state.get("callback_client")
    symbol = str(state.get("symbol") or "").strip()
    mode = str(state.get("effective_mode") or state.get("mode") or "").strip()
    trace_id = str(state.get("trace_id") or "").strip()
    if callback_client is not None and symbol and hasattr(callback_client, "get_recent_supervisor_decisions"):
        fetch_limit = min(max(limit * 3, limit + 4), _RECENT_SUPERVISOR_DECISION_FETCH_CAP)
        try:
            recent = callback_client.get_recent_supervisor_decisions(
                symbol,
                mode="",  # 不传递mode参数,避免mode不匹配导致查询不到数据
                limit=limit,
                exclude_trace_id=trace_id,
            )
        except Exception:
            recent = []
        normalized = _normalize_recent_supervisor_decisions(
            recent,
            limit=limit,
            exclude_trace_id=trace_id,
            current_time=current_time,
            ttl_seconds=ttl_seconds,
            enforce_freshness=False,
            state=state,
        )
        normalized_limit = max(int(limit or 0), 1)
        if len(normalized) >= normalized_limit:
            state["recent_supervisor_decisions"] = normalized
            return
        if fetch_limit > limit:
            try:
                recent = callback_client.get_recent_supervisor_decisions(
                    symbol,
                    mode="",
                    limit=fetch_limit,
                    exclude_trace_id=trace_id,
                )
            except Exception:
                recent = []
            normalized = _normalize_recent_supervisor_decisions(
                recent,
                limit=limit,
                exclude_trace_id=trace_id,
                current_time=current_time,
                ttl_seconds=ttl_seconds,
                enforce_freshness=False,
                state=state,
            )
            if normalized:
                state["recent_supervisor_decisions"] = normalized
                return
        if normalized:
            state["recent_supervisor_decisions"] = normalized
            return
    state["recent_supervisor_decisions"] = _recent_supervisor_decisions_from_short_term_memory(
        state,
        limit=limit,
    )


def _resolve_supervisor_prompt_request(state: DecisionState, ai_model_config: dict) -> dict:
    _hydrate_recent_supervisor_decisions(state)
    synchronize_prompt_memory_state(state)
    prompt_config = resolve_agent_execution_config(state, "supervisor_agent", binding_scope="SUPERVISOR")
    metadata = {
        "prompt_source": "inline",
        "binding_scope": "SUPERVISOR",
        "binding_template_code": str((prompt_config or {}).get("template_code") or "").strip(),
        "fallback_template_code": str((prompt_config or {}).get("fallback_template_code") or "").strip(),
        "resolved_template_code": None,
        "output_schema_code": str((prompt_config or {}).get("output_schema_code") or "").strip(),
        "prompt_template_fallback_used": False,
        "model_id": (prompt_config or {}).get("model_id"),
        "model_code": str((prompt_config or {}).get("model_code") or "").strip(),
        "model_provider": str((prompt_config or {}).get("model_provider") or "").strip(),
        "resolution_source": str((prompt_config or {}).get("resolution_source") or "").strip(),
    }
    if prompt_config is None:
        return {
            "prompt": _build_supervisor_prompt(state, ai_model_config),
            "metadata": metadata,
            "model_id": metadata["model_id"],
        }
    registry = resolve_prompt_template_registry(state)
    render_context = build_supervisor_render_context(state)
    template_codes = [
        (str(prompt_config.get("template_code") or "").strip(), False),
        (str(prompt_config.get("fallback_template_code") or "").strip(), True),
    ]
    for template_code, fallback_used in template_codes:
        if not template_code or registry is None:
            continue
        prompt = render_template(registry.get_template(template_code), render_context)
        if prompt:
            metadata["prompt_source"] = "template"
            metadata["resolved_template_code"] = template_code
            metadata["prompt_template_fallback_used"] = fallback_used
            return {
                "prompt": prompt,
                "metadata": metadata,
                "model_id": metadata["model_id"],
            }
    metadata["prompt_template_fallback_used"] = bool(
        metadata["binding_template_code"] or metadata["fallback_template_code"]
    )
    return {
        "prompt": _build_supervisor_prompt(state, ai_model_config),
        "metadata": metadata,
        "model_id": metadata["model_id"],
    }


def _try_model_supervisor_decision(state: DecisionState, ai_model_config: dict, prompt_request: dict) -> dict | None:
    decision_model_client = state.get("decision_model_client")
    model_id = prompt_request.get("model_id")
    if decision_model_client is None or model_id is None:
        return None
    try:
        response = decision_model_client.call_model(
            model_id=model_id,
            prompt=str(prompt_request.get("prompt") or ""),
        )
    except Exception as exc:
        record_llm_error(
            state,
            agent_code="supervisor_agent",
            model_id=model_id,
            template_code=(prompt_request.get("metadata") or {}).get("resolved_template_code")
            or (prompt_request.get("metadata") or {}).get("binding_template_code")
            or "",
            error=exc,
        )
        return None
    if not isinstance(response, dict):
        record_llm_error(
            state,
            agent_code="supervisor_agent",
            model_id=model_id,
            template_code=(prompt_request.get("metadata") or {}).get("resolved_template_code")
            or (prompt_request.get("metadata") or {}).get("binding_template_code")
            or "",
            error="invalid_model_response",
        )
        return None
    content = str(response.get("content") or "").strip()
    if not content:
        record_llm_error(
            state,
            agent_code="supervisor_agent",
            model_id=model_id,
            template_code=(prompt_request.get("metadata") or {}).get("resolved_template_code")
            or (prompt_request.get("metadata") or {}).get("binding_template_code")
            or "",
            error="empty_supervisor_decision_content",
            raw_response_snippet=response.get("content"),
        )
        return None
    payload = parse_json_object_content(content)
    if payload is None:
        record_llm_error(
            state,
            agent_code="supervisor_agent",
            model_id=model_id,
            template_code=(prompt_request.get("metadata") or {}).get("resolved_template_code")
            or (prompt_request.get("metadata") or {}).get("binding_template_code")
            or "",
            error="invalid_supervisor_decision_content",
            raw_response_snippet=response.get("content"),
        )
        return None
    try:
        payload = _normalize_model_decision_payload(state, payload)
        normalized_action = str(payload.get("action") or "").strip().upper()
        decision = SupervisorDecision(
            action=normalized_action,
            side=str(payload.get("side") or "").strip(),
            confidence=int(payload.get("confidence", 0)),
            size_hint=float(payload.get("size_hint", 0.0)),
            leverage_hint=int(payload.get("leverage_hint", 3)),
            holding_window=_normalize_holding_window(payload.get("holding_window")),
            invalidation=_normalize_invalidation(payload.get("invalidation"), action=normalized_action),
            summary_reason=str(payload.get("summary_reason") or "").strip(),
            model_code=str(
                response.get("modelCode")
                or (prompt_request.get("metadata") or {}).get("model_code")
                or ai_model_config.get("model_code")
                or ""
            ).strip(),
            model_provider=str(
                response.get("modelProvider")
                or (prompt_request.get("metadata") or {}).get("model_provider")
                or ai_model_config.get("provider")
                or ""
            ).strip(),
        )
    except Exception as exc:
        record_llm_error(
            state,
            agent_code="supervisor_agent",
            model_id=model_id,
            template_code=(prompt_request.get("metadata") or {}).get("resolved_template_code")
            or (prompt_request.get("metadata") or {}).get("binding_template_code")
            or "",
            error=exc,
            raw_response_snippet=response.get("content"),
        )
        return None
    return _clamp_size_hint(state, _apply_exit_escalation(state, decision.model_dump()))


def _resolve_action_and_side(state: DecisionState, bullish_score: int, bearish_score: int) -> tuple[list[dict], str, str]:
    current_position_side = str(state.get("current_position_side", "flat") or "flat")
    has_active_position = _has_active_position(state)
    views = [view for view in _collect_views(state) if view]
    bullish_views = [view for view in views if view.get("bias") == "bullish"]
    bearish_views = [view for view in views if view.get("bias") == "bearish"]

    if bullish_score > bearish_score:
        if has_active_position and current_position_side == "long":
            return bullish_views, "HOLD", "long"
        if has_active_position and current_position_side == "short":
            return bullish_views, "CLOSE", "short"
        return bullish_views, "OPEN_LONG", "long"
    if bearish_score > bullish_score:
        if has_active_position and current_position_side == "short":
            return bearish_views, "HOLD", "short"
        if has_active_position and current_position_side == "long":
            return bearish_views, "CLOSE", "long"
        return bearish_views, "OPEN_SHORT", "short"
    if has_active_position and current_position_side in {"long", "short"}:
        return [], "REDUCE", current_position_side
    return [], "SKIP", "flat"


def _append_supervisor_final_message(state: DecisionState, decision: dict, metadata: dict | None = None) -> None:
    messages = state.get("agent_messages")
    if not isinstance(messages, list):
        messages = []
    if any(
        isinstance(message, dict)
        and str(message.get("speaker_agent") or "").strip().lower() == "supervisor_agent"
        and str(message.get("message_type") or "").strip().lower() == "final_decision"
        for message in messages
    ):
        state["agent_messages"] = messages
        return
    max_round = max((int(message.get("round_no") or 0) for message in messages if isinstance(message, dict)), default=0)
    resolved_metadata = metadata if isinstance(metadata, dict) else {}
    # 添加 event_time 字段，用于短期记忆 TTL 过滤
    supervised_at = state.get("supervisedAt")
    event_time_str = ""
    if isinstance(supervised_at, datetime):
        event_time_str = supervised_at.isoformat()
    elif isinstance(supervised_at, str) and supervised_at:
        event_time_str = supervised_at
    else:
        event_time_str = datetime.now(timezone.utc).isoformat()
    messages.append(
        {
            "round_no": max_round + 1,
            "speaker_agent": "supervisor_agent",
            "target_agent": "",
            "message_type": "final_decision",
            "event_time": event_time_str,
            "template_code": str(
                resolved_metadata.get("resolved_template_code")
                or resolved_metadata.get("binding_template_code")
                or ""
            ).strip(),
            "model_code": str(decision.get("model_code") or resolved_metadata.get("model_code") or "").strip(),
            "content": dict(decision),
            "summary_text": str(decision.get("summary_reason") or "").strip(),
        }
    )
    state["agent_messages"] = messages


def _set_supervisor_decision(state: DecisionState, decision: dict, metadata: dict | None = None) -> DecisionState:
    state["supervisor_decision"] = decision
    _append_supervisor_final_message(state, decision, metadata)
    return state


def supervisor_agent(state: DecisionState) -> DecisionState:
    """主管Agent节点

    汇总各专业Agent观点，做出最终交易决策。

    流程：
    1. 检查是否允许LLM分发
    2. 解析AI模型配置
    3. 构建主管提示
    4. 调用LLM生成决策
    5. 处理失败情况（fail-open或fail-closed）
    6. 规范化决策结果

    Args:
        state: 决策状态

    Returns:
        DecisionState: 更新后的状态，包含supervisor_decision
    """
    stamp_state_timestamp(state, "supervisedAt")
    state["agent_messages"] = _specialist_handoff_messages(state)
    supervisor_policy_mode = _resolve_supervisor_policy_mode(state)
    if not _supervisor_stage_enabled(state):
        suppression_codes = build_suppression_reason_codes(state)
        summary_reason = str(state.get("rule_only_reason") or "").strip()
        if not summary_reason:
            if supervisor_policy_mode == "NO_DISPATCH":
                summary_reason = "supervisor_disabled_by_policy"
            else:
                summary_reason = ",".join(suppression_codes) if suppression_codes else "dispatch_not_allowed"
        decision = SupervisorDecision(
            action="SKIP",
            side="flat",
            confidence=0,
            size_hint=0.0,
            summary_reason=summary_reason,
        ).model_dump()
        return _set_supervisor_decision(state, decision, state.get("supervisor_prompt_metadata") or {})
    ai_model_config = _resolve_ai_model_config(state)
    prompt_request: dict = {"metadata": {}}
    if llm_dispatch_allowed(state):
        prompt_request = _resolve_supervisor_prompt_request(state, ai_model_config)
        state["supervisor_prompt_metadata"] = prompt_request.get("metadata") or {}
        if _is_ai_model_available(ai_model_config, prompt_request.get("model_id")):
            model_decision = _try_model_supervisor_decision(state, ai_model_config, prompt_request)
            if model_decision is not None:
                return _set_supervisor_decision(state, model_decision, prompt_request.get("metadata") or {})
            if state.get("ai_call_failed") and not _supervisor_ai_fail_open_enabled(state):
                return _set_supervisor_decision(
                    state,
                    _build_ai_fail_closed_decision(
                        ai_model_config,
                        prompt_request.get("metadata") or {},
                    ).model_dump(),
                    prompt_request.get("metadata") or {},
                )
        elif supervisor_policy_mode == "LLM_ALLOWED":
            return _set_supervisor_decision(
                state,
                _build_model_unavailable_decision(ai_model_config).model_dump(),
                prompt_request.get("metadata") or {},
            )
    views = [view for view in _collect_views(state) if view]
    bullish_views = [view for view in views if view.get("bias") == "bullish"]
    bearish_views = [view for view in views if view.get("bias") == "bearish"]
    bullish_score = sum(int(view.get("confidence", 0)) for view in bullish_views)
    bearish_score = sum(int(view.get("confidence", 0)) for view in bearish_views)
    winning_views, action, side = _resolve_action_and_side(state, bullish_score, bearish_score)

    confidence = (
        int(round(sum(int(view.get("confidence", 0)) for view in winning_views) / len(winning_views)))
        if winning_views
        else 50 if action == "SKIP" else max(bullish_score, bearish_score, 50)
    )
    summary_reason = "; ".join(
        str(view.get("reason", "")).strip() for view in winning_views if str(view.get("reason", "")).strip()
    )
    if not summary_reason and action == "REDUCE":
        summary_reason = "balanced_views_reduce_existing_position"
    if not summary_reason and action == "CLOSE":
        summary_reason = "close_opposing_existing_position"
    if not summary_reason and action == "HOLD":
        summary_reason = "aligned_views_hold_existing_position"
    if not summary_reason and action == "SKIP":
        summary_reason = "no_clear_edge_skip"

    decision_payload = {
        "action": action,
        "side": side,
        "confidence": confidence,
        "size_hint": (
            0.5
            if action == "REDUCE"
            else 1.0
            if action == "CLOSE"
            else 0.0
            if action in {"HOLD", "SKIP"}
            else 0.35
        ),
        "summary_reason": summary_reason,
        "model_code": str(ai_model_config.get("model_code") or "").strip(),
        "model_provider": str(ai_model_config.get("provider") or "").strip(),
    }
    return _set_supervisor_decision(
        state,
        _clamp_size_hint(state, _apply_exit_escalation(state, decision_payload)),
        prompt_request.get("metadata") or {},
    )
