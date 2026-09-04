#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""止损阈值校准 —— 1.2% 是不是砍在了半路。

止损是价格幅度阈值，与杠杆无关：杠杆不改变它触发的频率，只改变每次触发
亏多少钱。真正的问题是 1.2% 相对信号自身的波动够不够宽——ready 信号
209 分钟持仓的收益标准差是 1.60%，1.2% 只有 0.75 个标准差。

做法：对每个 ready 信号逐分钟走一遍持仓窗口，记录最大不利偏移(MAE)与
最大有利偏移(MFE)，再在不同止损位下重算最终收益。触发止损就按止损价
结算，否则按到期价结算。
"""
import argparse
import glob
import json
import os
import statistics as st
import sys

sys.path.insert(0, '/opt/dca/src/python-worker')
from trade_runtime.strategy.wyckoff_shortterm import analyze_wyckoff_shortterm  # noqa: E402

CACHE = '/opt/dca/calibration-cache'
HOLD_MIN = 209
FEE = 0.08


def resample(candles, minutes):
    out, bucket = [], None
    step = minutes * 60_000
    for c in candles:
        ts = int(c.get('open_time') or 0)
        key = ts - (ts % step)
        if bucket is None or bucket['open_time'] != key:
            if bucket is not None:
                out.append(bucket)
            bucket = {'open_time': key, 'open': c['open'], 'high': c['high'],
                      'low': c['low'], 'close': c['close'],
                      'volume': c.get('volume', 0.0), 'quote_volume': c.get('quote_volume', 0.0)}
        else:
            bucket['high'] = max(bucket['high'], c['high'])
            bucket['low'] = min(bucket['low'], c['low'])
            bucket['close'] = c['close']
            bucket['volume'] += c.get('volume', 0.0)
            bucket['quote_volume'] += c.get('quote_volume', 0.0)
    if bucket is not None:
        out.append(bucket)
    return out


def scan(symbol):
    files = sorted(glob.glob(os.path.join(CACHE, symbol + '_*.json')))
    if not files:
        return []
    raw = json.load(open(files[-1], encoding='utf-8'))
    minute = raw.get('candles') or []
    if len(minute) < 2000:
        return []
    f15 = resample(minute, 15)
    h1 = resample(minute, 60)
    idx = {int(c['open_time']): i for i, c in enumerate(minute)}

    rows = []
    for i in range(96, len(f15)):
        t = int(f15[i]['open_time'])
        r = analyze_wyckoff_shortterm(
            {'15m': f15[max(0, i - 96):i + 1], '1h': [c for c in h1 if int(c['open_time']) <= t][-24:]},
            latest_price=float(f15[i]['close']),
            config={'macroPositionEnabled': False},
        )
        if r.get('trade_readiness') != 'ready':
            continue
        bias = r.get('entry_bias')
        if bias not in ('bullish', 'bearish'):
            continue
        entry_t = t + 15 * 60_000
        j = idx.get(entry_t - (entry_t % 60_000))
        if j is None or j + HOLD_MIN >= len(minute):
            continue
        entry = float(minute[j]['close'])
        sign = 1.0 if bias == 'bullish' else -1.0
        # 逐分钟走完持仓窗口，记录路径
        path = []
        for k in range(j + 1, j + 1 + HOLD_MIN):
            c = minute[k]
            # 不利极值用 low(多)/high(空)，有利极值反之——按最坏情况估止损
            adverse = (float(c['low']) - entry) / entry * 100.0 * sign
            favorable = (float(c['high']) - entry) / entry * 100.0 * sign
            path.append((adverse, favorable, (float(c['close']) - entry) / entry * 100.0 * sign))
        if not path:
            continue
        rows.append({
            'symbol': symbol, 'bias': bias,
            'mae': min(p[0] for p in path),
            'mfe': max(p[1] for p in path),
            'final': path[-1][2],
            'path': [(round(p[0], 4), round(p[2], 4)) for p in path],
        })
    return rows


def apply_stop(row, stop_pct):
    """止损位为 stop_pct（正数，价格不利幅度）。触发即按止损价结算。"""
    if stop_pct <= 0:
        return row['final']
    for adverse, close in row['path']:
        if adverse <= -stop_pct:
            return -stop_pct
    return row['final']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', required=True)
    args = ap.parse_args()

    rows = []
    for s in args.symbols.split(','):
        got = scan(s.strip())
        print('%-14s ready 样本 %d' % (s.strip(), len(got)))
        rows.extend(got)
    if not rows:
        print('无样本')
        return

    maes = sorted(r['mae'] for r in rows)
    n = len(rows)
    print()
    print('最大不利偏移(MAE)分布 —— 持仓期间最深浮亏')
    for q in (0.25, 0.5, 0.75, 0.9, 0.95):
        print('  p%-4s  %.3f%%' % (int(q * 100), maes[int(n * (1 - q))]))
    print('  最深   %.3f%%' % maes[0])

    print()
    print('不同止损位下的结果（%d 个信号，209 分钟持仓，扣双边手续费 %.2f%%）' % (n, FEE))
    print('%-10s %10s %10s %8s %10s' % ('止损位', '均收益%', '中位数%', '被扫出', '总收益%'))
    best = None
    for stop in (0.6, 0.9, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 0.0):
        outs = [apply_stop(r, stop) - FEE for r in rows]
        hit = sum(1 for r in rows if stop > 0 and r['mae'] <= -stop)
        mean = st.mean(outs)
        label = '不止损' if stop == 0 else '%.1f%%' % stop
        print('%-10s %10.4f %10.4f %7.1f%% %10.2f' % (
            label, mean, st.median(outs), hit / n * 100, sum(outs)))
        if best is None or mean > best[1]:
            best = (label, mean)
    print()
    print('  最优：%s（均收益 %+.4f%%）' % best)
    print('  当前线上：1.2%%')


if __name__ == '__main__':
    main()
