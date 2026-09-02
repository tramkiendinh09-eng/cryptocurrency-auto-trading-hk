<template>
  <div class="cockpit" :class="{ 'is-live': isLive }">
    <!-- ── 顶部状态条：实盘与模拟必须一眼可辨 ───────────────────── -->
    <header class="topbar">
      <div class="mode" :class="isLive ? 'mode--live' : 'mode--paper'">
        <span class="mode__dot" />
        <span class="mode__label">{{ isLive ? '实盘 LIVE' : '模拟 PAPER' }}</span>
        <span class="mode__sub">{{ isLive ? '真实资金' : '不下真实订单' }}</span>
      </div>

      <div class="pills">
        <span class="pill" :class="workerOnline ? 'pill--ok' : 'pill--bad'">
          <i class="pill__dot" />Worker {{ workerOnline ? '在线' : '离线' }}
          <em v-if="worker.lastHeartbeat">{{ worker.lastHeartbeat }}</em>
        </span>
        <span class="pill" :class="sourceHealthy ? 'pill--ok' : 'pill--warn'">
          <i class="pill__dot" />行情源 {{ sourceHealthy ? '正常' : '降级' }}
        </span>
        <span class="pill pill--muted">
          <i class="pill__dot" />分发 {{ overview.latestDispatchMode || '—' }}
        </span>
        <span class="pill pill--muted" v-if="modelName">
          <i class="pill__dot" />{{ modelName }}
        </span>
      </div>

      <div class="topbar__right">
        <span class="refresh" :class="{ 'refresh--busy': loading }">
          {{ loading ? '刷新中' : '每 10 秒自动刷新' }}
        </span>
        <el-button size="small" @click="loadAll" :loading="loading">立即刷新</el-button>
      </div>
    </header>

    <!-- ── 账户与风险 ──────────────────────────────────────────── -->
    <section class="grid grid--metrics">
      <div class="card metric">
        <div class="metric__label">未实现盈亏</div>
        <div class="metric__value" :class="pnlClass(overview.totalUnrealizedPnl)">
          {{ signed(overview.totalUnrealizedPnl) }}
          <span class="metric__unit">USDT</span>
        </div>
        <div class="metric__foot">持仓 {{ overview.activePositionCount || 0 }} 个</div>
      </div>

      <div class="card metric">
        <div class="metric__label">今日盈亏</div>
        <div class="metric__value" :class="pnlClass(overview.latestDailyPnl)">
          {{ signed(overview.latestDailyPnl) }}
          <span class="metric__unit">USDT</span>
        </div>
        <div class="metric__foot">
          日亏上限 {{ fmt(config.maxDailyLoss) }}
          <div class="bar" v-if="dailyLossPct > 0">
            <div class="bar__fill" :style="{ width: Math.min(dailyLossPct, 100) + '%' }" />
          </div>
        </div>
      </div>

      <div class="card metric">
        <div class="metric__label">最大回撤</div>
        <div class="metric__value">{{ fmt(overview.maxDrawdownPct) }}<span class="metric__unit">%</span></div>
        <div class="metric__foot">仓位上限 {{ pct(config.maxPositionRatio) }}</div>
      </div>

      <div class="card metric">
        <div class="metric__label">今日风控拦截</div>
        <div class="metric__value" :class="{ 'v-warn': (risk.todayBlocks || 0) > 0 }">
          {{ risk.todayBlocks || 0 }}
        </div>
        <div class="metric__foot">拦截率 {{ fmt(risk.blockRate) }}%</div>
      </div>
    </section>

    <!-- ── 执行统计：从未成交是重要信号，不该被平均掉 ─────────── -->
    <section class="card exec">
      <div class="card__head">
        <h3>订单执行</h3>
        <span class="card__hint">共 {{ exec.total || 0 }} 次决策落地尝试</span>
      </div>
      <div class="exec__row">
        <div v-for="item in execCells" :key="item.key" class="exec__cell" :class="item.cls">
          <div class="exec__num">{{ item.value }}</div>
          <div class="exec__key">{{ item.label }}</div>
        </div>
      </div>
      <div class="notice notice--warn" v-if="(exec.filled || 0) === 0 && (exec.total || 0) > 0">
        尚无任何成交：{{ exec.total }} 次尝试全部被拦截或跳过。上实盘前应先在模拟下跑出至少一笔完整成交。
      </div>
    </section>

    <div class="grid grid--main">
      <!-- ── 行情与指标 ───────────────────────────────────────── -->
      <section class="card">
        <div class="card__head">
          <h3>行情与指标</h3>
          <span class="card__hint">{{ market.symbol || '—' }}</span>
        </div>

        <div class="price">
          <div class="price__main">{{ fmt(market.latest_price, 1) }}</div>
          <div class="price__meta">
            <span>标记价 {{ fmt(market.mark_price, 1) }}</span>
            <span :class="pnlClass(market.mark_price_deviation_pct)">
              偏离 {{ fmt(market.mark_price_deviation_pct, 4) }}%
            </span>
          </div>
        </div>

        <div class="kv">
          <div class="kv__item">
            <span class="kv__k">资金费率</span>
            <span class="kv__v" :class="pnlClass(market.funding_rate)">
              {{ fundingPct }}<em>%/8h</em>
            </span>
          </div>
          <div class="kv__item">
            <span class="kv__k">持仓量</span>
            <span class="kv__v">{{ fmt(market.open_interest, 0) }}</span>
          </div>
          <div class="kv__item">
            <span class="kv__k">24h 成交额</span>
            <span class="kv__v">{{ compact(market.quote_volume_24h) }}</span>
          </div>
          <div class="kv__item">
            <span class="kv__k">行情延迟</span>
            <span class="kv__v">{{ fmt(market.market_tick_staleness_seconds, 1) }}<em>s</em></span>
          </div>
        </div>

        <table class="matrix" v-if="klineCtx">
          <thead>
            <tr><th>周期</th><th>涨跌%</th><th>RSI</th><th>ATR%</th><th>量比</th><th>趋势</th></tr>
          </thead>
          <tbody>
            <tr v-for="tf in timeframes" :key="tf">
              <td class="matrix__tf">{{ tf }}</td>
              <td :class="pnlClass(pick(klineCtx.price_change_pct, tf))">
                {{ fmt(pick(klineCtx.price_change_pct, tf), 3) }}
              </td>
              <td :class="rsiClass(pick(klineCtx.rsi_14, tf))">
                {{ fmt(pick(klineCtx.rsi_14, tf), 1) }}
              </td>
              <td>{{ fmt(pick(klineCtx.atr_pct, tf), 3) }}</td>
              <td>{{ fmt(pick(klineCtx.quote_volume_ratio, tf), 2) }}</td>
              <td>
                <span class="trend" :class="'trend--' + (pick(klineCtx.ema_trend, tf) || 'flat')">
                  {{ trendLabel(pick(klineCtx.ema_trend, tf)) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ── 策略判定 ─────────────────────────────────────────── -->
      <section class="card">
        <div class="card__head">
          <h3>策略判定</h3>
          <span class="card__hint">Wyckoff 短线</span>
        </div>

        <div class="verdict" v-if="wyckoff">
          <div class="verdict__badge" :class="'verdict--' + (wyckoff.trade_readiness || 'unknown')">
            {{ readinessLabel(wyckoff.trade_readiness) }}
          </div>
          <div class="verdict__body">
            <div class="verdict__line"><span>阶段</span><b>{{ wyckoff.phase || '—' }}</b></div>
            <div class="verdict__line"><span>入场倾向</span><b>{{ wyckoff.entry_bias || '—' }}</b></div>
            <div class="verdict__line"><span>诱多风险</span><b>{{ wyckoff.trap_risk || '—' }}</b></div>
            <div class="verdict__line"><span>置信度</span><b>{{ fmt(wyckoff.confidence, 2) }}</b></div>
          </div>
        </div>
        <div class="reason" v-if="wyckoff && wyckoff.no_trade_reason">
          不交易原因：{{ wyckoff.no_trade_reason }}
        </div>
        <div class="reason" v-if="wyckoff && wyckoff.effort_evidence">
          量价证据：{{ wyckoff.effort_evidence }}（{{ wyckoff.effort_result }}）
        </div>

        <div class="card__head card__head--sub"><h3>门控</h3></div>
        <div class="kv">
          <div class="kv__item">
            <span class="kv__k">最近触发源</span>
            <span class="kv__v">{{ overview.lastTriggerSource || '—' }}</span>
          </div>
          <div class="kv__item">
            <span class="kv__k">触发原因</span>
            <span class="kv__v kv__v--sm">{{ overview.lastTriggerReason || '—' }}</span>
          </div>
          <div class="kv__item">
            <span class="kv__k">预算抑制</span>
            <span class="kv__v">{{ overview.budgetSuppressionCount || 0 }}</span>
          </div>
          <div class="kv__item">
            <span class="kv__k">冷却抑制</span>
            <span class="kv__v">{{ overview.cooldownSuppressionCount || 0 }}</span>
          </div>
        </div>
      </section>
    </div>

    <div class="grid grid--main">
      <!-- ── 决策流 ───────────────────────────────────────────── -->
      <section class="card">
        <div class="card__head">
          <h3>最近决策</h3>
          <span class="card__hint">累计 {{ overview.decisionCount || 0 }} 次</span>
        </div>
        <div class="feed">
          <div v-for="d in overview.recentDecisions || []" :key="d.id" class="feed__row">
            <span class="chip" :class="actionClass(d.action)">{{ d.action || '—' }}</span>
            <span class="feed__sym">{{ d.symbol }}</span>
            <span class="chip chip--ghost">{{ d.dispatchMode || d.mode }}</span>
            <span class="feed__reason">{{ d.summaryReason || d.triggerReason || '—' }}</span>
            <span class="feed__time">{{ shortTime(d.createdAt) }}</span>
          </div>
          <div v-if="!(overview.recentDecisions || []).length" class="empty">暂无决策记录</div>
        </div>
      </section>

      <!-- ── 风控命中 ─────────────────────────────────────────── -->
      <section class="card">
        <div class="card__head">
          <h3>风控命中</h3>
          <span class="card__hint">累计 {{ overview.riskHitCount || 0 }} 次</span>
        </div>
        <div class="feed">
          <div v-for="r in overview.recentRiskHits || []" :key="r.id" class="feed__row">
            <span class="chip chip--danger">{{ r.ruleCode }}</span>
            <span class="feed__reason">{{ r.reason }}</span>
            <span class="feed__time">{{ shortTime(r.createdAt) }}</span>
          </div>
          <div v-if="!(overview.recentRiskHits || []).length" class="empty">暂无风控命中</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup name="TradeMonitor">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { getTradeRuntimeOverview, getTradeRuntimeConfig } from '@/api/dca/tradeRuntime'
import { getWorkerStatus, getRiskStats } from '@/api/dca/dashboard'

const loading = ref(false)
const overview = ref({})
const config = ref({})
const worker = ref({})
const risk = ref({})
let timer = null

const timeframes = ['15m', '60m', '240m']

const isLive = computed(() => String(config.value.defaultMode || '').toUpperCase() === 'LIVE')
const workerOnline = computed(() => !!worker.value.online)
const exec = computed(() => overview.value.executionStats || {})

const execCells = computed(() => {
  const e = exec.value
  return [
    { key: 'filled', label: '已成交', value: e.filled || 0, cls: (e.filled || 0) > 0 ? 'is-good' : '' },
    { key: 'partial', label: '部分成交', value: e.partial || 0, cls: '' },
    { key: 'submitted', label: '已提交', value: e.submitted || 0, cls: '' },
    { key: 'pending', label: '等待中', value: e.pending || 0, cls: '' },
    { key: 'blocked', label: '风控拦截', value: e.blocked || 0, cls: (e.blocked || 0) > 0 ? 'is-warn' : '' },
    { key: 'skipped', label: '跳过', value: e.skipped || 0, cls: '' },
    { key: 'failed', label: '失败', value: e.failed || 0, cls: (e.failed || 0) > 0 ? 'is-bad' : '' },
    { key: 'canceled', label: '已撤销', value: e.canceled || 0, cls: '' }
  ]
})

// 最新的 market_metric 事件即运行时对市场的完整视图
const market = computed(() => {
  const events = overview.value.recentEvents || []
  const hit = events.find(e => e.eventType === 'market_metric')
  if (!hit) return {}
  try {
    return JSON.parse(hit.payloadJson || '{}')
  } catch (err) {
    return {}
  }
})
const klineCtx = computed(() => market.value.kline_context || null)
const wyckoff = computed(() => market.value.wyckoff_shortterm || null)

const sourceHealthy = computed(() => {
  const status = market.value.trade_tick_status
  return !status || status === 'ready'
})

const modelName = computed(() => {
  const d = (overview.value.recentDecisions || []).find(x => x.modelCode)
  return d ? d.modelCode : ''
})

const fundingPct = computed(() => {
  const v = Number(market.value.funding_rate)
  return Number.isFinite(v) ? (v * 100).toFixed(4) : '—'
})

const dailyLossPct = computed(() => {
  const pnl = Number(overview.value.latestDailyPnl)
  const cap = Math.abs(Number(config.value.maxDailyLoss))
  if (!Number.isFinite(pnl) || !Number.isFinite(cap) || cap === 0 || pnl >= 0) return 0
  return (Math.abs(pnl) / cap) * 100
})

function pick(obj, key) {
  return obj && obj[key] !== undefined ? obj[key] : null
}
function fmt(v, digits = 2) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return n.toFixed(digits)
}
function signed(v, digits = 2) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return (n > 0 ? '+' : '') + n.toFixed(digits)
}
function pct(v) {
  const n = Number(v)
  return Number.isFinite(n) ? (n * 100).toFixed(0) + '%' : '—'
}
function compact(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(2) + 'K'
  return n.toFixed(0)
}
function pnlClass(v) {
  const n = Number(v)
  if (!Number.isFinite(n) || n === 0) return ''
  return n > 0 ? 'v-up' : 'v-down'
}
function rsiClass(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return ''
  if (n >= 70) return 'v-down'
  if (n <= 30) return 'v-up'
  return ''
}
function trendLabel(v) {
  return { bullish: '多', bearish: '空' }[v] || '—'
}
function readinessLabel(v) {
  return { ready: '可交易', avoid: '回避', watch: '观察' }[v] || (v || '未知')
}
function actionClass(action) {
  const a = String(action || '').toUpperCase()
  if (a.includes('LONG') || a === 'BUY') return 'chip--long'
  if (a.includes('SHORT') || a === 'SELL') return 'chip--short'
  if (a === 'CLOSE') return 'chip--close'
  return 'chip--ghost'
}
function shortTime(v) {
  if (!v) return '—'
  return String(v).slice(5, 16)
}

