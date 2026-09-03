#!/usr/bin/env bash
#
# 新闻链路修复后的观测。
#
#   ./observe.sh          最近 24 小时
#   ./observe.sh 48       最近 48 小时
#
# 只为回答一个问题：**LLM 预算该不该调，调到多少。**
#
# 背景（见 deploy/native/CALIBRATION-MULTI.md）：回测证明放宽行情阈值
# 是无效操作，真正卡住门控的是 llmBudgetPolicy。但回测里 news 恒为 0
# （辅助源无历史），而新闻链路刚修好、输入分布刚发生量级变化 —— 所以
# 预算不能按回测定，必须用修好之后的线上实测来定。
#
# 判断口径写在最后。

set -euo pipefail
HOURS="${1:-24}"
DB="${DB:-ai_trading}"
CUT="2026-09-03 11:05:00"     # 新闻链路上线时刻，用于前后对比

q() { mysql -N -B -e "$1" "$DB" 2>/dev/null; }
line() { printf '%s\n' "────────────────────────────────────────────────────────"; }
say()  { printf '  %-28s %s\n' "$1" "$2"; }

SINCE="DATE_SUB(NOW(), INTERVAL $HOURS HOUR)"

echo
echo "门控观测（最近 ${HOURS} 小时）  $(date '+%F %H:%M')"
line

# ── 决策漏斗 ────────────────────────────────────────────────────────
read -r N ND RO LA BB CB <<<"$(q "SELECT COUNT(*),
    SUM(dispatch_mode='NO_DISPATCH'), SUM(dispatch_mode='RULE_ONLY'),
    SUM(dispatch_mode='LLM_ALLOWED'), SUM(budget_blocked), SUM(cooldown_blocked)
  FROM decision_run WHERE created_at > $SINCE")"
echo "决策漏斗"
say "决策总数" "${N:-0}"
if [ "${N:-0}" -gt 0 ]; then
  pct() { awk -v a="$1" -v b="$N" 'BEGIN{printf "%s  (%.2f%%)", a, 100*a/b}'; }
  say "  NO_DISPATCH" "$(pct "${ND:-0}")"
  say "  RULE_ONLY"   "$(pct "${RO:-0}")"
  say "  LLM_ALLOWED" "$(pct "${LA:-0}")"
fi
say "被预算挡回" "${BB:-0}"
say "被冷却挡回" "${CB:-0}"
line

# ── 这份报告的核心：真实 LLM 用量对比预算上限 ──────────────────────
echo "LLM 用量 vs 预算上限"
# 预算上限要从接口读，不能读 trade_runtime_config：库里那行只存覆盖项
# （顶层只有 maxLeverage / marketTrigger / symbolUniverse /
# marketDataEnhancement 四个键），llmBudgetPolicy 是后端代码里的默认值，
# 只有接口返回的才是合并后的完整配置。
read -r DAILY WINDOW <<<"$(curl -s -m 10 http://127.0.0.1:18081/dca/trade/runtime/config |
  python3 -c "
import sys, json
try:
    f = json.loads(json.load(sys.stdin)['data']['runtimeFlagsJson'])
    b = f.get('llmBudgetPolicy') or {}
    print(b.get('perSymbolDailyLimit', ''), b.get('rollingWindowLimit', ''))
except Exception:
    print('', '')
" 2>/dev/null)"
say "当前上限" "每标的 ${DAILY:-?} 次/天，${WINDOW:-?} 次/小时"
echo
printf '  %-14s %10s %12s %10s\n' "标的" "实际次/天" "占日上限" "被预算挡"
q "SELECT symbol,
      ROUND(SUM(dispatch_mode='LLM_ALLOWED') / ($HOURS/24), 2),
      SUM(budget_blocked)
    FROM decision_run WHERE created_at > $SINCE AND symbol <> ''
    GROUP BY symbol ORDER BY 2 DESC" |
while IFS=$'\t' read -r sym per blocked; do
  ratio=$(awk -v a="$per" -v b="${DAILY:-0}" 'BEGIN{ b=b+0; if (b>0) printf "%.0f%%", 100*a/b; else printf "—" }')
  printf '  %-14s %10s %12s %10s\n' "$sym" "$per" "$ratio" "$blocked"
done
line

# ── 调用是否健康 ────────────────────────────────────────────────────
read -r C OK FAIL TOK <<<"$(q "SELECT COUNT(*), SUM(status=1), SUM(status=0), IFNULL(SUM(total_tokens),0)
  FROM audit_ai_call_log WHERE call_time > $SINCE")"
echo "LLM 调用"
say "调用次数" "${C:-0}（成功 ${OK:-0} / 失败 ${FAIL:-0}）"
say "消耗 tokens" "${TOK:-0}"
if [ "${C:-0}" -gt 0 ]; then
  say "折合日均" "$(awk -v c="$C" -v h="$HOURS" 'BEGIN{printf "%.1f 次/天", c*24/h}')"
fi
FC=$(q "SELECT COUNT(*) FROM decision_run WHERE created_at > $SINCE AND summary_reason LIKE '%ai_model_call_failed%'")
say "fail-closed 决策" "${FC:-0}"
line

