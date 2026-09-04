<template>
  <div class="terminal">
    <!-- 左：自选 -->
    <aside class="tm-watchlist">
      <div class="tm-panel-head">
        <span>自选</span>
        <span class="tm-dim">{{ watchlist.length }}</span>
      </div>
      <ul class="tm-symbols">
        <li
          v-for="item in watchlist"
          :key="item.symbol"
          :class="['tm-symbol', { active: item.symbol === activeSymbol }]"
          @click="selectSymbol(item.symbol)"
        >
          <div class="tm-symbol-row">
            <span class="tm-symbol-code">{{ shortSymbol(item.symbol) }}</span>
            <span v-if="item.side" :class="['tm-pos-dot', item.side]" :title="`持仓 ${item.side}`"></span>
          </div>
          <div class="tm-symbol-row">
            <span class="tm-num">{{ item.price ?? '—' }}</span>
            <span class="tm-num" :class="changeClass(item.changePct)">{{ formatPct(item.changePct) }}</span>
          </div>
        </li>
      </ul>
      <div v-if="!watchlist.length" class="tm-empty">{{ loadError || '加载中…' }}</div>
    </aside>

    <!-- 中：图表 -->
    <section class="tm-stage">
      <div class="tm-stage-head">
        <span class="tm-stage-symbol">{{ activeSymbol || '—' }}</span>
        <span class="tm-num tm-stage-price">{{ activeTicker.price ?? '—' }}</span>
        <span class="tm-num" :class="changeClass(activeTicker.changePct)">{{ formatPct(activeTicker.changePct) }}</span>
        <span class="tm-spacer"></span>
        <button
          v-for="option in intervals"
          :key="option"
          :class="['tm-tab', { active: option === interval }]"
          @click="selectInterval(option)"
        >{{ option }}</button>
      </div>
      <div ref="chartHost" class="tm-chart"></div>
      <div v-if="chartError" class="tm-chart-error">{{ chartError }}</div>
    </section>

    <!-- 右：持仓与决策 -->
    <aside class="tm-side">
      <div class="tm-panel-head">持仓</div>
      <div v-if="activePosition" class="tm-position">
        <div class="tm-kv">
          <span>方向</span>
          <span :class="['tm-side-tag', normalizeSide(activePosition.side)]">
            {{ normalizeSide(activePosition.side) === 'long' ? '多' : '空' }}
          </span>
        </div>
        <div class="tm-kv"><span>数量</span><span class="tm-num">{{ activePosition.positionQuantity }}</span></div>
        <div class="tm-kv"><span>开仓价</span><span class="tm-num">{{ activePosition.entryPrice }}</span></div>
        <div class="tm-kv">
          <span>浮动盈亏</span>
          <span class="tm-num" :class="changeClass(activePosition.unrealizedPnl)">
            {{ formatNumber(activePosition.unrealizedPnl) }}
          </span>
        </div>
      </div>
      <div v-else class="tm-empty">无持仓</div>

      <div class="tm-panel-head">最近决策</div>
      <ul class="tm-decisions">
        <li v-for="run in decisions" :key="run.id || run.traceId" class="tm-decision">
          <div class="tm-decision-row">
            <span :class="['tm-action', actionClass(run.action)]">{{ run.action || '—' }}</span>
            <span class="tm-dim tm-num">{{ shortTime(run.createdAt) }}</span>
          </div>
          <div class="tm-dim tm-decision-reason">
            {{ run.triggerSource || '—' }} · {{ run.dispatchMode || '—' }}
          </div>
        </li>
      </ul>
      <div v-if="!decisions.length" class="tm-empty">暂无决策</div>
    </aside>
  </div>
</template>

<script setup name="DcaTerminal">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { CandlestickSeries, HistogramSeries, createChart, createSeriesMarkers } from 'lightweight-charts'
import { listKlines, listTickers } from '@/api/dca/terminal'
import { getTradeRuntimeConfig } from '@/api/dca/tradeRuntime'
import { listRuntimePositions } from '@/api/dca/tradeExecution'
import { listDecisionRuns } from '@/api/dca/decisionAudit'

const intervals = ['15m', '1h', '4h', '1d']

const chartHost = ref(null)
const activeSymbol = ref('')
const interval = ref('15m')
const symbols = ref([])
const tickers = ref({})
const positions = ref([])
const decisions = ref([])
const loadError = ref('')
const chartError = ref('')

// 图表实例不放进 ref：它内部持有 canvas 与大量数据，被 Vue 深度代理会
// 让每一次行情更新都走一遍响应式追踪，正是「卡」的来源。
const chart = shallowRef(null)
const candleSeries = shallowRef(null)
const volumeSeries = shallowRef(null)
const markersApi = shallowRef(null)
let timer = null

