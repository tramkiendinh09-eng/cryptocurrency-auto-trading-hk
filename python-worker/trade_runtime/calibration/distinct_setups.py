#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""163 个 ready 是「163 次机会」还是「163 根 K 线」？

回测逐根 15m 扫描，同一次突破会连续若干根都判 ready，而线上有去重和冷却
把它们收敛成一次派发。不区分这两者就会得出「线上漏掉了大量机会」的错误
结论——那正是上一轮拿 2 笔亏损推规律犯的同一类错。

做法：把同标的、同方向、间隔在 cooldown 之内的连续 ready 合并成一次机会。
"""
import json
from collections import defaultdict

GAP_MS = 300 * 1000  # 线上 cooldownPolicy.globalSeconds = 300

rows = json.load(open('/tmp/macro_ts.json', encoding='utf-8'))
by_key = defaultdict(list)
for r in rows:
    by_key[(r['symbol'], r['bias'])].append(r)

total_bars = len(rows)
setups = []
for key, items in by_key.items():
    items.sort(key=lambda x: x['t'])
    cur = None
    for it in items:
        if cur is not None and it['t'] - cur['t_last'] <= GAP_MS:
            cur['t_last'] = it['t']
            cur['bars'] += 1
            continue
        if cur is not None:
            setups.append(cur)
        cur = {'symbol': key[0], 'bias': key[1], 't': it['t'], 't_last': it['t'],
               'bars': 1, 'ret': it['ret']}
    if cur is not None:
        setups.append(cur)

days = 30
symbols = len({r['symbol'] for r in rows})
print('ready 的 K 线根数        %d' % total_bars)
print('合并后的独立机会数      %d' % len(setups))
print('平均每次机会持续        %.1f 根 15m' % (total_bars / max(len(setups), 1)))
print()
print('每标的每天独立机会      %.2f 次' % (len(setups) / symbols / days))
print('折算到线上 12 个标的    %.1f 次/天' % (len(setups) / symbols / days * 12))
print()
print('线上近 7 天实际开仓     7 次 = 1.0 次/天')
