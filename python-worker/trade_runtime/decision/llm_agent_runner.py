from __future__ import annotations

from typing import Any

from trade_runtime.decision.agent_profile_resolver import resolve_agent_execution_config
from trade_runtime.decision.output_parsers import parse_agent_view_content
from trade_runtime.prompting.prompt_template_registry import resolve_prompt_template_registry
from trade_runtime.prompting.render_context_builder import build_agent_render_context
from trade_runtime.prompting.renderers import render_template


def record_llm_error(
    state: dict[str, Any],
    *,
    agent_code: str,
    model_id: object = None,
    template_code: str = "",
    error: object,
    raw_response_snippet: object = None,
) -> None:
    errors = state.setdefault("agent_llm_errors", [])
    if not isinstance(errors, list):
        errors = []
        state["agent_llm_errors"] = errors
    payload = {
        "agent_code": str(agent_code or "").strip(),
        "model_id": model_id,
        "template_code": str(template_code or "").strip(),
        "error": str(error or "").strip(),
    }
    if raw_response_snippet not in (None, ""):
        payload["raw_response_snippet"] = str(raw_response_snippet)[:500]
    errors.append(payload)
    state["ai_call_failed"] = True



def run_llm_agent(
    state: dict[str, Any],
    *,
    agent_code: str,
    binding_scope: str,
    rule_view: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    decision_model_client = state.get("decision_model_client")
    if decision_model_client is None:
        return None
    agent_config = resolve_agent_execution_config(state, agent_code, binding_scope=binding_scope)
    if agent_config is None:
        return None
    registry = resolve_prompt_template_registry(state)
    if registry is None:
        return None
    template_code = str(agent_config.get("template_code") or "").strip()
    template = registry.get_template(template_code)
    if not isinstance(template, dict):
        return None
    model_id = agent_config.get("model_id")
    if model_id is None:
        return None
    prompt = render_template(
        template,
        build_agent_render_context(state, agent_code=agent_code, rule_view=rule_view),
    )
    if not prompt:
        return None
    try:
        response = decision_model_client.call_model(model_id=model_id, prompt=prompt)
    except Exception as exc:
        record_llm_error(
            state,
            agent_code=agent_code,
            model_id=model_id,
            template_code=template_code,
            error=exc,
        )
        return None
    if not isinstance(response, dict):
        record_llm_error(
            state,
            agent_code=agent_code,
            model_id=model_id,
            template_code=template_code,
            error="invalid_model_response",
        )
        return None
    view = parse_agent_view_content(response.get("content"))
    if view is None:
        record_llm_error(
            state,
            agent_code=agent_code,
            model_id=model_id,
            template_code=template_code,
            error="invalid_agent_view_content",
            raw_response_snippet=response.get("content"),
        )
        return None
    view["template_code"] = template_code
    view["model_code"] = str(
        response.get("modelCode")
        or agent_config.get("model_code")
        or ""
    ).strip()
    view["model_provider"] = str(
        response.get("modelProvider")
        or agent_config.get("model_provider")
        or ""
    ).strip()
    return view
