#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预算侧扫描。

价格阈值那一轮的结论是：把 priceChangePct 从 2.5 放宽到 0.8，
LLM 频次几乎不动、分发数完全不动，而「预算挡」从 303 涨到 426 ——
说明卡住门控的是 llmBudgetPolicy，不是行情阈值。放宽阈值只会制造
更多被预算挡掉的信号。

这里改扫预算本身的两个参数：
  rollingWindowLimit —— 每 rollingWindowMinutes 内允许几次
  perSymbolDailyLimit —— 每标的每天上限
"""
from __future__ import annotations

import argparse, json, sys, time
from datetime import datetime, timezone

sys.path.insert(0, '/opt/dca/src/python-worker')
from trade_runtime.calibration.history import load_history
from trade_runtime.calibration.replay import build_frames

sys.path.insert(0, '/opt/dca/src/python-worker/trade_runtime/calibration')
from gate_scan import gate_metrics, load_live_config   # noqa: E402

CACHE = '/opt/dca/calibration-cache'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', required=True)
    ap.add_argument('--days', type=int, default=30)
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    live = load_live_config()
    base_budget = dict(live.get('llmBudgetPolicy') or {})
    print('线上现行 llmBudgetPolicy:', json.dumps(base_budget, ensure_ascii=False))

    def cfg(**over):
        c = json.loads(json.dumps(live))
        c['llmBudgetPolicy'] = {**base_budget, **over}
        return c

    CONFIGS = {
        '现行 2次/时,6次/天': cfg(),
        '3次/时,6次/天':     cfg(rollingWindowLimit=3),
        '4次/时,8次/天':     cfg(rollingWindowLimit=4, perSymbolDailyLimit=8),
        '6次/时,12次/天':    cfg(rollingWindowLimit=6, perSymbolDailyLimit=12),
        '10次/时,20次/天':   cfg(rollingWindowLimit=10, perSymbolDailyLimit=20),
    }

    end = int(time.time() * 1000)
    start = end - args.days * 86400 * 1000
    out: dict = {'generated_at': datetime.now(timezone.utc).isoformat(),
                 'days': args.days, 'base_budget': base_budget, 'symbols': {}}

    for symbol in [s.strip() for s in args.symbols.split(',') if s.strip()]:
        print(f'\n=== {symbol} ===', flush=True)
        bundle = load_history(symbol, start_ms=start, end_ms=end, cache_dir=CACHE)
        frames = build_frames(bundle, warmup_bars=500)
        days = max(0.0001, len(bundle.candles) / 1440.0)
        out['symbols'][symbol] = {'days': round(days, 2), 'configs': {}}
        for label, config in CONFIGS.items():
            m = gate_metrics(frames, config, days)
            out['symbols'][symbol]['configs'][label] = m
            print(f'  {label:<18} LLM {m["llm_per_day"]:>6}/天   分发 {m["dispatch_per_day"]:>6}/天'
                  f'   预算挡 {m["budget_blocked"]:>4}  冷却挡 {m["cooldown_blocked"]:>4}', flush=True)

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f'\n已写入 {args.out}')


if __name__ == '__main__':
    main()