async function loadAll() {
  loading.value = true
  const settle = (p, sink) => p.then(res => { sink(res) }).catch(() => {})
  await Promise.all([
    settle(getTradeRuntimeOverview(), r => { overview.value = r.data || {} }),
    settle(getTradeRuntimeConfig(), r => { config.value = r.data || {} }),
    settle(getWorkerStatus(), r => { worker.value = r.data || {} }),
    settle(getRiskStats(), r => { risk.value = r.data || {} })
  ])
  loading.value = false
}

onMounted(() => {
  loadAll()
  timer = setInterval(loadAll, 10000)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style lang="scss" scoped>
.cockpit {
  --ink: var(--el-text-color-primary);
  --ink-dim: var(--el-text-color-secondary);
  --panel: var(--el-bg-color-overlay);
  --line: var(--el-border-color-light);
  --up: #16a34a;
  --down: #dc2626;
  --warn: #d97706;

  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum';
}

/* 顶部状态条 */
.topbar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 12px 16px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
}
.topbar__right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}
.refresh {
  font-size: 12px;
  color: var(--ink-dim);
}
.refresh--busy { color: var(--el-color-primary); }

.mode {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 8px;
  font-weight: 700;
}
.mode__dot {
  width: 8px; height: 8px; border-radius: 50%;
  align-self: center;
}
.mode__label { font-size: 15px; letter-spacing: .3px; }
.mode__sub { font-size: 12px; font-weight: 500; opacity: .75; }
.mode--paper {
  background: color-mix(in srgb, var(--el-color-info) 12%, transparent);
  color: var(--el-color-info);
  .mode__dot { background: var(--el-color-info); }
}
/* 实盘必须一眼可辨，而不是一个不起眼的小标签 */
.mode--live {
  background: color-mix(in srgb, var(--down) 16%, transparent);
  color: var(--down);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--down) 40%, transparent);
  .mode__dot {
    background: var(--down);
    animation: pulse 1.6s ease-in-out infinite;
  }
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .25; }
}
.is-live .topbar { border-color: color-mix(in srgb, var(--down) 45%, var(--line)); }

