#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宏观位置过滤的阈值校准。

要回答的不是「这个阈值挡掉多少笔」——挡得多必然交易少，那不说明任何问题。
要回答的是：**被挡掉的那些入场，前向收益是不是真的更差。**

做法：把过滤关掉跑一遍历史，收集全部 ready 信号连同它当时的 24h 分位，
再按线上实测的持仓时长（209 分钟）算前向收益，然后按分位分桶看收益分布。
如果高分位桶的收益确实更差，阈值就该设在收益转负的地方；如果各桶没差别，
那这个过滤只是在减少交易，不该上。

判定复用生产的 analyze_wyckoff_shortterm，本文件不复制任何一条规则。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, '/opt/dca/src/python-worker')
from trade_runtime.strategy.wyckoff_shortterm import analyze_wyckoff_shortterm  # noqa: E402

CACHE = '/opt/dca/calibration-cache'
HOLD_MINUTES = 209  # 线上两笔平仓的实测均值


def resample(candles, minutes):
    out, bucket = [], None
    step = minutes * 60_000
    for c in candles:
        ts = int(c.get('open_time') or 0)
        key = ts - (ts % step)
        if bucket is None or bucket['open_time'] != key:
            if bucket is not None:
                out.append(bucket)
            bucket = {
                'open_time': key, 'open': c['open'], 'high': c['high'],
                'low': c['low'], 'close': c['close'],
                'volume': c.get('volume', 0.0), 'quote_volume': c.get('quote_volume', 0.0),
            }
        else:
            bucket['high'] = max(bucket['high'], c['high'])
            bucket['low'] = min(bucket['low'], c['low'])
            bucket['close'] = c['close']
            bucket['volume'] += c.get('volume', 0.0)
            bucket['quote_volume'] += c.get('quote_volume', 0.0)
    if bucket is not None:
        out.append(bucket)
    return out


def latest_cache(symbol):
    files = sorted(glob.glob(os.path.join(CACHE, symbol + '_*.json')))
    return files[-1] if files else None


def scan(symbol, config):
    path = latest_cache(symbol)
    if not path:
        return []
    raw = json.load(open(path, encoding='utf-8'))
    minute = raw.get('candles') or []
    if len(minute) < 2000:
        return []
    f15 = resample(minute, 15)
    h1 = resample(minute, 60)
    # 1 分钟收盘序列，用来算前向收益（按开盘时间索引）
    closes = {int(c['open_time']): float(c['close']) for c in minute}
    times = sorted(closes)

    rows = []
    # 从有足够历史的位置开始：24h = 96 根 15m
    for i in range(96, len(f15)):
        window15 = f15[max(0, i - 96):i + 1]
        t = int(f15[i]['open_time'])
        window1h = [c for c in h1 if int(c['open_time']) <= t][-24:]
        r = analyze_wyckoff_shortterm(
            {'15m': window15, '1h': window1h},
            latest_price=float(f15[i]['close']),
            config=config,
        )
        if r.get('trade_readiness') != 'ready':
            continue
        bias = r.get('entry_bias')
        if bias not in ('bullish', 'bearish'):
            continue
        pct = r.get('range_position_pct_24h')
        if pct is None:
            continue
        entry_t = t + 15 * 60_000          # 下一根 15m 开盘进场
        exit_t = entry_t + HOLD_MINUTES * 60_000
        e = closes.get(entry_t - (entry_t % 60_000))
        x = closes.get(exit_t - (exit_t % 60_000))
        if not e or not x:
            continue
        ret = (x - e) / e * 100.0
        if bias == 'bearish':
            ret = -ret
        rows.append({'symbol': symbol, 'bias': bias, 'pct': float(pct), 'ret': ret, 't': t})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', required=True)
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    # 关掉过滤，才能拿到全部 ready 信号（含会被否决的那些）
    config = {'macroPositionEnabled': False}

    rows = []
    for s in args.symbols.split(','):
        got = scan(s.strip(), config)
        print('%-14s ready 样本 %d' % (s.strip(), len(got)))
        rows.extend(got)

    if not rows:
        print('没有样本，无法给出结论')
        return

    print('\n持仓 %d 分钟的前向收益，按 24h 区间分位分桶' % HOLD_MINUTES)
    print('%-14s %6s %9s %9s %8s' % ('分位桶', '样本', '均收益%', '中位数%', '胜率'))
    buckets = defaultdict(list)
    for r in rows:
        b = min(int(r['pct'] * 5), 4)      # 0-0.2, 0.2-0.4, ... 0.8-1.0
        buckets[b].append(r['ret'])
    for b in sorted(buckets):
        v = sorted(buckets[b])
        n = len(v)
        mean = sum(v) / n
        med = v[n // 2]
        win = sum(1 for x in v if x > 0) / n * 100
        print('%-14s %6d %9.3f %9.3f %7.1f%%' % (
            '%.1f~%.1f' % (b / 5, (b + 1) / 5), n, mean, med, win))

    print('\n多空分开看（只有做多才受高分位否决影响）')
    for bias in ('bullish', 'bearish'):
        sub = [r for r in rows if r['bias'] == bias]
        if not sub:
            continue
        hi = [r['ret'] for r in sub if r['pct'] >= 0.8]
        lo = [r['ret'] for r in sub if r['pct'] < 0.8]
        f = lambda v: (len(v), sum(v) / len(v) if v else 0.0)
        print('  %-8s 分位>=0.8: n=%d 均%.3f%%   分位<0.8: n=%d 均%.3f%%' % (
            bias, *f(hi), *f(lo)))

    if args.out:
        json.dump(rows, open(args.out, 'w', encoding='utf-8'))
        print('\n明细已写入 %s' % args.out)


if __name__ == '__main__':
    main()
