#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ready 和 watch 的优势对比 —— 决定 watch 该不该占用 LLM 预算。

两者在 trigger_policy 里拿的都是 LLM_ALLOWED，而 watch 数量约是 ready 的
8 倍，等于把预算大部分喂给了「结构成立但差一项确认」的信号。ready 已经
验过有优势（t=3.11）；watch 有没有，决定了预算该整体放大还是该重新分配。
"""
import json
import math
import statistics as st
from collections import defaultdict

rows = json.load(open('/tmp/rw.json', encoding='utf-8'))
groups = defaultdict(list)
for r in rows:
    groups[r.get('readiness', '?')].append(r['ret'])

FEE = 0.08
line = '=' * 74
print(line)
print('209 分钟持仓的前向收益，按 trade_readiness 分组')
print(line)
print('%-8s %6s %10s %10s %9s %8s %8s' % ('就绪度', '样本', '均值%', '中位数%', '标准差%', 't值', '胜率'))
stats = {}
for k in ('ready', 'watch'):
    v = groups.get(k) or []
    if not v:
        continue
    n = len(v)
    mean = st.mean(v)
    sd = st.pstdev(v)
    t = mean / (sd / math.sqrt(n)) if sd else 0.0
    win = sum(1 for x in v if x > 0) / n * 100
    stats[k] = (n, mean, sd, t, win)
    print('%-8s %6d %10.4f %10.4f %9.4f %8.2f %7.1f%%' % (k, n, mean, st.median(v), sd, t, win))

print()
for k, (n, mean, sd, t, win) in stats.items():
    net = mean - FEE
    verdict = '显著为正' if t > 1.96 else ('显著为负' if t < -1.96 else '与 0 无异')
    print('  %-6s t=%5.2f  %s ；扣费后 %+.4f%%  %s' % (
        k, t, verdict, net, '仍为正' if net > 0 else '转负'))

if 'ready' in stats and 'watch' in stats:
    n1, m1, s1, _, _ = stats['ready']
    n2, m2, s2, _, _ = stats['watch']
    se = math.sqrt(s1 * s1 / n1 + s2 * s2 / n2)
    tt = (m1 - m2) / se if se else 0.0
    print()
    print(line)
    print('两组差异检验')
    print(line)
    print('  ready - watch = %+.4f%%   t=%.2f   %s' % (
        m1 - m2, tt, '差异显著' if abs(tt) > 1.96 else '差异不显著'))
    print('  watch : ready 数量比 = %.1f : 1' % (n2 / n1))
    print()
    total = n1 + n2
    print('  当前预算按数量分配，watch 会拿走约 %.0f%%' % (n2 / total * 100))
    if m2 <= 0 or (m2 - FEE) <= 0:
        print('  → watch 扣费后不赚钱，占用的这部分预算是纯浪费')
    else:
        print('  → watch 扣费后仍为正，预算该整体放大而不是重新分配')