.pills { display: flex; gap: 8px; flex-wrap: wrap; }
.pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 999px;
  font-size: 12px; border: 1px solid var(--line);
  color: var(--ink-dim);
  em { font-style: normal; opacity: .6; margin-left: 2px; }
}
.pill__dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.pill--ok { color: var(--up); border-color: color-mix(in srgb, var(--up) 35%, transparent); }
.pill--warn { color: var(--warn); border-color: color-mix(in srgb, var(--warn) 35%, transparent); }
.pill--bad { color: var(--down); border-color: color-mix(in srgb, var(--down) 35%, transparent); }

/* 栅格 */
.grid { display: grid; gap: 14px; }
.grid--metrics { grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }
.grid--main { grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); }

.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px 16px;
}
.card__head {
  display: flex; align-items: baseline; justify-content: space-between;
  margin-bottom: 12px;
  h3 { margin: 0; font-size: 14px; font-weight: 600; color: var(--ink); }
}
.card__head--sub { margin-top: 18px; padding-top: 12px; border-top: 1px dashed var(--line); }
.card__hint { font-size: 12px; color: var(--ink-dim); }

/* 指标卡 */
.metric__label { font-size: 12px; color: var(--ink-dim); }
.metric__value {
  font-size: 26px; font-weight: 650; line-height: 1.25; margin: 6px 0 4px;
  letter-spacing: -.4px;
}
.metric__unit { font-size: 12px; font-weight: 500; color: var(--ink-dim); margin-left: 4px; }
.metric__foot { font-size: 12px; color: var(--ink-dim); }
.v-up { color: var(--up); }
.v-down { color: var(--down); }
.v-warn { color: var(--warn); }

