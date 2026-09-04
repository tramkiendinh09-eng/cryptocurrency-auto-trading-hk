#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回测正收益、线上却亏钱——差距在样本量还是在执行。

163 个 ready 信号的前向收益分布由 macro_position_scan 产出，这里回答：
  1. 这个分布的均值真的显著大于 0，还是被方差淹没了？
  2. 线上那 2 笔全亏，在这个分布下有多正常？
  3. 要多少笔才能把「有优势」和「运气」分开？

注意：算的是固定持仓、不带止损的裸信号收益，衡量的是信号本身而非策略。
"""
import json
import math
import statistics as st

rows = json.load(open('/tmp/macro.json', encoding='utf-8'))
rets = [r['ret'] for r in rows]
n = len(rets)
mean = st.mean(rets)
sd = st.pstdev(rets)
se = sd / math.sqrt(n)
t = mean / se if se else 0.0
win = sum(1 for x in rets if x > 0) / n

line = '=' * 62
print(line)
print('30 天历史 Wyckoff ready 信号的前向收益（209 分钟持仓，未计费）')
print(line)
print(f'  样本数            {n}')
print(f'  均值              {mean:+.4f}%')
print(f'  中位数            {st.median(rets):+.4f}%')
print(f'  标准差            {sd:.4f}%')
print(f'  标准误            {se:.4f}%')
print(f'  t 值              {t:.2f}   ' + ('显著' if abs(t) > 1.96 else '不显著'))
print(f'  胜率              {win * 100:.1f}%')
print(f'  最好 / 最差       {max(rets):+.2f}% / {min(rets):+.2f}%')

FEE = 0.08  # 币安 U 本位吃单双边约 0.08% 名义
net = mean - FEE
print(f'\n  扣双边手续费 0.08% 后   {net:+.4f}%   ' + ('仍为正' if net > 0 else '转负'))

print('\n' + line)
print('线上 2 笔全亏，有多正常')
print(line)
p_loss = 1 - win
print(f'  单笔亏损概率      {p_loss * 100:.1f}%')
print(f'  连亏 2 笔概率     {p_loss ** 2 * 100:.1f}%   ' +
      ('← 完全在正常范围内' if p_loss ** 2 > 0.15 else ''))
for k in (3, 5):
    print(f'  连亏 {k} 笔概率     {p_loss ** k * 100:.1f}%')

print('\n' + line)
print('要多少笔才能把「有优势」和「运气」分开')
print(line)
for tt, label in ((1.96, '95%'), (2.58, '99%')):
    need = math.ceil((tt * sd / mean) ** 2) if mean else 0
    print(f'  {label} 置信度需要      {need} 笔')
if net > 0:
    need_net = math.ceil((1.96 * sd / net) ** 2)
    print(f'  扣费后 95% 需要      {need_net} 笔')
else:
    print('  扣费后 95% 需要      均值转负，无解')

need95 = math.ceil((1.96 * sd / mean) ** 2) if mean else 0
rate = 5 / 7  # 近 7 天 5 次开仓
print(f'\n  线上当前            2 笔')
print(f'  按当前开仓节奏攒够    约 {math.ceil(need95 / rate)} 天')
