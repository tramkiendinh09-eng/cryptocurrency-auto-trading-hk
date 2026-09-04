"""从代码常量生成 prompt_template / trade_prompt_binding 的 SQL。

不手写 SQL 的理由：模板正文必须与内联提示词逐字一致，否则
prompt_source=inline 与 template 的对照测的是措辞漂移而不是方法论。
这个脚本直接引用 prompting/supervisor_template.py，两边不可能分叉。

用法:
    python3 deploy/native/seed_supervisor_prompt_template.py > /tmp/seed.sql
    mysql -uroot -p ai_trading < /tmp/seed.sql

生成的 SQL 是幂等的：prompt_template.code 上只有非唯一索引，所以走的是
UPDATE + 条件 INSERT 而不是 upsert，重复执行不会插出重复行。
"""
from __future__ import annotations

import sys

import pathlib

# deploy/native/ -> 仓库根 -> python-worker，不写死部署路径
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "python-worker"))

from trade_runtime.prompting.supervisor_template import (  # noqa: E402
    SUPERVISOR_TEMPLATE_CODE,
    SUPERVISOR_TEMPLATE_NAME,
    supervisor_template_content,
    supervisor_template_placeholders,
)
from trade_runtime.prompting.render_context_builder import (  # noqa: E402
    build_supervisor_render_context,
)

CONTENT = supervisor_template_content()
PLACEHOLDERS = supervisor_template_placeholders()

# 上线前的两道自检，任何一条不过就不该生成 SQL。
_probe_context = build_supervisor_render_context({"symbol": "ETHUSDT", "runtime_config": {}})
_missing = [name for name in PLACEHOLDERS if name not in _probe_context]
assert not _missing, f"模板占位符在渲染上下文里不存在，会被替换成空串: {_missing}"
assert "sizing_constraints_json" in PLACEHOLDERS, "模板丢了仓位约束"

_instruction_head = CONTENT.split("PREVIOUS SUPERVISOR DECISIONS")[0]
assert "{" not in _instruction_head and "}" not in _instruction_head, "指令段含花括号，渲染器会吃掉"


def sql_str(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


VARIABLES = ",".join(PLACEHOLDERS)
VARIABLES_COL = VARIABLES if len(VARIABLES) <= 255 else "see_content_placeholders"

REMARK = (
    "Supervisor instruction block. Generated from "
    "trade_runtime/prompting/supervisor_template.py - do not hand-edit, "
    "regenerate instead. Content must stay free of literal curly braces: the "
    "renderer substitutes every placeholder it finds and drops unknown ones. "
    "Requires sizing_constraints_json in build_supervisor_render_context."
)

BINDING_REMARK = (
    "Global supervisor binding. binding_scope SUPERVISOR maps to agent_code "
    "supervisor_agent in TradeRuntimeConfigServiceImpl, which overrides the "
    "agent profile default_template_code. Empty scope json matches every mode "
    "and event strength."
)

out = []
out.append("-- 由 gen_seed.py 从 prompting/supervisor_template.py 生成，不要手改。")
out.append("")
# prompt_template.code 上只有非唯一索引（idx_prompt_template_code），
# 所以 ON DUPLICATE KEY UPDATE 不会触发——重复执行会不断插入同 code 的新行，
# 而 selectPromptTemplateByCode 是 order by version desc limit 1，故障会表现成
# "改了模板但没生效"。改用 UPDATE + 条件 INSERT，两者都幂等。
out.append("-- code 上没有唯一索引，所以先更新、再按不存在插入，而不是 upsert。")
out.append("UPDATE prompt_template SET")
out.append(f"  name = {sql_str(SUPERVISOR_TEMPLATE_NAME)},")
out.append(f"  content = {sql_str(CONTENT)},")
out.append(f"  variables = {sql_str(VARIABLES_COL)},")
out.append("  version = version + 1, is_active = 1, is_default = 1,")
out.append(f"  remark = {sql_str(REMARK)},")
out.append("  update_by = 'handoff', update_time = NOW()")
out.append(f"WHERE code = {sql_str(SUPERVISOR_TEMPLATE_CODE)};")
out.append("")
out.append("INSERT INTO prompt_template")
out.append("  (code, name, content, variables, version, is_active, is_default,")
out.append("   remark, create_by, create_time, update_by, update_time)")
out.append("SELECT")
out.append(f"  {sql_str(SUPERVISOR_TEMPLATE_CODE)},")
out.append(f"  {sql_str(SUPERVISOR_TEMPLATE_NAME)},")
out.append(f"  {sql_str(CONTENT)},")
out.append(f"  {sql_str(VARIABLES_COL)},")
out.append("  1, 1, 1,")
out.append(f"  {sql_str(REMARK)},")
out.append("  'handoff', NOW(), 'handoff', NOW()")
out.append("WHERE NOT EXISTS (")
out.append("  SELECT 1 FROM (SELECT code FROM prompt_template) AS existing")
out.append(f"  WHERE existing.code = {sql_str(SUPERVISOR_TEMPLATE_CODE)}")
out.append(");")
out.append("")
out.append("INSERT INTO trade_prompt_binding")
out.append("  (binding_name, strategy_id, strategy_version_id, symbol, exchange_code, binding_scope,")
out.append("   template_code, fallback_template_code, model_id, output_schema_code, priority,")
out.append("   mode_scope_json, event_strength_scope_json, enabled, remark, created_at, updated_at)")
out.append("SELECT 'supervisor-entry-discipline-global', NULL, NULL, NULL, NULL, 'SUPERVISOR',")
out.append(f"  {sql_str(SUPERVISOR_TEMPLATE_CODE)}, NULL, NULL, NULL, 100, '[]', '[]', 1,")
out.append(f"  {sql_str(BINDING_REMARK)},")
out.append("  NOW(), NOW()")
out.append("WHERE NOT EXISTS (")
out.append("  SELECT 1 FROM (SELECT * FROM trade_prompt_binding) AS existing")
out.append(f"  WHERE existing.binding_scope = 'SUPERVISOR' AND existing.template_code = {sql_str(SUPERVISOR_TEMPLATE_CODE)}")
out.append(");")

sys.stdout.write("\n".join(out) + "\n")
sys.stderr.write(
    f"模板 {SUPERVISOR_TEMPLATE_CODE}: 正文 {len(CONTENT)} 字符, 占位符 {len(PLACEHOLDERS)} 个, 自检通过\n"
)