const watchlist = computed(() =>
  symbols.value.map((symbol) => {
    const ticker = tickers.value[symbol] || {}
    const position = positions.value.find((item) => item.symbol === symbol)
    return {
      symbol,
      price: ticker.price,
      changePct: ticker.changePct,
      side: position ? normalizeSide(position.side) : ''
    }
  })
)

const activeTicker = computed(() => tickers.value[activeSymbol.value] || {})
const activePosition = computed(() =>
  positions.value.find((item) => item.symbol === activeSymbol.value) || null
)

function normalizeSide(value) {
  const normalized = String(value || '').toLowerCase()
  if (normalized === 'long' || normalized === 'buy') return 'long'
  if (normalized === 'short' || normalized === 'sell') return 'short'
  return ''
}

function shortSymbol(symbol) {
  return String(symbol || '').replace(/USDT$/, '')
}

function formatNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(4) : '—'
}

function formatPct(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'
  return `${number >= 0 ? '+' : ''}${number.toFixed(2)}%`
}

function changeClass(value) {
  const number = Number(value)
  if (!Number.isFinite(number) || number === 0) return ''
  return number > 0 ? 'up' : 'down'
}

function actionClass(action) {
  const normalized = String(action || '').toUpperCase()
  if (normalized.startsWith('OPEN_LONG') || normalized.startsWith('ADD_LONG')) return 'up'
  if (normalized.startsWith('OPEN_SHORT') || normalized.startsWith('ADD_SHORT')) return 'down'
  if (normalized === 'CLOSE' || normalized === 'REDUCE') return 'warn'
  return ''
}

function shortTime(value) {
  const text = String(value || '')
  return text.length >= 16 ? text.slice(5, 16) : text
}

function buildChart() {
  if (!chartHost.value || chart.value) return
  chart.value = createChart(chartHost.value, {
    layout: {
      background: { color: '#12161c' },
      textColor: '#8b95a5',
      fontSize: 11
    },
    grid: {
      vertLines: { color: '#1c2027' },
      horzLines: { color: '#1c2027' }
    },
    rightPriceScale: { borderColor: '#252b34' },
    timeScale: { borderColor: '#252b34', timeVisible: true },
    crosshair: { mode: 0 },
    autoSize: true
  })
  candleSeries.value = chart.value.addSeries(CandlestickSeries, {
    upColor: '#26a37b',
    downColor: '#d0454c',
    borderVisible: false,
    wickUpColor: '#26a37b',
    wickDownColor: '#d0454c'
  })
  volumeSeries.value = chart.value.addSeries(HistogramSeries, {
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume'
  })
  // 成交量压在底部 20%，不和价格抢纵轴。
  chart.value.priceScale('volume').applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 }
  })
  markersApi.value = createSeriesMarkers(candleSeries.value, [])
}

async function loadSymbols() {
  try {
    const response = await getTradeRuntimeConfig()
    const config = response?.data || {}
    const parsed = JSON.parse(config.allowedSymbolsJson || '[]')
    symbols.value = Array.isArray(parsed) ? parsed : []
    loadError.value = ''
  } catch (error) {
    symbols.value = []
    loadError.value = '交易对加载失败'
  }
  if (!activeSymbol.value && symbols.value.length) {
    activeSymbol.value = symbols.value[0]
  }
}

async function loadTickers() {
  if (!symbols.value.length) return
  try {
    const response = await listTickers({ symbols: symbols.value.join(',') })
    const next = {}
    for (const row of response?.data || []) {
      next[row.symbol] = { price: row.price, changePct: row.changePct }
    }
    tickers.value = next
  } catch (error) {
    // 报价拿不到不该让整页空掉，图表和持仓是独立的数据源。
  }
}

async function loadPositions() {
  try {
    const response = await listRuntimePositions({})
    positions.value = response?.data || response?.rows || []
  } catch (error) {
    positions.value = []
  }
}

async function loadDecisions() {
  if (!activeSymbol.value) return
  try {
    const response = await listDecisionRuns({ symbol: activeSymbol.value, pageNum: 1, pageSize: 12 })
    decisions.value = response?.rows || response?.data || []
  } catch (error) {
    decisions.value = []
  }
  applyMarkers()
}

async function loadKlines() {
  if (!activeSymbol.value || !candleSeries.value) return
  try {
    const response = await listKlines({
      symbol: activeSymbol.value,
      interval: interval.value,
      limit: 300
    })
    const rows = response?.data || []
    if (!rows.length) {
      chartError.value = '该周期暂无 K 线'
      return
    }
    candleSeries.value.setData(
      rows.map((row) => ({ time: row.t, open: row.o, high: row.h, low: row.l, close: row.c }))
    )
    volumeSeries.value.setData(
      rows.map((row) => ({
        time: row.t,
        value: row.v,
        color: row.c >= row.o ? 'rgba(38,163,123,0.35)' : 'rgba(208,69,76,0.35)'
      }))
    )
    chartError.value = response?.stale ? '行情源暂时不可用，显示的是缓存数据' : ''
    applyMarkers()
  } catch (error) {
    chartError.value = 'K 线加载失败'
  }
}

