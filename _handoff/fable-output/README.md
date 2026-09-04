# 交接回执 —— 三件事的改写结果

对应 `_handoff/0-任务说明.md`。顺序按建议执行：任务二 → 任务一 → 任务三。

| 交付物 | 替换目标 | 状态 |
|---|---|---|
| `wyckoff_shortterm.py` | `python-worker/trade_runtime/strategy/wyckoff_shortterm.py` | 已改，回归通过 |
| `supervisor_prompt_builder.py` | 决策图模块里的 `_build_supervisor_prompt` | 已改，自检通过 |
| `generate_template_seed.py` → `prompt_template_seed.sql` | `prompt_template` + `trade_prompt_binding` 数据 | 已生成，渲染器正则验证通过 |
| 本文「渲染上下文补丁」 | `prompting/render_context_builder.py` | **必须一起上，否则模板路径丢仓位约束** |

---

## 任务二：Wyckoff 宏观位置过滤

### 改了什么
- 新增 `_range_position()` / `_macro_position_snapshot()` / `_apply_macro_position_filter()`。
- 24h 窗口优先用 24 根 1h K，缺则退到 96 根 15m；4h 窗口优先 16 根 15m，缺则 4 根 1h。样本不足 → `macro_position_status = insufficient`，**不放行、不否决**，把缺口写进字段让主管看见。
- 过滤放在 1h 结构分类之后、funding/OI 加分之前，只会把 `ready/watch` 收紧为 `avoid`，不会反向放松。
- **原有输出字段一个没改名**（`status/phase/entry_bias/trigger/trade_readiness/confidence/no_trade_reason/trap_risk/breakout_extension_pct/range_high/range_low/invalidation/...`）。新增字段：

```
macro_position_status        ready | partial | insufficient
macro_position_verdict       ok | warn_long_upper_band | warn_short_lower_band
                             | veto_long_high_percentile | veto_short_low_percentile
                             | insufficient_history | disabled | not_applicable
macro_position_evidence      "window=24h, position_pct=0.951, to_high_pct=0.313, ..."
range_position_pct_24h / range_position_pct_4h
range_high_24h / range_low_24h / range_high_4h / range_low_4h
distance_to_24h_high_pct / distance_to_24h_low_pct
macro_position               完整快照（含样本数、来源）
```

- 否决时 `no_trade_reason = macro_position_high_24h_percentile_no_chase`（或 `low_..`），`confirmation_needed` 追加 `pullback_toward_24h_range_mid`，置信 −0.10；警戒带置信 −0.04。

### 新增配置键（走 `runtime_flags_json` 里的 wyckoff config，驼峰/蛇形都认）

| 键 | 临时默认 | 说明 |
|---|---|---|
| `macroPositionEnabled` | `true` | 关掉即与原版逐字段一致（已验证） |
| `macroPositionPrimaryWindow` | `"24h"` | 允许否决的窗口；4h 只做信息 |
| `macroPositionVetoPercentile` | `0.80` | 多头 ≥0.80 否决；空头 ≤ 1−0.80 否决 |
| `macroPositionWarnPercentile` | `0.70` | 软惩罚带 |
| `macroPositionMaxDistanceToExtremePct` | `1.0` | 离 24h 高/低点 ≤1% 亦否决 |
| `macroPositionMinSamples24h` / `4h` | `12` / `8` | 窗口可信的最少样本 |

**0.80 / 0.20 是临时值**，仅保证复盘里两笔亏损（SOL 多 95%、SOL 空 17%）会被挡掉。正式值必须 sweep。

### 回归结果（合成 SOL 场景：24h 区间 99.14–105.88，1h 突破到 105.55）

| | trade_readiness | confidence | no_trade_reason | 24h 分位 | 离高点 |
|---|---|---|---|---|---|
| 原版 | `ready` | 0.78 | — | （不知道） | — |
| 新版 | `avoid` | 0.68 | `macro_position_high_24h_percentile_no_chase` | 0.951 | 0.31% |
| 新版 + `macroPositionEnabled=false` | `ready` | 0.78 | — | — | — |

突破延伸 0.380%、区间 104.62–105.15，与复盘表里的 #9 一致。旧字段缺失：0；关过滤后差异字段：0。

