#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""错过的机会,按钱算。

不数「挡掉多少个信号」——挡得多必然交易少,那不说明任何问题。要算的是
被挡掉的那些入场,按线上实测的 209 分钟持仓,本来会赚多少或亏多少。

每条 ready 信号按它实际走到哪一步分组:
  到达模型并开仓 / 到达模型但被 SKIP / 被冷却挡掉 / 被预算挡掉 / 未分发
"""
import json
import subprocess
import statistics as st
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

HOLD_MIN = 209
FEE = 0.08
LEVERAGE = 10.0          # 当前配置
NOTIONAL = 400.0         # 10 倍 x 0.40 仓位 x 100 USDT 权益


def q(sql):
    out = subprocess.run(["mysql", "-N", "-B", "-e", sql, "ai_trading"],
                         capture_output=True, text=True, check=True).stdout
    parsed = []
    for line in out.strip().split(chr(10)):
        if not line.strip():
            continue
        # 末尾的空字段会被 split 丢掉，补齐到固定列数
        cols = line.split(chr(9))
        parsed.append(cols + [""] * (8 - len(cols)))
    return parsed


rows = q("""
SELECT s.symbol,
       UNIX_TIMESTAMP(s.created_at) * 1000,
       JSON_UNQUOTE(JSON_EXTRACT(s.feature_json, '$.wyckoff_shortterm.entry_bias')),
       COALESCE(d.dispatch_mode, ''),
       COALESCE(d.action, ''),
       COALESCE(d.budget_blocked, 0),
       COALESCE(d.cooldown_blocked, 0),
       COALESCE(d.prompt_source, '')
FROM signal_event s
LEFT JOIN decision_run d ON d.trace_id = s.trace_id
WHERE JSON_UNQUOTE(JSON_EXTRACT(s.feature_json, '$.wyckoff_shortterm.trade_readiness')) = 'ready'
ORDER BY s.created_at
""")
print("ready 信号总数: %d" % len(rows))

# MySQL 存的是 +08:00 本地时间,UNIX_TIMESTAMP 已按会话时区换算成 UTC 毫秒
symbols = sorted({r[0] for r in rows})
klines = {}
for sym in symbols:
    try:
        merged = {}
        # 一次最多 1500 根 1m（25 小时），信号跨了两天多，按 startTime 分页拉
        start = min(int(r[1]) for r in rows if r[0] == sym) - 3600_000
        while True:
            url = ("https://fapi.binance.com/fapi/v1/klines?symbol=%s&interval=1m"
                   "&limit=1500&startTime=%d" % (sym, start))
            data = json.load(urllib.request.urlopen(url, timeout=25))
            if not data:
                break
            merged.update({int(k[0]): float(k[4]) for k in data})
            nxt = int(data[-1][0]) + 60_000
            if nxt <= start or len(data) < 1500:
                break
            start = nxt
        klines[sym] = merged
    except Exception as exc:
        print("  %s 行情拉取失败: %s" % (sym, exc))

covered = min((min(v) for v in klines.values() if v), default=0)
print("行情覆盖起点: %s UTC(1m K 线上限 1500 根)" %
      datetime.fromtimestamp(covered / 1000, tz=timezone.utc).strftime("%m-%d %H:%M"))


def bucket(dispatch, action, budget_blocked, cooldown_blocked):
    if action in ("OPEN_LONG", "OPEN_SHORT"):
        return "已开仓"
    if int(cooldown_blocked or 0):
        return "被冷却挡掉"
    if int(budget_blocked or 0):
        return "被预算挡掉"
    if dispatch == "LLM_ALLOWED":
        return "模型看过后 SKIP"
    if dispatch in ("RULE_ONLY", "NO_DISPATCH"):
        return "未分发到模型"
    return "其它"


groups = defaultdict(list)
no_data = 0
for symbol, ts_ms, bias, dispatch, action, bb, cb, psrc in rows:
    ts = int(ts_ms)
    if bias not in ("bullish", "bearish"):
        continue
    prices = klines.get(symbol)
    if not prices:
        no_data += 1
        continue
    entry_key = ts - (ts % 60000)
    exit_key = entry_key + HOLD_MIN * 60000
    entry = prices.get(entry_key)
    exit_price = prices.get(exit_key)
    if entry is None or exit_price is None:
        no_data += 1
        continue
    ret = (exit_price - entry) / entry * 100.0
    if bias == "bearish":
        ret = -ret
    groups[bucket(dispatch, action, bb, cb)].append(ret - FEE)

print("行情窗口外/无数据,无法核算: %d 条" % no_data)
print()
line = "=" * 78
print(line)
print("%-18s %6s %10s %10s %8s %14s" % ("去向", "样本", "均收益%", "中位数%", "胜率", "折合盈亏 USDT"))
print(line)
total_missed = 0.0
for name in ("已开仓", "模型看过后 SKIP", "被冷却挡掉", "被预算挡掉", "未分发到模型"):
    v = groups.get(name) or []
    if not v:
        print("%-18s %6d %10s" % (name, 0, "—"))
        continue
    mean = st.mean(v)
    med = st.median(v)
    win = sum(1 for x in v if x > 0) / len(v) * 100
    pnl = sum(x / 100.0 * NOTIONAL for x in v)
    print("%-18s %6d %10.4f %10.4f %7.1f%% %14.1f" % (name, len(v), mean, med, win, pnl))
    if name != "已开仓":
        total_missed += pnl
print(line)
print("被挡掉的合计折合盈亏: %+.1f USDT（按当前 10 倍杠杆、单笔名义 %.0f USDT 计）" %
      (total_missed, NOTIONAL))
print("账户权益 100 USDT,即 %+.1f%%" % total_missed)
