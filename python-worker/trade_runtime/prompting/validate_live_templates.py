"""校验线上 prompt_template 能被生产渲染器完整填充。

为什么需要它：`tests/trade_runtime/test_sql_prompt_rendering.py` 做的正是这件事，
但它从 `sql/ai_trading.sql` 读模板，而作者把那个文件加进了 .gitignore、从未提交。
于是这两个测试在本部署上恒为 FileNotFoundError——一直挂着、一直被当成"已知失败"
忽略，等于这条校验从部署起就没生效过。

本部署的模板真实来源是数据库。这个脚本对它跑同样的判定，且复用生产的
`build_supervisor_render_context` 与 `render_template`，不复制任何渲染逻辑。

失败意味着什么：`render_template_content` 对上下文里没有的键做的是
`safe_variables.get(key, "")`——**静默替换成空字符串**，不是留下 `{foo}`。
所以模板里写错一个变量名，模型看到的就是少了一整段的提示词，而调用成功、
日志干净、什么信号都没有。判定必须落在"占位符是否都在上下文里"，
不能指望从渲染结果里看出残留（那永远看不出来）。

用法（在服务器上）：
    /opt/dca/venv/bin/python -m trade_runtime.prompting.validate_live_templates
退出码非 0 表示有模板渲染不完整。
"""
from __future__ import annotations

import re
import subprocess
import sys
from typing import Any

from trade_runtime.prompting.render_context_builder import build_supervisor_render_context
from trade_runtime.prompting.renderers import render_template

_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _query(sql: str, database: str = "ai_trading") -> str:
    return subprocess.run(
        ["mysql", "-N", "-B", "--raw", "-e", sql, database],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _active_templates() -> list[tuple[str, str]]:
    rows = _query(
        "SELECT code, content FROM prompt_template WHERE is_active = 1 ORDER BY id"
    ).split("\t", 1)
    if len(rows) < 2:
        return []
    codes = _query("SELECT code FROM prompt_template WHERE is_active = 1 ORDER BY id").split()
    return [(code, _query(f"SELECT content FROM prompt_template WHERE code='{code}'")) for code in codes]


def _representative_state() -> dict[str, Any]:
    """渲染上下文只关心键是否齐全，值取到即可，不必是真实行情。"""
    return {
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "trace_id": "validate-live-templates",
        "feature_snapshot": {"symbol": "BTCUSDT", "event_strength": "strong"},
        "runtime_account_context": {"current_position_side": "flat"},
        "runtime_config": {},
        "strategy_context": {},
    }


def main() -> int:
    templates = _active_templates()
    if not templates:
        print("没有启用中的模板，跳过")
        return 0

    context = build_supervisor_render_context(_representative_state())
    failures = 0
    for code, content in templates:
        placeholders = set(_PLACEHOLDER.findall(content))
        missing = sorted(p for p in placeholders if p not in context)
        rendered = render_template({"content": content}, context)

        problems = []
        if missing:
            problems.append(f"上下文缺失 {missing}（这些位置会被静默替换成空串）")
        if re.search(r"\?{4,}", rendered):
            problems.append("渲染后出现 ???? 乱码（多半是编码问题）")
        if not rendered.strip():
            problems.append("渲染结果为空")

        if problems:
            failures += 1
            print(f"  {code}  ✗  " + "；".join(problems))
        else:
            print(f"  {code}  ✓  占位符 {len(placeholders)} 个全部填充")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