### Sweep 计划（`python-worker/trade_runtime/calibration/`）
1. 用 `history` 拉近 30 天 15m + 1h K（`openInterestHist` 只有 30 天，超出会让 OI 维度静默为 0）。
2. 基线：`macroPositionEnabled=false`，记录 `ready` 次数与 `evaluate_trigger_policy` 的 dispatch 数、后续 1h/4h 方向命中率。
3. **隔离被测维度**：sweep 时把其它会在同一根 K 上触发的维度（`maxReadyExtensionPct`、`requireRetestForReady`、trap）固定为生产值，只变 `macroPositionVetoPercentile ∈ {0.70, 0.75, 0.80, 0.85, 0.90, 0.95}`，`macroPositionMaxDistanceToExtremePct ∈ {0, 0.5, 1.0, 1.5}`。不隔离的话不同取值会得到相同 dispatch 数。
4. 判定复用生产 `evaluate_trigger_policy`，不要复制阈值比较逻辑。
5. 选点标准：ready 后 4h 内朝入场方向走 ≥1×ATR(60m) 的比例，对比基线 0.5051；同时看剩余 dispatch 数别掉到样本不足。
6. 把选出的值写进 `trade_runtime_config.runtime_flags_json`，**不要改代码默认值**。

---

## 任务一：主管提示词指令段

### 结构
```
SUPERVISOR_METHODOLOGY   (5.1k 字符)  ROLE → Gate 1 位置 → Gate 2 regime → Gate 3 风险收益 → Gate 4 证据 → Gate 5 冲突 → PRIORITY RULES
SUPERVISOR_OUTPUT_CONTRACT (2.3k 字符) JSON 键、action 枚举、size_hint/leverage_hint 口径 —— 语义与旧版一致，只压缩措辞
```
关键词覆盖（旧版 → 新版）：`risk` 1→7，`reward` 0→8，`regime` 0→6，`overbought/extended/chase` 0→各 1，`invalidation` 7。

### 直接对应复盘的条款
- Gate 1：24h 分位 ≥0.80 或离高点 ≤1% 不开多；≤0.20 或离低点 ≤1% 不开空；RSI 15m/60m ≥70 挡多、≤30 挡空；`macro_position_verdict` 以 `veto` 开头直接判失败。→ 挡掉 SOL 多（95%）和 SOL 空（17%）。
- Gate 2：EMA 60m、240m 涨跌符号、60m 涨跌符号三者一致且 |240m 涨跌| > 1.5×ATR60m 才算趋势；否则震荡，突破信号降一级（ready→watch），只准做区间边缘的 spring/upthrust 反转且必须 `retest_confirmed`。
- Gate 3：risk% = |入场−失效位|/入场；reward% = 到 24h 高/低点（或 240m 极值）的距离；要求比值 ≥2.0 且 reward ≥ 2×ATR15m。→ SOL 多 risk 0.9%、reward≈0.3% 直接出局。
- PRIORITY：「如果 summary_reason 会写 *reduced size because RSI/overbought/extended/empty memory*，正确输出是 SKIP」；过门的仓位给足 sizing_constraints 内的正常仓，没有半信半疑仓。
- 出场规则只重申不加严：CLOSE 仅在失效位击穿或反向 Wyckoff 触发；开仓 60 分钟内不 ADD。

### 保留不动的口径
键名、action 枚举、`size_hint` 为权益比例、敞口 = `account_equity * size_hint * leverage_hint`、落在 `min_size_hint ~ max_size_hint`、`leverage_hint` 为 `min_leverage ~ max_leverage` 整数、最小名义/步进规则、`any_size_tradeable=false → SKIP`。

### 删掉的噪声（`_prune_prompt_noise`）
`wyckoff_shortterm.config`（两处）、`market_api_config` 的 `ws_*`/`doc_reference_url`/`id`/`version_no`/`priority`、`news/onchain/social_api_config`、`market_data_config`。下游解析器、风控、`trigger_policy` 都不读这些。

### 记忆为空的警告
旧文案「降低 confidence 和 size_hint」正是复盘里的病灶，改为「不许用缩仓补偿，改用更严格过门 + 歧义即 SKIP」。

---

## 任务三：模板落表 + 绑定

