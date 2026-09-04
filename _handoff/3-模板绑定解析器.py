from __future__ import annotations

import json
from typing import Any


def _is_enabled_flag(value: object, default: bool = True) -> bool:
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


def _normalize_scope_values(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    payload = value
    if isinstance(value, str):
        try:
            payload = json.loads(value)
        except (TypeError, ValueError):
            payload = [value]
    if not isinstance(payload, (list, tuple, set)):
        payload = [payload]
    normalized: list[str] = []
    for item in payload:
        canonical = str(item or "").strip().upper()
        if canonical and canonical not in normalized:
            normalized.append(canonical)
    return normalized


def _matches_scope_value(scope_values: Any, current_value: str | None) -> bool:
    values = _normalize_scope_values(scope_values)
    if not values:
        return True
    if current_value in (None, ""):
        return False
    return str(current_value).strip().upper() in values


def _specificity_score(binding: dict[str, Any]) -> int:
    score = 0
    if binding.get("strategy_version_id") not in (None, "") or binding.get("strategyVersionId") not in (None, ""):
        score += 100
    elif binding.get("strategy_id") not in (None, "") or binding.get("strategyId") not in (None, ""):
        score += 50
    if binding.get("symbol") not in (None, ""):
        score += 10
    if binding.get("exchange_code") not in (None, "") or binding.get("exchangeCode") not in (None, ""):
        score += 5
    if binding.get("mode_scope_json") not in (None, "") or binding.get("modeScopeJson") not in (None, ""):
        score += 1
    return score


def resolve_prompt_binding(
    prompt_bindings: list[dict[str, Any]] | None,
    *,
    binding_scope: str,
    mode: str | None = None,
    event_strength: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(prompt_bindings, list):
        return None
    normalized_scope = str(binding_scope or "").strip().upper()
    candidates: list[tuple[int, int, int, dict[str, Any]]] = []
    for index, binding in enumerate(prompt_bindings):
        if not isinstance(binding, dict):
            continue
        if not _is_enabled_flag(binding.get("enabled"), default=True):
            continue
        if str(binding.get("binding_scope") or "").strip().upper() != normalized_scope:
            continue
        if not _matches_scope_value(binding.get("mode_scope_json"), mode):
            continue
        if not _matches_scope_value(binding.get("event_strength_scope_json"), event_strength):
            continue
        try:
            priority = int(binding.get("priority") or 0)
        except (TypeError, ValueError):
            priority = 0
        candidates.append((_specificity_score(binding), priority, index, binding))
    if not candidates:
        return None
    return min(candidates, key=lambda item: (-item[0], item[1], item[2]))[3]
