from __future__ import annotations

import re
from typing import Any


VARIABLE_PATTERN = re.compile(r"\{([^}]+)\}")


def render_template_content(template_content: str | None, variables: dict[str, Any] | None) -> str:
    content = str(template_content or "")
    if not content:
        return ""
    safe_variables = variables or {}

    def replace(match: re.Match[str]) -> str:
        key = str(match.group(1) or "").strip()
        value = safe_variables.get(key, "")
        return "" if value is None else str(value)

    return VARIABLE_PATTERN.sub(replace, content)


def render_template(template_payload: dict[str, Any] | None, variables: dict[str, Any] | None) -> str:
    if not isinstance(template_payload, dict):
        return ""
    return render_template_content(template_payload.get("content"), variables)