.bar {
  margin-top: 6px; height: 4px; border-radius: 2px;
  background: color-mix(in srgb, var(--down) 15%, transparent);
  overflow: hidden;
}
.bar__fill { height: 100%; background: var(--down); }

/* 执行统计 */
.exec__row { display: grid; grid-template-columns: repeat(auto-fit, minmax(84px, 1fr)); gap: 8px; }
.exec__cell {
  text-align: center; padding: 10px 6px; border-radius: 8px;
  border: 1px solid var(--line);
}
.exec__num { font-size: 20px; font-weight: 650; }
.exec__key { font-size: 11px; color: var(--ink-dim); margin-top: 2px; }
.exec__cell.is-good { border-color: color-mix(in srgb, var(--up) 40%, transparent); .exec__num { color: var(--up); } }
.exec__cell.is-warn { border-color: color-mix(in srgb, var(--warn) 40%, transparent); .exec__num { color: var(--warn); } }
.exec__cell.is-bad  { border-color: color-mix(in srgb, var(--down) 40%, transparent); .exec__num { color: var(--down); } }

.notice {
  margin-top: 12px; padding: 9px 12px; border-radius: 8px;
  font-size: 12.5px; line-height: 1.6;
}
.notice--warn {
  background: color-mix(in srgb, var(--warn) 10%, transparent);
  color: var(--warn);
  border: 1px solid color-mix(in srgb, var(--warn) 30%, transparent);
}

