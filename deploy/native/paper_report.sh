#!/usr/bin/env bash
#
# 模拟盘周报：判断这套系统是否值得接真钱。
#
#   ./paper_report.sh          最近 7 天
#   ./paper_report.sh 1        最近 1 天
#
# 关注的不是「赚了多少」——一周的样本量说明不了收益率。要看的是：
# 决策漏斗有没有在正常收窄、成交是否真的发生、风控拦了什么、
# 以及 LLM 花的钱与产出是否成比例。

set -euo pipefail
DAYS="${1:-7}"
DB="${DB:-ai_trading}"

q() { mysql -N -B -e "$1" "$DB" 2>/dev/null; }
line() { printf '%s\n' "────────────────────────────────────────────────────────"; }
say()  { printf '  %-30s %s\n' "$1" "$2"; }

SINCE="DATE_SUB(NOW(), INTERVAL $DAYS DAY)"

echo
echo "模拟盘周报（最近 ${DAYS} 天）  $(date '+%F %H:%M')"
line

# ── 账户 ────────────────────────────────────────────────────────────
read -r EQ PEAK DD <<<"$(q "SELECT ROUND(account_equity,4), ROUND(IFNULL(peak_account_equity,account_equity),4), ROUND(IFNULL(max_drawdown_pct,0),3)
  FROM pnl_snapshot ORDER BY id DESC LIMIT 1" || echo "- - -")"
START=$(q "SELECT ROUND(account_equity,4) FROM pnl_snapshot ORDER BY id ASC LIMIT 1")
echo "账户"
say "起始权益" "${START:-—} USDT"
say "当前权益" "${EQ:-—} USDT"
if [ -n "${START:-}" ] && [ -n "${EQ:-}" ]; then
  say "收益" "$(awk -v a="$START" -v b="$EQ" 'BEGIN{ p=0; if (a>0) p=(b-a)/a*100; printf "%+.4f USDT  (%+.2f%%)", b-a, p }')"
fi
say "峰值权益 / 最大回撤" "${PEAK:-—} USDT / ${DD:-—}%"
line

# ── 成交 ────────────────────────────────────────────────────────────
FILLS=$(q "SELECT COUNT(*) FROM exchange_fill WHERE created_at > $SINCE")
CLOSED=$(q "SELECT COUNT(*) FROM trade_lifecycle WHERE exit_time IS NOT NULL AND created_at > $SINCE")
echo "成交"
say "成交笔数" "${FILLS:-0}"
say "完整平仓轮次" "${CLOSED:-0}"
if [ "${CLOSED:-0}" -gt 0 ]; then
  WIN=$(q "SELECT COUNT(*) FROM trade_lifecycle WHERE exit_time IS NOT NULL AND realized_pnl_pct > 0 AND created_at > $SINCE")
  AVG=$(q "SELECT ROUND(AVG(realized_pnl_pct),4) FROM trade_lifecycle WHERE exit_time IS NOT NULL AND created_at > $SINCE")
  HOLD=$(q "SELECT ROUND(AVG(holding_minutes),1) FROM trade_lifecycle WHERE exit_time IS NOT NULL AND created_at > $SINCE")
  say "胜率" "$WIN / $CLOSED  ($(awk -v w="$WIN" -v c="$CLOSED" 'BEGIN{ if (c>0) printf "%.0f%%", w/c*100; else printf "0%%" }'))"
  say "单笔平均收益" "${AVG:-—}%"
  say "平均持仓时长" "${HOLD:-—} 分钟"
else
  echo "    ⚠ 本期没有完整的开仓到平仓，收益类指标无法计算。"
fi
line

