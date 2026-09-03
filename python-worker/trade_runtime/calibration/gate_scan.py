#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨标的的门控频次评估。

上一轮校准只做了 BTCUSDT，而 BTCUSDT 已经不在 allowedSymbols 里了——
现行阈值在真正参与交易的 12 个标的上从来没有被量过。

判定全部走生产的 trigger_policy（经 calibration.replay），本文件不复制
任何一条阈值比较逻辑。评价口径沿用上一轮报告的结论：**看门控频次，
不看方向命中率**——触发策略的职责是决定"此刻值不值得花一次 LLM 调用"。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, '/opt/dca/src/python-worker')

from trade_runtime.calibration.history import load_history
from trade_runtime.calibration.replay import build_frames, evaluate_frames

CACHE = '/opt/dca/calibration-cache'


def load_live_config() -> dict:
    """线上现行的 runtimeFlags，作为基线。"""
    import urllib.request
    with urllib.request.urlopen('http://127.0.0.1:18081/dca/trade/runtime/config', timeout=20) as r:
        data = json.loads(r.read())['data']
    return json.loads(data['runtimeFlagsJson'])


def gate_metrics(frames, config, days: float) -> dict:
    result = evaluate_frames(frames, runtime_config=config, strategy_context=None)
    counts: dict[str, int] = {}
    types: dict[str, int] = {}
    cooldown = budget = 0
    for step in result.steps:
        counts[step.dispatch_mode] = counts.get(step.dispatch_mode, 0) + 1
        if step.dispatch_mode == 'NO_DISPATCH':
            continue
        for t in step.signal_types:
            types[t] = types.get(t, 0) + 1
        cooldown += bool(step.cooldown_blocked)
        budget += bool(step.budget_blocked)
    llm = counts.get('LLM_ALLOWED', 0)
    disp = llm + counts.get('RULE_ONLY', 0)
    return {
        'llm_per_day': round(llm / days, 2),
        'dispatch_per_day': round(disp / days, 2),
        'llm_total': llm,
        'dispatch_total': disp,
        'cooldown_blocked': cooldown,
        'budget_blocked': budget,
        'signal_types': types,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', required=True)
    ap.add_argument('--days', type=int, default=30)
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    live = load_live_config()
    base_market = dict(live.get('marketTrigger') or {})
    print('线上现行 marketTrigger:', json.dumps(base_market, ensure_ascii=False))

    def cfg(**over):
        c = json.loads(json.dumps(live))
        c['marketTrigger'] = {**base_market, **over}
        return c

    # 候选：只动主价格阈值这一个维度，其余保持不变。
    # 上一轮报告已经证明 markPriceDeviationPct 与 fundingRateAbs 的取值,
    # 这里不重复推翻；priceChangePct 是原作者定的、从未被检验过的值。
    CONFIGS = {
        '现行 2.5': cfg(),
        '2.0': cfg(priceChangePct=2.0),
        '1.5': cfg(priceChangePct=1.5),
        '1.2': cfg(priceChangePct=1.2),
        '1.0': cfg(priceChangePct=1.0),
        '0.8': cfg(priceChangePct=0.8),
    }

    end = int(time.time() * 1000)
    start = end - args.days * 86400 * 1000
    out: dict = {'generated_at': datetime.now(timezone.utc).isoformat(),
                 'days': args.days, 'base_market_trigger': base_market, 'symbols': {}}

    for symbol in args.symbols.split(','):
        symbol = symbol.strip()
        if not symbol:
            continue
        print(f'\n=== {symbol} ===', flush=True)
        t0 = time.time()
        bundle = load_history(symbol, start_ms=start, end_ms=end, cache_dir=CACHE)
        frames = build_frames(bundle, warmup_bars=500)
        days = max(0.0001, len(bundle.candles) / 1440.0)
        print(f'  帧 {len(frames.frames)} 个，覆盖 {days:.1f} 天，建帧耗时 {time.time()-t0:.0f}s', flush=True)
        out['symbols'][symbol] = {'days': round(days, 2), 'configs': {}}
        for label, config in CONFIGS.items():
            m = gate_metrics(frames, config, days)
            out['symbols'][symbol]['configs'][label] = m
            print(f'  {label:<10} LLM {m["llm_per_day"]:>6}/天   分发 {m["dispatch_per_day"]:>6}/天'
                  f'   冷却挡 {m["cooldown_blocked"]:>4}  预算挡 {m["budget_blocked"]:>4}', flush=True)

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f'\n已写入 {args.out}')


if __name__ == '__main__':
    main()