### 执行
```bash
python3 generate_template_seed.py > prompt_template_seed.sql
mysql ... < prompt_template_seed.sql
```
- 模板 code：`SUPERVISOR_ENTRY_DISCIPLINE_V1`，`is_active=1, is_default=1, version=1`，重复执行走 `ON DUPLICATE KEY UPDATE`，version 自增。
- 绑定：`binding_scope='SUPERVISOR'`，无 strategy/symbol 限定，`mode_scope_json='[]'`、`event_strength_scope_json='[]'`（解析器把空列表当匹配全部），`priority=100`（解析器里数字小者优先，之后做 A/B 时加更小 priority 的窄范围绑定即可覆盖）。

### 两个会静默失效的坑（都已处理/标注）
1. **渲染器正则是 `\{([^}]+)\}`**，正文里任何字面 `{}` 都会被替换成空串。方法论/契约常量里已无花括号，生成脚本有 assert；模板正文用真实渲染正则跑过，方法论段原样保留，32 个占位符与声明列表完全一致。
2. **`build_supervisor_render_context` 没有 `sizing_constraints`**。内联提示词专门为「size_hint 低到交易所不接」加的这一段，切到模板路径会直接消失。补丁如下：

### 渲染上下文补丁（`prompting/render_context_builder.py`）
```python
# build_supervisor_render_context(...) 返回 dict 中追加：
        "sizing_constraints_json": _json_dumps(_sizing_constraints(state, runtime_config)),
```
`_sizing_constraints` 与内联构造函数用同一个实现（从决策图模块导入或搬到共享模块），别复制一份。

同时建议 `_build_market_context` 输出前套一遍 `_prune_prompt_noise` 里的 Wyckoff `config` 剔除，模板路径才能同样省掉那 570 字符。

### 验证判据（不是「调用成功」）
```sql
SELECT prompt_source, resolved_template_code, prompt_template_fallback_used, COUNT(*)
FROM decision_run
WHERE create_time > NOW() - INTERVAL 1 HOUR
GROUP BY 1, 2, 3;
```
期望：`prompt_source='template'`、`resolved_template_code='SUPERVISOR_ENTRY_DISCIPLINE_V1'`、`fallback_used=0`。
再抽一条 `decision_run` 的原始 prompt，确认包含 `sizing_constraints:` 后面**不是空串**，且 `Gate 1 - Location` 段存在。
仍是 `inline` 时按顺序查：`prompt_template.is_active=1` → `GET /dca/template/code/SUPERVISOR_ENTRY_DISCIPLINE_V1` 有返回 → worker 重启（registry 有进程内缓存）。

---

## 上线顺序与仓位风险

1. **先**把 `trade_runtime_config.runtime_flags_json.minPositionRatio` 从 `0.40` 调到 `0.15`。6 倍杠杆下单笔名义从 240 USDT 降到 90 USDT。
2. 部署 `wyckoff_shortterm.py`（`macroPositionEnabled=true`，临时阈值），观察 `macro_position_verdict` 分布 1–2 天，同时跑 sweep。
3. 部署提示词（内联版）+ 渲染上下文补丁。
4. 执行 SQL，确认 `prompt_source` 翻转。
5. sweep 出结果后把阈值写进 runtime config；入场胜率稳定后再考虑放回 `minPositionRatio`。

## 复盘对照：这套改动如何解释掉 5 笔入场

| # | 标的 | 方向 | 24h 分位（估） | 会被谁挡 |
|---|---|---|---|---|
| 5 | SOL 空 | 17% | 检测器 veto_short_low_percentile；Gate 1 |
| 6 | BNB 多 | 中位（+3.35% 在手） | 不挡；Gate 4 量比 0.74 <1.2 会要求更强证据 |
| 7 | SK海力士 多 | — | 不挡（量比 1.31） |
| 8 | 美光 多 | — | 不挡（量比 1.28） |
| 9 | SOL 多 | 95% | 检测器 veto_long_high_percentile；Gate 1 + Gate 3（RR≈0.3） |

两笔亏损全部在入场端被拦下；三笔盈利中两笔完全不受影响，BNB 那笔由 Gate 4 的量比要求决定——这是要用 sweep 校准的地方，不是拍脑袋放宽的地方。
