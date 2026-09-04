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
    position_ratio_floor,
    venue_order_floor,
)
# 可下仓位区间搬到了 decision/sizing.py：模板渲染上下文也要用同一份实现，
# 否则内联与模板两条路径会给模型算出不同的区间。这里保留原名以免改动调用点。
from trade_runtime.decision.sizing import (
    current_market_price as _current_market_price,
    sizing_constraints as _sizing_constraints,
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
# 指令段的正文放在 prompting 下：数据库模板与这里的内联提示词读同一份，
# 分成两份的话 inline / template 的对照就变成在比措辞。
from trade_runtime.prompting.supervisor_template import (
    SUPERVISOR_EMPTY_MEMORY_NOTE,
    SUPERVISOR_METHODOLOGY,
    SUPERVISOR_OUTPUT_CONTRACT,
)

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
    # 缺省是 EVENT_GATED 而不是 LLM_ALLOWED。后者会让 _supervisor_stage_enabled
    # 直接返回 llm_dispatch_allowed()，于是 RULE_ONLY 下主管阶段整个被关掉，
    # 下面那段规则基线在名为"仅规则"的模式里成了死代码——线上 24 小时
    # 13053 次 RULE_ONLY 决策，无一例外 SKIP/dispatch_not_allowed。
    return normalized if normalized in _SUPERVISOR_POLICY_MODES else "EVENT_GATED"


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


def _supervisor_runtime_flags(state: DecisionState) -> dict:
    """取合并后的 runtime flags。

    直接写的 runtime_flags 覆盖 runtime_flags_json 里的同名键，两处都可能缺。
    """
    runtime_config = state.get("runtime_config") or {}
    if not isinstance(runtime_config, dict):
        return {}
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
    return runtime_flags


#: 规则基线动作的门槛。基线只看四个观点的多空得分，而行情观点在价格变动
#: 超过 0.1% 时就会取向——没有门槛的话它几乎每一跳都会给出一个动作。
_DEFAULT_BASELINE_POLICY = {
    # 规则基线能不能自己开仓。默认关：开仓是加风险敞口，交给模型判断；
    # 平仓/减仓是降风险，基线可以做。保护性平仓另有 position_risk_watcher
    # 那条确定性路径，不依赖这里。
    "entriesEnabled": False,
    "minConfidence": 65,
    # 胜方得分要领先多少（占多空总分的百分比）才算有边际。51 比 49 不是边际。
    "minScoreMarginPct": 20,
}


def _resolve_baseline_policy(state: DecisionState) -> dict:
    policy = dict(_DEFAULT_BASELINE_POLICY)
    candidate = _supervisor_runtime_flags(state).get("baselinePolicy")
    if isinstance(candidate, dict):
        policy.update({key: value for key, value in candidate.items() if value is not None})
    return {
        "entries_enabled": _is_enabled_flag(policy.get("entriesEnabled"), default=False),
        "min_confidence": _safe_float(policy.get("minConfidence"), 65.0),
        "min_score_margin_pct": _safe_float(policy.get("minScoreMarginPct"), 20.0),
    }


def _apply_baseline_policy(
    state: DecisionState,
    decision_payload: dict,
    bullish_score: int,
    bearish_score: int,
) -> dict:
    """给规则基线的动作加门槛。

    基线本身只是"谁的加权得分高就往哪边动"，没有任何边际要求：行情规则观点
    在 |涨跌| >= 0.1% 时就会取向，所以不加门槛的话，RULE_ONLY 一放开就会在
    几乎每一次决策上给出动作。

    保护路径不受这里约束：position_risk 已经把这笔仓位标成 reduce/close 时
    直接放行，让 _apply_exit_escalation 能照常升级；而 hardClose 那条更是
    完全不经过主管。
    """
    payload = dict(decision_payload or {})
    action = str(payload.get("action") or "").strip().upper()
    if action in {"", "SKIP", "NO_ACTION"}:
        return payload

    risk_severity = str((state.get("position_risk_result") or {}).get("severity") or "").strip().lower()
    if risk_severity in {"reduce", "close"}:
        return payload

    total_score = max(0, int(bullish_score)) + max(0, int(bearish_score))
    # 观点真的对立时的 REDUCE 是"信号打架就减风险"，本身是降风险动作，不受
    # 边际门槛约束。但要和另一种平局分开：四个观点全中性时两边都是 0，
    # _resolve_action_and_side 同样会走到 REDUCE 分支——那不是对立，是没有
    # 信息，而 RULE_ONLY 下这种安静的决策每天上万次，不挡就会一直削仓。
    if action == "REDUCE" and total_score > 0:
        return payload

    policy = _resolve_baseline_policy(state)
    blocked = ""
    if action in {"OPEN_LONG", "OPEN_SHORT", "ADD_LONG", "ADD_SHORT"} and not policy["entries_enabled"]:
        blocked = "baseline_entries_disabled"
    else:
        confidence = _safe_float(payload.get("confidence"), 0.0)
        margin_pct = (abs(bullish_score - bearish_score) / total_score * 100.0) if total_score > 0 else 0.0
        if confidence < policy["min_confidence"]:
            blocked = f"baseline_confidence_{confidence:.0f}_below_{policy['min_confidence']:.0f}"
        elif margin_pct < policy["min_score_margin_pct"]:
            blocked = f"baseline_margin_{margin_pct:.0f}pct_below_{policy['min_score_margin_pct']:.0f}pct"
    if not blocked:
        return payload

    # 有仓位就 HOLD（什么都不做，但如实说明还持着），没仓位就 SKIP。
    holding_side = _current_position_side(state)
    if _has_active_position(state) and holding_side in {"long", "short"}:
        payload["action"] = "HOLD"
        payload["side"] = holding_side
    else:
        payload["action"] = "SKIP"
        payload["side"] = "flat"
    payload["size_hint"] = 0.0
    summary_reason = str(payload.get("summary_reason") or "").strip()
    payload["summary_reason"] = f"{summary_reason}; {blocked}" if summary_reason else blocked
    return payload


def _supervisor_ai_fail_open_enabled(state: DecisionState) -> bool:
    runtime_config = state.get("runtime_config") or {}
    if not isinstance(runtime_config, dict):
        return False
    effective_mode = str(state.get("effective_mode") or state.get("mode") or "").strip().lower()
    if effective_mode not in {"paper", "shadow", ""}:
        return False
    runtime_flags = _supervisor_runtime_flags(state)
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


def _apply_size_floor(state: DecisionState, size_hint: float, ceiling: float) -> float:
    """把建仓的 size_hint 夹进 [下界, 上限]。

    只抬高大于 0 的值：OPEN 配 size_hint=0 是自相矛盾的输入，保守的读法是
    模型并不想建仓，不该由这里凭空造出一个仓位来——和 leverage_hint 给 0
    时退回默认倍数不同，那一档没有“不开”这个含义。
    """
    bounded = min(max(float(size_hint or 0.0), 0.0), max(float(ceiling or 0.0), 0.0))
    if bounded <= 0:
        return bounded
    floor = position_ratio_floor(state.get("runtime_config") or {}, ceiling)
    return max(bounded, floor)


def _clamp_size_hint(state: DecisionState, decision_payload: dict) -> dict:
    payload = dict(decision_payload or {})
    action = str(payload.get("action") or "").strip().upper()
    side = str(payload.get("side") or "").strip().lower()
    size_hint = max(0.0, _safe_float(payload.get("size_hint"), 0.0))
    if action in {"OPEN_LONG", "OPEN_SHORT"}:
        payload["size_hint"] = _apply_size_floor(state, size_hint, _max_position_ratio(state))
        return payload
    if action in {"ADD_LONG", "ADD_SHORT"}:
        payload["size_hint"] = _apply_size_floor(state, size_hint, _remaining_position_headroom(state))
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


#: 自由裁量平仓的最短持仓分钟数。0 关闭本闸门。
_MIN_HOLD_KEY = "minHoldMinutesBeforeDiscretionaryClose"
_MIN_HOLD_DEFAULT_MINUTES = 60


def _apply_min_hold_guard(state: DecisionState, decision_payload: dict) -> dict:
    """拦住"死区内砍亏损单"——只拦这一件事。

    实测 122 个 ready 信号，收益按持仓时长拆开（扣费后）：
        15m -0.084%  30m -0.088%  45m -0.025%  60m +0.010%
        90m +0.174%(t=2.57)  120m +0.249%(t=3.32)  180m +0.492%(t=4.16)
    **60 分钟之前没有优势，是负的**；优势要到 90 分钟才统计显著。
    同一批信号的最大浮亏中位数是 -0.44%、p25 是 -0.845%——开仓后先逆向是常态，
    不是入场错了。

    线上代价是实测出来的：4 笔平仓全亏，其中 WDC 在第 24 分钟(-0.63%)、
    SNDK 在第 42 分钟(-1.11%) 被模型主动 CLOSE，都远没碰到 2% 硬止损。
    SNDK 砍在最深浮亏 -2.12% 附近，之后按原方向 +3.10%(60m)/+6.15%(120m)/
    +6.31%(240m)。模拟"风控叫醒即平"：阈值 0.6% 时扣费后 0.362%/胜率 49.2%，
    从不早平是 0.437%/56.6%——每笔吃掉 0.075 个百分点。

    三处不拦，都是有理由的：
    - **止盈不拦**：上面的结论是关于"砍亏损单"的，浮盈为正时照常放行。
    - **风控 close 级不拦**：那是 2% 级别的真失效，不是噪声。
    - **app.py 的硬平仓根本不经过这里**：它读 runner 返回值、不走图状态，
      LLM 失败时照样执行。所以这个闸门不会削弱兜底止损。
    """
    payload = dict(decision_payload or {})
    if str(payload.get("action") or "").strip().upper() != "CLOSE":
        return payload
    if _current_position_side(state) not in {"long", "short"}:
        return payload

    min_hold = _min_hold_minutes(state)
    if min_hold <= 0:
        return payload

    held = state.get("current_position_holding_minutes")
    try:
        held_minutes = int(held)
    except (TypeError, ValueError):
        # 拿不到持仓时长就不拦——宁可放行，也不要因为读不到数据而把仓位锁住。
        return payload
    if held_minutes >= min_hold:
        return payload

    risk_result = state.get("position_risk_result") or {}
    if str(risk_result.get("severity") or "").strip().lower() == "close":
        return payload

    risk_context = risk_result.get("position_risk_context") or {}
    pnl_pct = risk_context.get("pnl_pct")
    try:
        if pnl_pct is not None and float(pnl_pct) > 0:
            return payload
    except (TypeError, ValueError):
        pass

    payload["action"] = "HOLD"
    payload["size_hint"] = 0.0
    payload["min_hold_guard"] = {
        "blocked_action": "CLOSE",
        "held_minutes": held_minutes,
        "min_hold_minutes": min_hold,
        "original_reason": str(payload.get("summary_reason") or "")[:400],
    }
    payload["summary_reason"] = (
        f"[min_hold_guard] 持仓仅 {held_minutes} 分钟(<{min_hold})且为浮亏，"
        f"该区间平仓的历史期望为负，降级为 HOLD；2% 硬止损不受影响。"
        f"原因: {str(payload.get('summary_reason') or '')[:200]}"
    )
    return payload


def _min_hold_minutes(state: DecisionState) -> int:
    flags = _supervisor_runtime_flags(state)
    raw = flags.get(_MIN_HOLD_KEY)
    if raw is None:
        raw = flags.get("min_hold_minutes_before_discretionary_close")
    if raw is None:
        return _MIN_HOLD_DEFAULT_MINUTES
    try:
        return max(0, int(float(raw)))
    except (TypeError, ValueError):
        return _MIN_HOLD_DEFAULT_MINUTES


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
    # 旧文案让模型"降低 confidence 和 size_hint"——复盘里每一笔坏入场都是
    # 这个动作的产物。记忆为空该换来更严的确认要求，不是更小的仓位。
    memory_warning = "" if long_term_items else SUPERVISOR_EMPTY_MEMORY_NOTE

    return (
        f"{SUPERVISOR_METHODOLOGY}\n\n"
        f"{SUPERVISOR_OUTPUT_CONTRACT}\n\n"
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
    return _clamp_size_hint(state, _apply_min_hold_guard(state, _apply_exit_escalation(state, decision.model_dump())))


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
        elif not _supervisor_ai_fail_open_enabled(state):
            # 该用模型、模型却不可用时如实说明，不要静默退回规则基线。
            # 这里此前判的是 supervisor_policy_mode == "LLM_ALLOWED"，而策略
            # 缺省值一改这条就失效了——策略模式管"主管阶段跑不跑"，
            # 要不要退回规则由 fail-open 一个开关说了算，两件事不该缠在一起。
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
    gated_payload = _apply_baseline_policy(state, decision_payload, bullish_score, bearish_score)
    return _set_supervisor_decision(
        state,
        _clamp_size_hint(state, _apply_min_hold_guard(state, _apply_exit_escalation(state, gated_payload))),
        prompt_request.get("metadata") or {},
    )