# ── 决策漏斗 ────────────────────────────────────────────────────────
echo "决策漏斗（收窄比例是否合理，比绝对数量更重要）"
TOTAL=$(q "SELECT COUNT(*) FROM decision_run WHERE created_at > $SINCE")
say "决策总数" "${TOTAL:-0}"
q "SELECT CONCAT(IFNULL(NULLIF(dispatch_mode,''),'(空)'),'|',COUNT(*)) FROM decision_run
   WHERE created_at > $SINCE GROUP BY dispatch_mode ORDER BY COUNT(*) DESC" |
while IFS='|' read -r mode cnt; do
  say "  $mode" "$cnt  ($(awk -v c="$cnt" -v t="${TOTAL:-1}" 'BEGIN{ if (t>0) printf "%.2f%%", c/t*100; else printf "0%%" }'))"
done
echo "  动作分布"
q "SELECT CONCAT(IFNULL(NULLIF(action,''),'(空)'),'|',COUNT(*)) FROM decision_run
   WHERE created_at > $SINCE AND dispatch_mode='LLM_ALLOWED' GROUP BY action ORDER BY COUNT(*) DESC" |
while IFS='|' read -r act cnt; do say "    $act" "$cnt"; done
line

# ── 风控 ────────────────────────────────────────────────────────────
echo "风控拦截"
BLOCKS=$(q "SELECT COUNT(*) FROM risk_guard_hit WHERE created_at > $SINCE")
say "拦截总数" "${BLOCKS:-0}"
q "SELECT CONCAT(rule_code,'|',COUNT(*)) FROM risk_guard_hit
   WHERE created_at > $SINCE GROUP BY rule_code ORDER BY COUNT(*) DESC LIMIT 6" |
while IFS='|' read -r rule cnt; do say "  $rule" "$cnt"; done
line

# ── 成本 ────────────────────────────────────────────────────────────
echo "LLM 成本（与收益对比，判断这套决策是否养得起）"
CALLS=$(q "SELECT COUNT(*) FROM audit_ai_call_log WHERE create_time > $SINCE")
TOK=$(q "SELECT IFNULL(SUM(total_tokens),0) FROM audit_ai_call_log WHERE create_time > $SINCE")
FAIL=$(q "SELECT COUNT(*) FROM audit_ai_call_log WHERE create_time > $SINCE AND status <> 1")
say "调用次数" "${CALLS:-0}  (失败 ${FAIL:-0})"
say "消耗 tokens" "${TOK:-0}"
if [ "${CALLS:-0}" -gt 0 ]; then
  say "日均调用" "$(awk -v c="$CALLS" -v d="$DAYS" 'BEGIN{printf "%.1f 次/天", c/d}')"
fi
line

# ── 数据源 ──────────────────────────────────────────────────────────
echo "数据源健康（信号缺失会让模型倾向于不交易）"
for src in news onchain social; do
  bad=$(q "SELECT COUNT(*) FROM event_raw WHERE event_type='source_health'
      AND created_at > $SINCE
      AND JSON_UNQUOTE(JSON_EXTRACT(payload_json,'\$.source_name'))='$src'
      AND JSON_UNQUOTE(JSON_EXTRACT(payload_json,'\$.source_status')) NOT IN ('ready','ready_empty')")
  tot=$(q "SELECT COUNT(*) FROM event_raw WHERE event_type='source_health'
      AND created_at > $SINCE
      AND JSON_UNQUOTE(JSON_EXTRACT(payload_json,'\$.source_name'))='$src'")
  say "  $src 异常占比" "$(awk -v b="${bad:-0}" -v t="${tot:-0}" 'BEGIN{printf "%d/%d", b, t}')"
done
line

echo "判断口径"
echo "  · 完整平仓轮次为 0 → 这一周不足以支持任何实盘结论，先解决为什么不开仓"
echo "  · LLM_ALLOWED 占比长期低于 1% → 门控过紧，考虑放宽触发阈值"
echo "  · 拦截几乎全为 market_source_abnormal → 是数据链路问题，不是策略问题"
echo "  · 有成交但胜率与单笔收益接近随机 → 阈值未经校准，先做回测再谈实盘"
echo