/* 价格 */
.price { display: flex; align-items: baseline; gap: 14px; margin-bottom: 12px; }
.price__main { font-size: 30px; font-weight: 650; letter-spacing: -.6px; }
.price__meta { display: flex; flex-direction: column; gap: 2px; font-size: 12px; color: var(--ink-dim); }

/* 键值 */
.kv { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.kv__item {
  display: flex; flex-direction: column; gap: 3px;
  padding: 8px 10px; border-radius: 8px;
  background: color-mix(in srgb, var(--ink) 4%, transparent);
}
.kv__k { font-size: 11px; color: var(--ink-dim); }
.kv__v { font-size: 15px; font-weight: 600; em { font-style: normal; font-size: 11px; font-weight: 400; color: var(--ink-dim); margin-left: 2px; } }
.kv__v--sm { font-size: 12px; font-weight: 500; word-break: break-all; }

/* 指标矩阵 */
.matrix {
  width: 100%; margin-top: 14px; border-collapse: collapse; font-size: 13px;
  th {
    text-align: right; font-weight: 500; font-size: 11px; color: var(--ink-dim);
    padding: 6px 8px; border-bottom: 1px solid var(--line);
    &:first-child { text-align: left; }
  }
  td {
    text-align: right; padding: 7px 8px; border-bottom: 1px solid color-mix(in srgb, var(--line) 50%, transparent);
    &:first-child { text-align: left; }
  }
  tr:last-child td { border-bottom: none; }
}
.matrix__tf { color: var(--ink-dim); font-size: 12px; }
.trend { font-size: 12px; }
.trend--bullish { color: var(--up); }
.trend--bearish { color: var(--down); }

/* 策略判定 */
.verdict { display: flex; gap: 14px; align-items: flex-start; }
.verdict__badge {
  flex: 0 0 auto; padding: 10px 16px; border-radius: 8px;
  font-size: 15px; font-weight: 700;
  border: 1px solid var(--line); color: var(--ink-dim);
}
.verdict--ready { color: var(--up); border-color: color-mix(in srgb, var(--up) 45%, transparent); background: color-mix(in srgb, var(--up) 8%, transparent); }
.verdict--avoid { color: var(--down); border-color: color-mix(in srgb, var(--down) 45%, transparent); background: color-mix(in srgb, var(--down) 8%, transparent); }
.verdict--watch { color: var(--warn); border-color: color-mix(in srgb, var(--warn) 45%, transparent); background: color-mix(in srgb, var(--warn) 8%, transparent); }
.verdict__body { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px 16px; flex: 1; }
.verdict__line {
  display: flex; justify-content: space-between; font-size: 12.5px;
  span { color: var(--ink-dim); }
  b { font-weight: 600; }
}
.reason {
  margin-top: 10px; font-size: 12px; color: var(--ink-dim);
  padding: 7px 10px; border-radius: 6px;
  background: color-mix(in srgb, var(--ink) 4%, transparent);
}

/* 流式列表 */
.feed { display: flex; flex-direction: column; }
.feed__row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 0; border-bottom: 1px solid color-mix(in srgb, var(--line) 50%, transparent);
  font-size: 12.5px;
  &:last-child { border-bottom: none; }
}
.feed__sym { font-weight: 600; }
.feed__reason { flex: 1; color: var(--ink-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.feed__time { color: var(--ink-dim); font-size: 11.5px; flex: 0 0 auto; }
.empty { padding: 18px 0; text-align: center; color: var(--ink-dim); font-size: 12.5px; }

.chip {
  display: inline-block; padding: 2px 9px; border-radius: 5px;
  font-size: 11.5px; font-weight: 600; flex: 0 0 auto;
  border: 1px solid var(--line); color: var(--ink-dim);
}
.chip--ghost { opacity: .8; }
.chip--long { color: var(--up); border-color: color-mix(in srgb, var(--up) 40%, transparent); background: color-mix(in srgb, var(--up) 8%, transparent); }
.chip--short { color: var(--down); border-color: color-mix(in srgb, var(--down) 40%, transparent); background: color-mix(in srgb, var(--down) 8%, transparent); }
.chip--close { color: var(--warn); border-color: color-mix(in srgb, var(--warn) 40%, transparent); }
.chip--danger { color: var(--down); border-color: color-mix(in srgb, var(--down) 40%, transparent); }
</style>
