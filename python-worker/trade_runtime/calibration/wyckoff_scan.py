#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把生产的 Wyckoff 短线判定跑在 30 天历史上，看 trade_readiness 的分布。

线上 8000+ 次决策 100% 是 SKIP，模型给的理由几乎全部指向
trade_readiness = avoid / watch。要判断这是「行情确实没机会」还是
「入场条件根本不可能满足」，只能把这个判定本身放到历史上量一遍。

判定复用生产的 analyze_wyckoff_shortterm，本文件不复制任何一条规则。
务必用 --config 传入线上参数：模块默认值与线上不一致，不传会高估 ready。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter

sys.path.insert(0, '/opt/dca/src/python-worker')
from trade_runtime.calibration.history import load_history
from trade_runtime.strategy.wyckoff_shortterm import analyze_wyckoff_shortterm

CACHE = '/opt/dca/calibration-cache'


def resample(candles, minutes):
    """1m K 线聚合成 N 分钟。字段沿用 history 的命名。"""
    out, bucket = [], None
    step = minutes * 60_000
    for c in candles:
        ts = int(c.get('open_time') or 0)
        key = ts - (ts % step)
        if bucket is None or bucket['open_time'] != key:
            if bucket is not None:
                out.append(bucket)
            bucket = {
                'open_time': key,
                'open': c['open'], 'high': c['high'],
                'low': c['low'], 'close': c['close'],
                'quote_volume': float(c.get('quote_volume') or 0),
            }
        else:
            bucket['high'] = max(bucket['high'], c['high'])
            bucket['low'] = min(bucket['low'], c['low'])
            bucket['close'] = c['close']
            bucket['quote_volume'] += float(c.get('quote_volume') or 0)
    if bucket is not None:
        out.append(bucket)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', required=True)
    ap.add_argument('--days', type=int, default=30)
    ap.add_argument('--out', default='')
    ap.add_argument('--config', default='',
                    help='线上 wyckoff 参数的 JSON；不传会用模块默认值，结果不可比')
    args = ap.parse_args()

    cfg = None
    if args.config:
        with open(args.config, encoding='utf-8') as f:
            cfg = json.load(f)
        print('使用线上参数:', args.config)
    else:
        print('⚠ 未传 --config，使用模块默认值，与线上不可比')

    end = int(time.time() * 1000)
    start = end - args.days * 86400 * 1000
    report = {}

    for symbol in [s.strip() for s in args.symbols.split(',') if s.strip()]:
        print('\n=== %s ===' % symbol, flush=True)
        bundle = load_history(symbol, start_ms=start, end_ms=end, cache_dir=CACHE)
        c1 = sorted(bundle.candles, key=lambda x: int(x.get('open_time') or 0))
        c15 = resample(c1, 15)
        c60 = resample(c1, 60)
        print('  15m %d 根，1h %d 根' % (len(c15), len(c60)), flush=True)

        readiness, reasons, triggers = Counter(), Counter(), Counter()
        WARM = 60
        for i in range(WARM, len(c15)):
            t = c15[i]['open_time']
            hour_slice = [c for c in c60 if c['open_time'] <= t][-40:]
            res = analyze_wyckoff_shortterm(
                {'15m': c15[max(0, i - WARM):i + 1], '1h': hour_slice},
                latest_price=c15[i]['close'],
                mark_price=c15[i]['close'],
                config=cfg,
            )
            readiness[res.get('trade_readiness', '?')] += 1
            reasons[res.get('no_trade_reason') or '(无)'] += 1
            triggers[res.get('trigger', '?')] += 1

        total = max(sum(readiness.values()), 1)
        days = args.days
        print('  样本 %d 根 15m' % total)
        print('  trade_readiness 分布:')
        for k, v in readiness.most_common():
            extra = ''
            if k == 'ready':
                extra = '   → 约 %.2f 次/天' % (v / days)
            print('    %-10s %6d  (%.2f%%)%s' % (k, v, 100 * v / total, extra))
        print('  trigger 分布:')
        for k, v in triggers.most_common(5):
            print('    %-20s %6d  (%.2f%%)' % (k, v, 100 * v / total))
        print('  卡在哪一步（no_trade_reason top）:')
        for k, v in reasons.most_common(8):
            print('    %-42s %6d  (%.2f%%)' % (k, v, 100 * v / total))
        report[symbol] = {
            'total': total, 'days': days,
            'ready_per_day': round(readiness.get('ready', 0) / days, 3),
            'readiness': dict(readiness), 'triggers': dict(triggers),
            'reasons': dict(reasons),
        }

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print('\n已写入 %s' % args.out)


if __name__ == '__main__':
    main()
