from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from trade_runtime.config import parse_object_json


_DEFAULT_CONFIG = {
    "enabled": True,
    "intervalSeconds": 10,
    "cooldownSeconds": 30,
    "reviewAdverseMovePct": 0.35,
    "reduceAdverseMovePct": 0.7,
    "closeAdverseMovePct": 1.2,
    "profitGivebackPct": 0.45,
    "structureReviewEnabled": True,
    "hardCloseEnabled": False,
    "marketTickStaleAfterSeconds": 90,
}

_SEVERITY_RANK = {"none": 0, "review": 1, "reduce": 2, "close": 3}


def _object_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if value is None:
        return {}
    payload: dict[str, Any] = {}
    for key in dir(value):
        if key.startswith("_"):
            continue
        try:
            item = getattr(value, key)
        except Exception:
            continue
        if callable(item) or item in (None, ""):
            continue
        payload[key] = item
    return payload


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _is_enabled(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "disabled"}:
        return False
    return default


def _normalize_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    normalized = str(value or "").strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    if normalized:
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def resolve_position_risk_watcher_config(
    runtime_config: Any,
    strategy_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_payload = _object_payload(runtime_config)
    strategy_payload = strategy_context if isinstance(strategy_context, dict) else {}
    strategy_config = strategy_payload.get("strategy_config") if isinstance(strategy_payload.get("strategy_config"), dict) else {}
    runtime_flags = parse_object_json(runtime_payload.get("runtime_flags") or runtime_payload.get("runtimeFlags"))
    runtime_flags_json = parse_object_json(
        runtime_payload.get("runtime_flags_json") or runtime_payload.get("runtimeFlagsJson")
    )
    merged_flags = _deep_merge(runtime_flags_json, runtime_flags)
    candidates = [
        parse_object_json(runtime_payload.get("positionRiskWatcher") or runtime_payload.get("position_risk_watcher")),
        parse_object_json(merged_flags.get("positionRiskWatcher") or merged_flags.get("position_risk_watcher")),
        parse_object_json(strategy_config.get("positionRiskWatcher") or strategy_config.get("position_risk_watcher")),
        parse_object_json(strategy_payload.get("positionRiskWatcher") or strategy_payload.get("position_risk_watcher")),
    ]
    provided = any(bool(item) for item in candidates)
    config = dict(_DEFAULT_CONFIG)
    if provided:
        config["enabled"] = True
    for item in candidates:
        if item:
            config = _deep_merge(config, item)
    config["enabled"] = _is_enabled(config.get("enabled"), bool(provided))
    config["structureReviewEnabled"] = _is_enabled(config.get("structureReviewEnabled"), True)
    config["hardCloseEnabled"] = _is_enabled(config.get("hardCloseEnabled"), False)
    config["intervalSeconds"] = max(1, _safe_int(config.get("intervalSeconds"), 10))
    config["cooldownSeconds"] = max(0, _safe_int(config.get("cooldownSeconds"), 30))
    config["marketTickStaleAfterSeconds"] = max(1, _safe_int(config.get("marketTickStaleAfterSeconds"), 90))
    return config


def _position_side(account_context: dict[str, Any]) -> str:
    normalized = str(
        account_context.get("current_position_side")
        or account_context.get("position_side")
        or account_context.get("side")
        or ""
    ).strip().lower()
    if normalized in {"long", "buy", "bullish"}:
        return "long"
    if normalized in {"short", "sell", "bearish"}:
        return "short"
    return ""


def _position_quantity(account_context: dict[str, Any]) -> float:
    return max(
        _safe_float(
            account_context.get("current_position_quantity")
            or account_context.get("position_quantity")
            or account_context.get("quantity")
        ),
        0.0,
    )


def _latest_event(event_bundle: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    normalized_type = str(event_type or "").strip().lower()
    for event in reversed(event_bundle):
        if isinstance(event, dict) and str(event.get("event_type") or "").strip().lower() == normalized_type:
            return event
    return {}


def _current_price_context(
    feature_snapshot: dict[str, Any],
    event_bundle: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    staleness = _safe_float(
        feature_snapshot.get("market_tick_staleness_seconds")
        or feature_snapshot.get("trade_tick_age_seconds")
    )
    stale_after_seconds = _safe_float(config.get("marketTickStaleAfterSeconds"), 90.0)
    trade_tick_stale = staleness > stale_after_seconds
    effective_price = _safe_float(feature_snapshot.get("effective_price"))
    effective_source = str(feature_snapshot.get("effective_price_source") or "").strip() or "effective_price"
    if effective_price > 0:
        return {
            "current_price": effective_price,
            "price_source": effective_source,
            "trade_tick_stale": trade_tick_stale,
        }
    mark_price = _safe_float(feature_snapshot.get("mark_price") or _latest_event(event_bundle, "mark_price").get("price"))
    if mark_price > 0:
        return {"current_price": mark_price, "price_source": "mark_price", "trade_tick_stale": trade_tick_stale}
    kline_close = _safe_float(feature_snapshot.get("latest_kline_close"))
    if kline_close > 0:
        return {"current_price": kline_close, "price_source": "kline_close", "trade_tick_stale": trade_tick_stale}
    trade_price = _safe_float(feature_snapshot.get("latest_trade_price") or _latest_event(event_bundle, "market_tick").get("price"))
    if trade_price > 0:
        return {"current_price": trade_price, "price_source": "trade", "trade_tick_stale": trade_tick_stale}
    return {"current_price": 0.0, "price_source": "", "trade_tick_stale": trade_tick_stale}


def _signed_position_pnl_pct(side: str, entry_price: float, current_price: float) -> float:
    if entry_price <= 0 or current_price <= 0:
        return 0.0
    if side == "long":
        return round(((current_price - entry_price) / entry_price) * 100.0, 6)
    if side == "short":
        return round(((entry_price - current_price) / entry_price) * 100.0, 6)
    return 0.0


def _structure_reversal(side: str, feature_snapshot: dict[str, Any], config: dict[str, Any]) -> bool:
    if not config.get("structureReviewEnabled"):
        return False
    wyckoff = feature_snapshot.get("wyckoff_shortterm")
    if not isinstance(wyckoff, dict):
        return False
    readiness = str(wyckoff.get("trade_readiness") or "").strip().lower()
    if readiness not in {"ready", "watch"}:
        return False
    entry_bias = str(wyckoff.get("entry_bias") or "").strip().lower()
    if side == "long":
        return entry_bias == "bearish"
    if side == "short":
        return entry_bias == "bullish"
    return False


def _direction_for_position_risk(side: str) -> str:
    if side == "long":
        return "bearish"
    if side == "short":
        return "bullish"
    return "risk"


def _base_result(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": bool(config.get("enabled")),
        "has_position": False,
        "triggered": False,
        "suppressed_by_cooldown": False,
        "severity": "none",
        "action": "NONE",
        "reason": "",
        "risk_signals": [],
        "position_risk_context": {},
        "position_risk_event": {},
        "bypass_trigger_guards": False,
    }


def evaluate_position_risk(
    *,
    account_context: dict[str, Any] | None,
    feature_snapshot: dict[str, Any] | None,
    event_bundle: list[dict[str, Any]] | None,
    runtime_config: Any,
    strategy_context: dict[str, Any] | None,
    now: Any = None,
) -> dict[str, Any]:
    config = resolve_position_risk_watcher_config(runtime_config, strategy_context)
    result = _base_result(config)
    if not config.get("enabled"):
        return result
    account_payload = account_context if isinstance(account_context, dict) else {}
    feature_payload = feature_snapshot if isinstance(feature_snapshot, dict) else {}
    events = [item for item in event_bundle or [] if isinstance(item, dict)]
    side = _position_side(account_payload)
    quantity = _position_quantity(account_payload)
    if side not in {"long", "short"} or quantity <= 0:
        return result
    result["has_position"] = True
    entry_price = _safe_float(account_payload.get("entry_price") or account_payload.get("avg_entry_price"))
    price_context = _current_price_context(feature_payload, events, config)
    current_price = _safe_float(price_context.get("current_price"))
    pnl_pct = _signed_position_pnl_pct(side, entry_price, current_price)
    adverse_move_pct = round(max(0.0, -pnl_pct), 6)
    peak_pnl_pct = _safe_float(
        account_payload.get("peak_unrealized_pnl_pct")
        or feature_payload.get("peak_unrealized_pnl_pct")
    )
    profit_giveback_pct = round(max(0.0, peak_pnl_pct - max(pnl_pct, 0.0)), 6) if peak_pnl_pct > 0 else 0.0

    risk_signals: list[dict[str, Any]] = []
    severity = "none"
    reason = ""
    if adverse_move_pct >= _safe_float(config.get("closeAdverseMovePct"), 1.2):
        severity = "close"
        reason = "adverse_move_close"
        risk_signals.append({"type": reason, "value": adverse_move_pct})
    elif adverse_move_pct >= _safe_float(config.get("reduceAdverseMovePct"), 0.7):
        severity = "reduce"
        reason = "adverse_move_reduce"
        risk_signals.append({"type": reason, "value": adverse_move_pct})
    elif adverse_move_pct >= _safe_float(config.get("reviewAdverseMovePct"), 0.35):
        severity = "review"
        reason = "adverse_move_review"
        risk_signals.append({"type": reason, "value": adverse_move_pct})
    elif profit_giveback_pct >= _safe_float(config.get("profitGivebackPct"), 0.45):
        severity = "review"
        reason = "profit_giveback"
        risk_signals.append({"type": reason, "value": profit_giveback_pct})
    elif _structure_reversal(side, feature_payload, config):
        severity = "review"
        reason = "structure_reversal"
        risk_signals.append({"type": reason, "value": 1.0})

    context = {
        "side": side,
        "quantity": quantity,
        "entry_price": entry_price,
        "current_price": current_price,
        "price_source": price_context.get("price_source") or "",
        "trade_tick_stale": bool(price_context.get("trade_tick_stale")),
        "pnl_pct": pnl_pct,
        "adverse_move_pct": adverse_move_pct,
        "peak_unrealized_pnl_pct": peak_pnl_pct,
        "profit_giveback_pct": profit_giveback_pct,
    }
    result["position_risk_context"] = context
    result["risk_signals"] = risk_signals
    result["severity"] = severity
    result["reason"] = reason
    if severity == "none":
        return result

    action = "CLOSE" if severity == "close" and config.get("hardCloseEnabled") else "REVIEW"
    now_dt = _normalize_datetime(now)
    event = {
        "event_type": "position_risk",
        "source_type": "position_risk",
        "symbol": str(feature_payload.get("symbol") or next((item.get("symbol") for item in events if item.get("symbol")), "") or "").strip(),
        "position_side": side,
        "direction": _direction_for_position_risk(side),
        "severity": severity,
        "action": action,
        "reason": reason,
        "current_price": current_price,
        "entry_price": entry_price,
        "adverse_move_pct": adverse_move_pct,
        "profit_giveback_pct": profit_giveback_pct,
        "dispatch_mode": "LLM_ALLOWED",
        "event_time": now_dt.isoformat(),
    }
    result.update(
        {
            "triggered": True,
            "action": action,
            "position_risk_event": event,
            "bypass_trigger_guards": True,
        }
    )
    return result


class PositionRiskWatcher:
    def __init__(self):
        self._cooldowns: dict[str, dict[str, Any]] = {}

    def evaluate(
        self,
        *,
        account_context: dict[str, Any] | None,
        feature_snapshot: dict[str, Any] | None,
        event_bundle: list[dict[str, Any]] | None,
        runtime_config: Any,
        strategy_context: dict[str, Any] | None,
        now: Any = None,
    ) -> dict[str, Any]:
        result = evaluate_position_risk(
            account_context=account_context,
            feature_snapshot=feature_snapshot,
            event_bundle=event_bundle,
            runtime_config=runtime_config,
            strategy_context=strategy_context,
            now=now,
        )
        if not result.get("triggered"):
            return result
        config = resolve_position_risk_watcher_config(runtime_config, strategy_context)
        now_dt = _normalize_datetime(now)
        context = result.get("position_risk_context") if isinstance(result.get("position_risk_context"), dict) else {}
        cooldown_key = ":".join(
            [
                str((feature_snapshot or {}).get("symbol") or "").strip(),
                str(context.get("side") or ""),
                str(context.get("entry_price") or ""),
            ]
        )
        cooldown_seconds = max(0, _safe_int(config.get("cooldownSeconds"), 30))
        previous = self._cooldowns.get(cooldown_key)
        severity_rank = _SEVERITY_RANK.get(str(result.get("severity") or "none"), 0)
        if previous and cooldown_seconds > 0:
            elapsed = (now_dt - previous["triggered_at"]).total_seconds()
            previous_rank = int(previous.get("severity_rank") or 0)
            if elapsed < cooldown_seconds and severity_rank <= previous_rank:
                suppressed = dict(result)
                suppressed["triggered"] = False
                suppressed["suppressed_by_cooldown"] = True
                suppressed["bypass_trigger_guards"] = False
                return suppressed
        self._cooldowns[cooldown_key] = {"triggered_at": now_dt, "severity_rank": severity_rank}
        return result
