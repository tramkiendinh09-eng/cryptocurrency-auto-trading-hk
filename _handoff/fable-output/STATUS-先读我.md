# 状态说明 —— 动手改写前先读这一份

`fable-output/` 是上一个模型按 `_handoff/0-任务说明.md` 交付的成果。**其中任务二已经上线，任务一和三还没动。**
但更重要的是：**任务说明本身的一条核心假设，在那之后被 30 天回测推翻了。** 照着 README 原样执行会把一条被证伪的规则写死进提示词。

## 当前状态

| 交付物 | 对应任务 | 状态 |
|---|---|---|
| `wyckoff_shortterm.py` | 二 | **已上线**（提交 `bad576d`），但 `macroPositionEnabled=false` |
| `supervisor_prompt_builder.py` | 一 | 未动 |
| `prompt_template_seed.sql` / `generate_template_seed.py` | 三 | 未动 |
| README 里的 `render_context_builder.py` 补丁 | 三的前置 | 未动 |

## 三条已经过时的前提

### 1. 「买在区间高位所以亏」——**已被证伪**

任务说明是从线上两笔亏损（SOL 多入在 24h 分位 95%、SOL 空入在 17%）推出这个结论的。那是 N=2。

30 天历史、5 个标的、163 个 `ready` 信号，按 209 分钟持仓算前向收益后分桶（`calibration/macro_position_scan.py`）：

| 24h 分位桶 | 样本 | 均收益% | 胜率 |
|---|---|---|---|
| 0.0~0.2 | 36 | +0.110 | 50.0% |
| 0.2~0.4 | 23 | +0.152 | 56.5% |
| 0.4~0.6 | 24 | **−0.218** | 45.8% |
| 0.6~0.8 | 28 | **+1.047** | 60.7% |
| **0.8~1.0** | 52 | **+0.617** | 55.8% |

**高分位桶不是最差的，是第二好的。** 做多单独看：分位 ≥0.8 均 +0.617%，<0.8 均 +0.731%，差异完全在噪声内，而 `0.80` 阈值会砍掉 52/95 的做多信号。做空侧分位 ≥0.8 的样本数是 **0**，那条否决规则本就是死的。

**因此**：
- 检测器的过滤已按 `macroPositionEnabled=false` 上线，只保留 `range_position_pct_24h` 等字段进决策记录，积累线上样本后再重判。
- **README 的「上线顺序」第 2 步写的 `macroPositionEnabled=true`（临时阈值），不要执行。**
- **提示词里的 Gate 1（24h 分位 ≥0.80 不开多 / ≤0.20 不开空）是同一个被证伪的假设。** 原样写进方法论等于把一条没有数据支撑的规则固化成教条。要么删掉，要么降级成「提示模型注意位置」而不是硬性否决。

### 2. Gate 3（风险收益比 ≥2.0）**没有被验证过**

方向上合理，但没人量过。它可能挡掉绝大多数信号——README 自己算过 SOL 多那笔 reward≈0.3%、risk 0.9%，RR 0.33；如果多数入场的 RR 都在 1 以下，这条会让系统几乎不交易。**上之前先用 `calibration/` 量一遍**：把 163 个 ready 信号的 RR 算出来看分布，再决定阈值。

### 3. 真正的瓶颈不是入场质量，是样本率 —— **已修**

任务说明写完之后才查出来的：

| | 样本 | 均值% | t值 | 扣费后 |
|---|---|---|---|---|
| **ready** | 163 | +0.3904 | **3.11 显著为正** | **+0.3104** |
| **watch** | 1773 | +0.0092 | 0.25 与 0 无异 | **−0.0708 转负** |

两组差异 t=2.92 显著，而 `watch : ready = 10.9 : 1`。两者在 `trigger_policy` 里拿的都是 `LLM_ALLOWED`，**watch 拿走约 92% 的 LLM 预算，把唯一被证明有优势的信号挤了出去**。已降回 `RULE_ONLY`（提交 `f54558a`），留 `wyckoffWatchDispatchesLlm` 开关可回退。

配套结论（`calibration/edge_significance.py`）：
- 线上那 0/2 全亏，在这个分布下概率 **21.2%**——正常抽样，不是策略失效。
- 要把「有优势」和「运气」分开需要 **65 笔**（扣费后 103 笔），线上现在 **2 笔**。

## 所以任务一该怎么改

`supervisor_prompt_builder.py` 里**可以直接用**的部分：

- **删噪声**（`_prune_prompt_noise`）：Wyckoff 内部阈值 `config`、`market_api_config` 的 `ws_*`/`doc_reference_url`、三个 `*_api_config`。约占提示词 10%，下游没人读，纯赚。
- **输出契约压缩**：语义不变、措辞变紧。
- **PRIORITY 那条**：「如果 summary_reason 会写 *reduced size because RSI/overbought/extended/empty memory*，正确输出是 SKIP」。这条直击复盘里的病灶——模型看见 RSI 81 的反应是把仓位减半而不是放弃，5 笔入场每一笔都这样。**这是整份提示词里最有价值的一句。**
- **记忆为空的警告改写**：旧文案「降低 confidence 和 size_hint」正是病灶本身。

**需要先量再上**的部分：

- Gate 1（位置纪律）—— 见上，数据不支持。
- Gate 3（风险收益比）—— 未验证。
- Gate 2（regime 判定，震荡时 ready 降级成 watch）—— 注意 watch 现在已经不进 LLM 预算了，这条会直接变成「震荡时不交易」。可能是对的，但要知道自己在做什么。

## 任务三的两个坑（README 已标注，确认一下没漏）

1. 渲染器正则是 `\{([^}]+)\}`，模板正文里任何字面 `{}` 都会被替换成空串。
2. `build_supervisor_render_context` 没有 `sizing_constraints`，切模板路径会直接丢掉仓位约束——**必须同时上 README 里那个 `render_context_builder.py` 补丁**，且 `_sizing_constraints` 要复用同一份实现，别复制。

验证判据不是「调用成功」（这套系统里已经出过多次「参数被丢掉但调用照样成功」）：

```sql
SELECT prompt_source, resolved_template_code, prompt_template_fallback_used, COUNT(*)
FROM decision_run WHERE created_at > NOW() - INTERVAL 1 HOUR GROUP BY 1,2,3;
```

期望 `prompt_source='template'`、`resolved_template_code` 有值、`fallback_used=0`。现在是 808/808 `inline`。

## 还没决定的事

`minPositionRatio` 仍是 **0.40**（6 倍杠杆下单笔名义 240 USDT，账户 100 USDT）。README 建议先降到 0.15。考虑到 `ready` 的优势已被证明是真的（t=3.11），维持 0.40 也说得通——但那是风险偏好判断，需要用户拍板，不要自行修改。

## 有用的现成工具

`python-worker/trade_runtime/calibration/` 下（判定一律复用生产代码，不复制阈值逻辑）：

- `macro_position_scan.py` —— 按 24h 分位分桶算前向收益
- `edge_significance.py` —— 优势显著性、连亏概率、所需样本量
- `readiness_edge.py` —— ready / watch 分组对比
- `distinct_setups.py` —— 合并连续 ready，区分「机会数」与「K 线根数」

两个已知的坑：`openInterestHist` 只留 30 天；sweep 必须隔离被测维度，否则不同取值会得到相同 dispatch 数。