/** 把非 SKIP 的决策打到 K 线上——图表的价值一半在这里。 */
function applyMarkers() {
  if (!markersApi.value) return
  const markers = decisions.value
    .filter((run) => run.action && !['SKIP', 'NO_ACTION'].includes(String(run.action).toUpperCase()))
    .map((run) => {
      const action = String(run.action).toUpperCase()
      const isLong = action.includes('LONG')
      return {
        time: Math.floor(new Date(String(run.createdAt).replace(' ', 'T')).getTime() / 1000),
        position: isLong ? 'belowBar' : 'aboveBar',
        color: actionClass(action) === 'up' ? '#26a37b' : actionClass(action) === 'down' ? '#d0454c' : '#c9922e',
        shape: isLong ? 'arrowUp' : 'arrowDown',
        text: action
      }
    })
    .filter((marker) => Number.isFinite(marker.time))
    .sort((a, b) => a.time - b.time)
  markersApi.value.setMarkers(markers)
}

function selectSymbol(symbol) {
  if (symbol === activeSymbol.value) return
  activeSymbol.value = symbol
  chartError.value = ''
  loadKlines()
  loadDecisions()
}

function selectInterval(value) {
  if (value === interval.value) return
  interval.value = value
  loadKlines()
}

async function refresh() {
  await Promise.all([loadTickers(), loadPositions(), loadKlines(), loadDecisions()])
}

onMounted(async () => {
  await loadSymbols()
  await nextTick()
  buildChart()
  await refresh()
  // 15 秒一轮。K 线端有 10 秒缓存，再快只会打自己的后端。
  timer = setInterval(refresh, 15000)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  if (chart.value) {
    chart.value.remove()
    chart.value = null
  }
})
</script>

<style scoped>
.terminal {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr) 300px;
  gap: 1px;
  height: calc(100vh - 84px);
  background: #0d1117;
  color: #c8d0da;
  font-size: 12px;
}

.tm-watchlist,
.tm-stage,
.tm-side {
  background: #12161c;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.tm-panel-head {
  display: flex;
  justify-content: space-between;
  padding: 8px 10px;
  color: #6f7b8c;
  font-weight: 600;
  letter-spacing: 0.04em;
  border-bottom: 1px solid #1c2027;
}

.tm-symbols {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  flex: 1;
}

.tm-symbol {
  padding: 6px 10px;
  border-bottom: 1px solid #171b21;
  cursor: pointer;
}

.tm-symbol:hover { background: #171d25; }
.tm-symbol.active { background: #1b2430; box-shadow: inset 2px 0 0 #3d7eff; }

.tm-symbol-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  line-height: 1.5;
}

.tm-symbol-code { font-weight: 600; color: #dbe3ec; }

.tm-pos-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.tm-pos-dot.long { background: #26a37b; }
.tm-pos-dot.short { background: #d0454c; }

.tm-num {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.up { color: #26a37b; }
.down { color: #d0454c; }
.warn { color: #c9922e; }

.tm-stage-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-bottom: 1px solid #1c2027;
}

.tm-stage-symbol { font-size: 14px; font-weight: 700; color: #eef2f7; }
.tm-stage-price { font-size: 14px; }
.tm-spacer { flex: 1; }

.tm-tab {
  background: transparent;
  border: 1px solid #252b34;
  color: #8b95a5;
  padding: 2px 8px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 11px;
}
.tm-tab.active { background: #1f2c3f; border-color: #3d7eff; color: #cfe0ff; }

.tm-chart { flex: 1; min-height: 0; }

.tm-chart-error {
  padding: 6px 12px;
  color: #c9922e;
  border-top: 1px solid #1c2027;
}

.tm-position { padding: 8px 10px; }

.tm-kv {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  color: #8b95a5;
}
.tm-kv > span:last-child { color: #dbe3ec; }

.tm-side-tag { font-weight: 600; }
.tm-side-tag.long { color: #26a37b; }
.tm-side-tag.short { color: #d0454c; }

.tm-decisions {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  flex: 1;
}

.tm-decision { padding: 6px 10px; border-bottom: 1px solid #171b21; }

.tm-decision-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tm-action { font-weight: 600; }
.tm-decision-reason { margin-top: 2px; }
.tm-dim { color: #6f7b8c; }

.tm-empty { padding: 12px 10px; color: #6f7b8c; }
</style>