# ── 持仓风险有没有在反复问同一个问题 ────────────────────────────────
# 这一段是被 48% 的 LLM 失败率逼出来的。position_risk 事件会绕过派发冷却，
# 一度还绕过 LLM 预算，于是一笔浮亏持仓每 30 秒就把同一个问题重问一遍：
# 近 6 小时里 MU 一个标的问了 103 次、模型 82 次答 HOLD，占掉全部 LLM 派发
# 的六成，把中转网关打到 503——连真正紧急的那次问询也一起被打掉。
# 改动见 position_risk_watcher：分级冷却 + 指标要有实质变化才重新问，
# 且只有 reduce/close 才抢占预算。这里盯的就是它有没有回潮。
echo "持仓风险问询"
read -r PR PRL <<<"$(q "SELECT COUNT(*), SUM(dispatch_mode='LLM_ALLOWED')
  FROM decision_run WHERE created_at > $SINCE AND trigger_source='position_risk'")"
say "触发决策" "${PR:-0}（其中进 LLM ${PRL:-0}）"
if [ "${LA:-0}" -gt 0 ]; then
  say "占全部 LLM 派发" "$(awk -v a="${PRL:-0}" -v b="$LA" 'BEGIN{printf "%.1f%%", 100*a/b}')"
fi
q "SELECT symbol, COUNT(*), SUM(action='HOLD')
   FROM decision_run WHERE created_at > $SINCE AND trigger_source='position_risk'
     AND dispatch_mode='LLM_ALLOWED' AND symbol <> ''
   GROUP BY symbol HAVING COUNT(*) > 0 ORDER BY 2 DESC LIMIT 5" |
while IFS=$'\t' read -r sym n holds; do
  printf '      %-14s %4s 次/%s 小时，%s 次 HOLD\n' "$sym" "$n" "$HOURS" "${holds:-0}"
done
line

# ── 产出：有没有真的动手 ────────────────────────────────────────────
echo "产出"
say "非 SKIP 决策" "$(q "SELECT COUNT(*) FROM decision_run WHERE created_at > $SINCE AND action NOT IN ('SKIP','NO_ACTION') AND action <> ''")"
say "成交笔数" "$(q "SELECT COUNT(*) FROM exchange_fill WHERE created_at > $SINCE")"
line

# ── 新闻链路是否还活着 ──────────────────────────────────────────────
echo "新闻链路"
read -r NT NB <<<"$(q "SELECT COUNT(*), SUM(JSON_UNQUOTE(JSON_EXTRACT(payload_json,'\$.source_status')) NOT IN ('ready','ready_empty'))
  FROM event_raw WHERE event_type='source_health' AND created_at > $SINCE
    AND JSON_UNQUOTE(JSON_EXTRACT(payload_json,'\$.source_name'))='news'")"
say "健康检查" "${NT:-0} 次，异常 ${NB:-0} 次"
say "news 触发的决策" "$(q "SELECT COUNT(*) FROM decision_run WHERE created_at > $SINCE AND trigger_source='news'")"
line

# ── 修复前后对比 ────────────────────────────────────────────────────
echo "新闻链路修复前后（$CUT）"
printf '  %-12s %8s %12s %12s %12s\n' "阶段" "决策" "未分发占比" "进LLM占比" "news来源"
for phase in before after; do
  if [ "$phase" = before ]; then
    W="created_at < '$CUT' AND created_at > DATE_SUB('$CUT', INTERVAL $HOURS HOUR)"; label="修复前"
  else
    W="created_at >= '$CUT'"; label="修复后"
  fi
  read -r n nd la ns <<<"$(q "SELECT COUNT(*), SUM(dispatch_mode='NO_DISPATCH'),
      SUM(dispatch_mode='LLM_ALLOWED'), SUM(trigger_source='news')
    FROM decision_run WHERE $W")"
  [ "${n:-0}" -eq 0 ] && continue
  printf '  %-12s %8s %11s%% %11s%% %12s\n' "$label" "$n" \
    "$(awk -v a="${nd:-0}" -v b="$n" 'BEGIN{printf "%.1f", 100*a/b}')" \
    "$(awk -v a="${la:-0}" -v b="$n" 'BEGIN{printf "%.2f", 100*a/b}')" "${ns:-0}"
done
line

echo "判断口径"
echo "  · 多数标的「占日上限」接近 100% → 预算是瓶颈，可以按 CALIBRATION-MULTI.md"
echo "    的弹性表提高 perSymbolDailyLimit 与 rollingWindowLimit（两个要一起动，"
echo "    日上限会先撞到）"
echo "  · 「占日上限」普遍很低而成交仍为 0 → 瓶颈不在预算，在信号或策略本身，"
echo "    调预算是浪费钱"
echo "  · fail-closed 占 LLM 调用一成以上 → 先看上面这段：多半是自己把网关"
echo "    打满了，而不是网关自己坏了"
echo "  · 单个标的的持仓风险问询远多于其它标的、且几乎全是 HOLD → 冷却或"
echo "    rearmDeltaPct 太松，在拿几乎一样的数字重复问同一个问题"
echo "  · 非 SKIP 决策持续为 0 且样本已足够 → 该回头看 prompt 与入场条件，"
echo "    而不是继续放门控"
echo
