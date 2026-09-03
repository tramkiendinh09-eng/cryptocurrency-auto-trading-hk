<template>
  <div class="dashboard-container">
    <el-row :gutter="16" class="summary-grid">
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-card__content">
            <div class="summary-card__icon summary-card__icon--primary">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="summary-card__meta">
              <div class="summary-card__label">运行模式</div>
            <div class="summary-card__value">{{ runtimeMeta.modeLabel }}</div>
            <div class="summary-card__hint">
              <el-tag :type="runtimeMeta.modeTag" size="small">{{ runtimeMeta.modeLabel }}</el-tag>
              <el-tag :type="runtimeMeta.liveEnabled ? 'danger' : 'info'" size="small">
                {{ runtimeMeta.liveEnabled ? '实盘已启用' : '实盘已禁用' }}
              </el-tag>
            </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-card__content">
            <div class="summary-card__icon summary-card__icon--success">
              <el-icon><Grid /></el-icon>
            </div>
            <div class="summary-card__meta">
              <div class="summary-card__label">策略覆盖</div>
            <div class="summary-card__value">{{ stats.totalStrategies }}</div>
            <div class="summary-card__hint">活跃 {{ stats.activeStrategies }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-card__content">
            <div class="summary-card__icon summary-card__icon--warning">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <div class="summary-card__meta">
              <div class="summary-card__label">总盈亏</div>
            <div class="summary-card__value" :class="profitLoss.profitAmount >= 0 ? 'text-success' : 'text-danger'">
              {{ profitLoss.profitAmount >= 0 ? '+' : '' }}{{ formatNumber(profitLoss.profitAmount) }}
            </div>
            <div class="summary-card__hint">
              收益率 {{ profitLoss.profitRate >= 0 ? '+' : '' }}{{ formatNumber(profitLoss.profitRate) }}%
            </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-card__content">
            <div class="summary-card__icon summary-card__icon--danger">
              <el-icon><WarningFilled /></el-icon>
            </div>
            <div class="summary-card__meta">
              <div class="summary-card__label">风险控制</div>
            <div class="summary-card__value">{{ riskStats.todayBlocks }}</div>
            <div class="summary-card__hint">拦截率 {{ formatPercentage(riskStats.blockRate) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="summary-grid">
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-card__content">
            <div class="summary-card__icon summary-card__icon--info">
              <el-icon><Bell /></el-icon>
            </div>
            <div class="summary-card__meta">
              <div class="summary-card__label">决策运行</div>
            <div class="summary-card__value">{{ activityStats.decisionCount }}</div>
            <div class="summary-card__hint">
              事件 {{ activityStats.eventCount }} / 信号 {{ activityStats.signalCount }}
            </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-card__content">
            <div class="summary-card__icon summary-card__icon--cyan">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div class="summary-card__meta">
              <div class="summary-card__label">通知</div>
            <div class="summary-card__value">{{ notifyStats.todayCount }}</div>
            <div class="summary-card__hint">成功率 {{ formatPercentage(notifyStats.successRate) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-card__content">
            <div class="summary-card__icon summary-card__icon--violet">
              <el-icon><MagicStick /></el-icon>
            </div>
            <div class="summary-card__meta">
              <div class="summary-card__label">AI调用</div>
            <div class="summary-card__value">{{ aiStats.todayCalls || 0 }}</div>
            <div class="summary-card__hint">{{ formatNumber(aiStats.todayTokens || 0) }}  tokens</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-card__content">
            <div class="summary-card__icon" :class="workerStatus.online ? 'summary-card__icon--success' : 'summary-card__icon--slate'">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="summary-card__meta">
              <div class="summary-card__label">工作状态</div>
            <div class="summary-card__value">{{ workerStatus.online ? '在线' : '离线' }}</div>
            <div class="summary-card__hint">队列 {{ workerStatus.queueLength }} · 任务 {{ workerStatus.totalTasks }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="action-card">
      <template #header>
        <div class="section-header">
          <span>操作快捷方式</span>
          <el-button type="primary" plain size="small" :icon="Refresh" @click="loadOverview">刷新</el-button>
        </div>
      </template>
      <div class="shortcut-grid">
        <button
          v-for="item in shortcutItems"
          :key="item.key"
          type="button"
          class="shortcut-item"
          @click="goToShortcut(item.key)"
        >
          <div class="shortcut-item__title">{{ item.label }}</div>
          <div class="shortcut-item__desc">{{ item.description }}</div>
        </button>
      </div>
    </el-card>

    <el-row :gutter="16" class="content-grid">
      <el-col :xs="24" :xl="16">
        <el-card shadow="never" class="feed-card">
          <template #header>
        <div class="section-header">
          <span>运行时 feed</span>
          <div class="section-header__actions">
            <el-button link type="primary" size="small" @click="goToShortcut('decision')">决策</el-button>
            <el-button link type="primary" size="small" @click="goToShortcut('replay')">回放</el-button>
            <el-button link type="primary" size="small" @click="goToShortcut('risk-hits')">风险拦截</el-button>
            <el-button link type="primary" size="small" @click="goToShortcut('fills')">成交记录</el-button>
            <el-button link type="primary" size="small" @click="goToShortcut('orders')">订单</el-button>
            <el-button link type="primary" size="small" @click="goToShortcut('positions')">持仓</el-button>
          </div>
        </div>
      </template>
          <el-table :data="runtimeFeedRows" size="small" v-loading="loading" max-height="520">
            <el-table-column label="类型" width="110" align="center">
              <template #default="scope">
                <el-tag :type="getFeedTypeTag(scope.row.feedType)" size="small">
                  {{ getFeedTypeName(scope.row.feedType) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="symbol" label="交易对" width="110" align="center" />
            <el-table-column prop="summary" label="摘要" min-width="220" show-overflow-tooltip />
            <el-table-column label="状态" width="120" align="center">
              <template #default="scope">
                <el-tag :type="getRuntimeStatusTag(scope.row.status)" size="small">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="traceId" label="追踪ID" min-width="180" show-overflow-tooltip />
            <el-table-column label="时间" width="180" align="center">
              <template #default="scope">
                {{ formatTimestamp(scope.row.time) }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!loading && runtimeFeedRows.length === 0" description="暂无运行时记录" />
        </el-card>
      </el-col>

      <el-col :xs="24" :xl="8">
        <el-card shadow="never" class="side-card">
          <template #header>
        <div class="section-header">
          <span>运行时快照</span>
          <el-tag :type="runtimeMeta.modeTag" size="small">{{ runtimeMeta.modeLabel }}</el-tag>
        </div>
      </template>
      <el-descriptions :column="1" size="small" border>
        <el-descriptions-item label="实盘交易">
          <el-tag :type="runtimeMeta.liveEnabled ? 'danger' : 'info'" size="small">
            {{ runtimeMeta.liveEnabled ? '已启用' : '已禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="执行总数">{{ executionStats.total }}</el-descriptions-item>
        <el-descriptions-item label="已成交">{{ executionStats.filled }}</el-descriptions-item>
        <el-descriptions-item label="已拦截">{{ executionStats.blocked }}</el-descriptions-item>
        <el-descriptions-item label="已失败">{{ executionStats.failed }}</el-descriptions-item>
        <el-descriptions-item label="工作ID">{{ workerStatus.workerId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最后心跳">{{ formatTimestamp(workerStatus.lastHeartbeat) }}</el-descriptions-item>
      </el-descriptions>
        </el-card>

        <el-card shadow="never" class="side-card">
          <template #header>
        <div class="section-header">
          <span>系统状态</span>
        </div>
      </template>
      <div class="status-grid">
        <div class="status-item">
          <span class="status-item__label">Redis</span>
          <el-tag :type="systemStatus.redisConnected ? 'success' : 'danger'" size="small">
            {{ systemStatus.redisConnected ? '正常' : '宕机' }}
          </el-tag>
        </div>
        <div class="status-item">
          <span class="status-item__label">数据库</span>
          <el-tag :type="systemStatus.dbConnected ? 'success' : 'danger'" size="small">
            {{ systemStatus.dbConnected ? '正常' : '宕机' }}
          </el-tag>
        </div>
        <div class="status-item">
          <span class="status-item__label">队列</span>
          <el-tag type="info" size="small">{{ systemStatus.queueLength }}</el-tag>
        </div>
        <div class="status-item">
          <span class="status-item__label">API延迟</span>
          <el-tag :type="systemStatus.apiLatency > 1000 ? 'warning' : 'success'" size="small">
            {{ systemStatus.apiLatency || 0 }}ms
          </el-tag>
        </div>
      </div>
        </el-card>

        <el-card shadow="never" class="side-card">
          <template #header>
        <div class="section-header">
          <span>执行摘要</span>
          <el-tag type="info" size="small">总计 {{ executionStats.total }}</el-tag>
        </div>
      </template>
      <div class="execution-grid">
        <div v-for="item in executionSummaryItems" :key="item.key" class="execution-grid__item">
          <span class="execution-grid__label">{{ item.label }}</span>
          <el-tag :type="item.tagType" size="small">{{ item.value }}</el-tag>
        </div>
      </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
/**
 * 仪表盘页面工具函数模块
 * 提供执行统计、通知统计、工作状态、运行时feed等数据构建函数
 */

import { executionStatusTag } from '@/utils/tradeExecutionStatus'

const EXECUTION_STATUS_KEYS = ['filled', 'submitted', 'pending', 'partial', 'canceled', 'expired', 'failed', 'blocked', 'skipped']
const RUNTIME_FEED_KEYS = [
  'recentEvents',
  'recentSignals',
  'recentAgentConclusions',
  'recentDecisions',
  'recentRiskHits',
  'recentFills',
  'recentOrders',
  'recentPositions'
]

export function createExecutionStats(stats = {}) {
  return {
    total: Number(stats.total || 0),
    filled: Number(stats.filled || 0),
    submitted: Number(stats.submitted || 0),
    pending: Number(stats.pending || 0),
    partial: Number(stats.partial || 0),
    canceled: Number(stats.canceled || 0),
    expired: Number(stats.expired || 0),
    failed: Number(stats.failed || 0),
    blocked: Number(stats.blocked || 0),
    skipped: Number(stats.skipped || 0)
  }
}

export function buildExecutionSummaryItems(stats = {}) {
  const normalized = createExecutionStats(stats)
  return EXECUTION_STATUS_KEYS.map((key) => ({
    key,
    label: key.charAt(0).toUpperCase() + key.slice(1),
    value: normalized[key],
    tagType: executionStatusTag(key)
  }))
}

export function createNotifyStats(stats = {}) {
  return {
    successRate: Number(stats.successRate || 0),
    todayCount: Number(stats.todayCount || 0),
    weekTotal: Number(stats.weekTotal || 0),
    weekSuccess: Number(stats.weekSuccess || 0),
    weekFailed: Number(stats.weekFailed || 0)
  }
}

export function createRiskStats(stats = {}) {
  return {
    todayBlocks: Number(stats.todayBlocks || 0),
    blockRate: Number(stats.blockRate || 0)
  }
}

export function createWorkerStatus(status = {}) {
  const toNumber = (value) => {
    if (value === null || value === undefined || value === '') return 0
    const normalized = Number(value)
    return Number.isFinite(normalized) ? normalized : 0
  }

  return {
    online: Boolean(status?.online),
    workerId: status?.workerId,
    workerType: status?.workerType,
    pid: status?.pid,
    host: status?.host,
    totalTasks: toNumber(status?.totalTasks),
    successTasks: toNumber(status?.successTasks),
    failedTasks: toNumber(status?.failedTasks),
    queueLength: toNumber(status?.queueLength),
    lastHeartbeat: status?.lastHeartbeat
  }
}

export function createActivityStats(data = {}) {
  return {
    decisionCount: Number(data.decisionCount || 0),
    eventCount: Number(data.eventCount || 0),
    signalCount: Number(data.signalCount || 0),
    activePositionCount: Number(data.activePositionCount || 0)
  }
}

export function createRuntimeMeta(data = {}) {
  const normalizedMode = String(data?.runtimeConfig?.defaultMode || 'paper').trim().toLowerCase()
  return {
    mode: normalizedMode,
    modeLabel: normalizedMode.toUpperCase(),
    modeTag: normalizedMode === 'live' ? 'danger' : normalizedMode === 'shadow' ? 'warning' : 'info',
    liveEnabled: Boolean(data?.runtimeConfig?.liveEnabled)
  }
}

export function createRuntimeFeed(data = {}) {
  return RUNTIME_FEED_KEYS.reduce((acc, key) => {
    acc[key] = Array.isArray(data?.[key]) ? data[key] : []
    return acc
  }, {})
}

export function buildOverviewState(data = {}) {
  return {
    stats: {
      totalStrategies: data.totalStrategies || 0,
      activeStrategies: data.activeStrategies || 0,
      todayTriggers: data.todayTriggers || 0,
      todayNotifications: data.todayNotifications || 0,
      triggerTrend: data.triggerTrend || 0
    },
    activityStats: createActivityStats(data),
    profitLoss: {
      totalInvest: data.totalInvest || 0,
      currentValue: data.currentValue || 0,
      profitAmount: data.profitAmount || 0,
      profitRate: data.profitRate || 0
    },
    systemStatus: {
      workerOnline: data.workerOnline || false,
      redisConnected: data.redisConnected || false,
      dbConnected: data.dbConnected || false,
      queueLength: data.queueLength || 0,
      apiLatency: data.apiLatency || 0
    },
    workerStatus: createWorkerStatus(data.workerStatus),
    notifyStats: createNotifyStats(data.notifyStats),
    aiStats: data.aiStats || null,
    riskStats: createRiskStats(data.riskStats),
    executionStats: createExecutionStats(data.executionStats),
    runtimeFeed: createRuntimeFeed(data)
  }
}

function parseFeedTime(row = {}) {
  const timestamp = row.createdAt || row.triggerTime || row.updatedAt || row.lastHeartbeat || null
  const parsed = timestamp ? Date.parse(timestamp) : Number.NaN
  return Number.isFinite(parsed) ? parsed : 0
}

function createFeedRow(feedType, row = {}) {
  const summaryMap = {
    event: row.eventType || row.exchangeCode || '-',
    signal: row.signalType || '-',
    agentConclusion: row.reason || row.bias || '-',
    decision: row.action || row.mode || '-',
    riskHit: row.reason || row.ruleCode || '-',
    fill: row.orderRef || row.fillPrice || '-',
    order: row.side || row.status || row.orderStatus || '-',
    position: row.side || row.positionQuantity || '-'
  }

  let status = row.executionStatus || row.status || row.orderStatus || row.bias || row.action || row.ruleCode || '-'
  if (feedType === 'fill' && status === '-') {
    status = 'filled'
  }

  return {
    feedType,
    symbol: row.symbol || '-',
    summary: summaryMap[feedType] || '-',
    status,
    traceId: row.traceId || '-',
    time: row.createdAt || row.triggerTime || row.updatedAt || null,
    _sortTime: parseFeedTime(row)
  }
}

export function buildRuntimeFeedRows(feed = {}) {
  const normalized = createRuntimeFeed(feed)
  const rows = [
    ...normalized.recentEvents.map((row) => createFeedRow('event', row)),
    ...normalized.recentSignals.map((row) => createFeedRow('signal', row)),
    ...normalized.recentAgentConclusions.map((row) => createFeedRow('agentConclusion', row)),
    ...normalized.recentDecisions.map((row) => createFeedRow('decision', row)),
    ...normalized.recentRiskHits.map((row) => createFeedRow('riskHit', row)),
    ...normalized.recentFills.map((row) => createFeedRow('fill', row)),
    ...normalized.recentOrders.map((row) => createFeedRow('order', row)),
    ...normalized.recentPositions.map((row) => createFeedRow('position', row))
  ]
  return rows.sort((a, b) => b._sortTime - a._sortTime)
}

export function getDashboardShortcutPath(target) {
  const normalized = String(target || '').trim().toLowerCase()
  if (normalized === 'strategy') {
    return '/dca/trade/strategy'
  }
  if (normalized === 'runtime') {
    return '/dca/trade/runtime'
  }
   if (normalized === 'market-api' || normalized === 'marketapi' || normalized === 'market_api') {
    return '/dca/market'
  }
  if (normalized === 'source-binding' || normalized === 'sourcebinding' || normalized === 'source_binding') {
    return '/dca/market?tab=bindings'
  }
  if (normalized === 'accounts' || normalized === 'account' || normalized === 'exchange-accounts') {
    return '/dca/trade/account'
  }
  if (normalized === 'notify-policy' || normalized === 'notifypolicy' || normalized === 'notify_policy') {
    return '/dca/trade/notify-policy'
  }
  if (normalized === 'notify-channels' || normalized === 'notifychannels' || normalized === 'notify_channels') {
    return '/dca/notify'
  }
  if (normalized === 'notify-records' || normalized === 'notifyrecords' || normalized === 'notify_records') {
    return '/dca/notify/record'
  }
  if (normalized === 'decision') {
    return '/dca/trade/decision'
  }
  if (normalized === 'replay') {
    return '/dca/trade/replay'
  }
  if (normalized === 'risk-hits' || normalized === 'riskhits' || normalized === 'risk_hits') {
    return '/dca/trade/risk-hits'
  }
  if (normalized === 'fills') {
    return '/dca/trade/fills'
  }
  if (normalized === 'orders') {
    return '/dca/trade/orders'
  }
  if (normalized === 'positions') {
    return '/dca/trade/positions'
  }
  return '/dca/dashboard'
}
</script>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Bell,
  ChatDotRound,
  Grid,
  MagicStick,
  Monitor,
  Refresh,
  TrendCharts,
  WarningFilled
} from '@element-plus/icons-vue'
import { getOverview } from '@/api/dca/dashboard'
import { getDashboardRuntimeFeed } from '@/api/dca/tradeRuntime'
import { parseTime } from '@/utils/ruoyi'
import { executionStatusTag } from '@/utils/tradeExecutionStatus'

const shortcutItems = [
  { key: 'market-api', label: '行情数据源', description: '统一维护REST/WebSocket数据源和运行时绑定' },
  { key: 'accounts', label: '交易所账户', description: '持久化的账户凭证、健康状态和运行时标志' },
  { key: 'notify-policy', label: '通知策略', description: '持久化的严重性路由和渠道策略绑定' },
  { key: 'notify-channels', label: '通知渠道', description: '在notify_channel中持久化的渠道定义' },
  { key: 'notify-records', label: '通知记录', description: '在notify_record中持久化的投递审计追踪' },
  { key: 'strategy', label: '运行时策略', description: '交易策略版本和作用域' },
  { key: 'runtime', label: '运行时控制台', description: '实盘模式、风险和运行时概览' },
  { key: 'decision', label: '决策审计', description: '监督决策和审计追踪' },
  { key: 'replay', label: '回放控制台', description: '追踪回放会话、源数据和比较' },
  { key: 'risk-hits', label: '风险拦截', description: '风险防护拦截和阻止原因' },
  { key: 'fills', label: '成交记录', description: '交易所成交和执行详情' },
  { key: 'orders', label: '订单', description: '执行请求和订单状态' },
  { key: 'positions', label: '持仓', description: '未平仓头寸和盈亏快照' }
]

const router = useRouter()
const loading = ref(false)
const runtimeMeta = ref(createRuntimeMeta())
const stats = ref({
  totalStrategies: 0,
  activeStrategies: 0,
  todayTriggers: 0,
  todayNotifications: 0,
  triggerTrend: 0
})
const activityStats = ref(createActivityStats())
const profitLoss = ref({
  totalInvest: 0,
  currentValue: 0,
  profitAmount: 0,
  profitRate: 0
})
const workerStatus = ref(createWorkerStatus())
const systemStatus = ref({
  workerOnline: false,
  redisConnected: false,
  dbConnected: false,
  queueLength: 0,
  apiLatency: 0
})
const notifyStats = ref(createNotifyStats())
const aiStats = ref({
  todayCalls: 0,
  todayTokens: 0
})
const riskStats = ref(createRiskStats())
const executionStats = ref(createExecutionStats())
const runtimeFeed = ref(createRuntimeFeed())
const executionSummaryItems = computed(() => buildExecutionSummaryItems(executionStats.value))
const runtimeFeedRows = computed(() => buildRuntimeFeedRows(runtimeFeed.value))

let refreshTimer = null

const formatPercentage = (value) => {
  const normalized = Number(value)
  if (!Number.isFinite(normalized)) return '0%'
  return `${normalized.toFixed(1)}%`
}

const formatSignedPercent = (value) => {
  const normalized = Number(value)
  if (!Number.isFinite(normalized)) return '0.0%'
  return `${normalized >= 0 ? '+' : ''}${normalized.toFixed(1)}%`
}

const formatNumber = (value) => {
  const normalized = Number(value)
  if (!Number.isFinite(normalized)) return '0.00'
  return normalized.toFixed(2)
}

const formatTimestamp = (value) => {
  if (!value) return '-'
  return parseTime(value) || '-'
}

const feedTypeNameMap = {
  event: 'Event',
  signal: 'Signal',
  agentConclusion: 'Agent',
  decision: 'Decision',
  riskHit: 'Risk',
  fill: 'Fill',
  order: 'Order',
  position: 'Position'
}

const feedTypeTagMap = {
  event: 'info',
  signal: 'warning',
  agentConclusion: 'primary',
  decision: 'success',
  riskHit: 'danger',
  fill: 'success',
  order: 'warning',
  position: ''
}

const getFeedTypeName = (type) => feedTypeNameMap[type] || type || '-'
const getFeedTypeTag = (type) => feedTypeTagMap[type] || 'info'

const getRuntimeStatusTag = (status) => {
  const normalized = String(status || '').trim().toLowerCase()
  if (normalized === 'blocked' || normalized === 'rejected') {
    return 'danger'
  }
  if (normalized === 'skip' || normalized === 'skipped') {
    return 'info'
  }
  return executionStatusTag(normalized)
}

const goToShortcut = (target) => {
  router.push(getDashboardShortcutPath(target))
}

const loadOverview = async () => {
  loading.value = true
  try {
    const [overviewRes, runtimeFeedRes] = await Promise.allSettled([
      getOverview(),
      getDashboardRuntimeFeed()
    ])

    if (overviewRes.status === 'fulfilled' && overviewRes.value.code === 200) {
      const normalized = buildOverviewState(overviewRes.value.data)
      stats.value = normalized.stats
      activityStats.value = normalized.activityStats
      profitLoss.value = normalized.profitLoss
      systemStatus.value = normalized.systemStatus
      workerStatus.value = normalized.workerStatus
      notifyStats.value = normalized.notifyStats
      aiStats.value = normalized.aiStats || { todayCalls: 0, todayTokens: 0 }
      riskStats.value = normalized.riskStats
      executionStats.value = normalized.executionStats
      runtimeFeed.value = normalized.runtimeFeed
    }

    if (runtimeFeedRes.status === 'fulfilled' && runtimeFeedRes.value.code === 200) {
      const runtimeData = runtimeFeedRes.value.data || {}
      runtimeMeta.value = createRuntimeMeta(runtimeData)
      runtimeFeed.value = createRuntimeFeed(runtimeData)
      if (runtimeData.executionStats) {
        executionStats.value = createExecutionStats(runtimeData.executionStats)
      }
    }
  } catch (error) {
    console.error('Failed to load dashboard data', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadOverview()
  refreshTimer = setInterval(loadOverview, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped lang="scss">
.dashboard-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  background: #f8fafc;
  min-height: 100vh;
}

.summary-grid,
.content-grid {
  margin: 0;
}

/* 汇总卡片 */
.summary-card {
  border: 1px solid var(--rf-line, #e6eaee);
  border-radius: var(--rf-radius, 10px);
  background: var(--rf-surface, #fff);
  box-shadow: var(--rf-shadow, 0 1px 3px rgba(16, 24, 40, .06));
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
}

.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.summary-card__content {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
}

/* 图标渐变背景 */
.summary-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  font-size: 18px;
  border-radius: 9px;
  color: #fff;
  font-size: 24px;
  flex-shrink: 0;
}

.summary-card__icon--primary {
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
  color: #4f46e5;
}

.summary-card__icon--success {
  background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
  color: #16a34a;
}

.summary-card__icon--warning {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
}

.summary-card__icon--danger {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  color: #dc2626;
}

.summary-card__icon--info {
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
  color: #0284c7;
}

.summary-card__icon--cyan {
  background: linear-gradient(135deg, #cffafe 0%, #a5f3fc 100%);
  color: #0891b2;
}

.summary-card__icon--violet {
  background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%);
  color: #7c3aed;
}

.summary-card__icon--slate {
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  color: #64748b;
}

.summary-card__meta {
  flex: 1;
  min-width: 0;
}

.summary-card__label {
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.summary-card__value {
  margin-top: 2px;
  color: var(--rf-ink, #1e293b);
  font-size: 23px;
  font-weight: 650;
  line-height: 1.2;
  letter-spacing: -.4px;
}

.summary-card__hint {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  color: #64748b;
  font-size: 13px;
}

/* 操作快捷方式卡片 */
.action-card {
  border: none;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.action-card :deep(.el-card__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
}

.action-card :deep(.el-card__body) {
  padding: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 600;
  color: #1e293b;
  font-size: 15px;
}

.section-header__actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

/* 快捷方式网格 */
.shortcut-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.shortcut-item {
  padding: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  text-align: left;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.shortcut-item:hover {
  transform: translateY(-2px);
  border-color: #c7d2fe;
  box-shadow: 0 4px 20px rgba(79, 70, 229, 0.1);
}

.shortcut-item__title {
  color: #1e293b;
  font-size: 15px;
  font-weight: 600;
}

.shortcut-item__desc {
  margin-top: 8px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

/* Feed卡片 */
.feed-card {
  border: none;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  height: 100%;
}

.feed-card :deep(.el-card__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
}

.feed-card :deep(.el-card__body) {
  padding: 24px;
}

/* 侧边卡片 */
.side-card {
  border: none;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  margin-bottom: 16px;
}

.side-card :deep(.el-card__header) {
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
}

.side-card :deep(.el-card__body) {
  padding: 20px;
}

.side-card:last-child {
  margin-bottom: 0;
}

/* 状态网格 */
.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.status-item,
.execution-grid__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  background: #f8fafc;
}

.status-item__label,
.execution-grid__label {
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
}

/* 执行摘要网格 */
.execution-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

/* Element Plus组件样式 */
:deep(.el-table) {
  border-radius: 12px;
}

:deep(.el-table th.el-table__cell) {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  font-size: 13px;
}

:deep(.el-table td.el-table__cell) {
  font-size: 13px;
}

:deep(.el-descriptions) {
  border-radius: 12px;
}

:deep(.el-descriptions__label) {
  background: #f8fafc;
  color: #64748b;
  font-weight: 500;
  font-size: 13px;
}

:deep(.el-descriptions__content) {
  font-size: 13px;
}

:deep(.el-tag) {
  border-radius: 8px;
}

.text-success {
  color: #16a34a;
}

.text-danger {
  color: #dc2626;
}

/* 响应式布局 */
@media (max-width: 1400px) {
  .shortcut-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1200px) {
  .shortcut-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .execution-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .dashboard-container {
    padding: 16px;
    gap: 16px;
  }

  .summary-card__content {
    padding: 16px;
  }

  .summary-card__icon {
    width: 48px;
    height: 48px;
    font-size: 20px;
    border-radius: 12px;
  }

  .summary-card__value {
    font-size: 24px;
  }

  .shortcut-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .shortcut-item {
    padding: 16px;
    border-radius: 12px;
  }

  .shortcut-item__title {
    font-size: 14px;
  }

  .shortcut-item__desc {
    font-size: 12px;
  }

  .status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .execution-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .status-item,
  .execution-grid__item {
    padding: 12px 14px;
    border-radius: 10px;
  }

  .section-header {
    flex-wrap: wrap;
    gap: 8px;
  }

  .section-header__actions {
    flex-wrap: wrap;
    gap: 6px;
  }

  :deep(.el-card__header) {
    padding: 16px;
  }

  :deep(.el-card__body) {
    padding: 16px;
  }

  :deep(.el-table th.el-table__cell) {
    font-size: 12px;
  }

  :deep(.el-table td.el-table__cell) {
    font-size: 12px;
  }

  :deep(.el-descriptions__label) {
    font-size: 12px;
  }

  :deep(.el-descriptions__content) {
    font-size: 12px;
  }
}

@media (max-width: 480px) {
  .dashboard-container {
    padding: 12px;
    gap: 12px;
  }

  .summary-card__content {
    padding: 14px;
    gap: 12px;
  }

  .summary-card__icon {
    width: 44px;
    height: 44px;
    font-size: 18px;
    border-radius: 10px;
  }

  .summary-card__label {
    font-size: 12px;
  }

  .summary-card__value {
    font-size: 22px;
    margin-top: 6px;
  }

  .summary-card__hint {
    font-size: 12px;
    gap: 6px;
    margin-top: 8px;
  }

  .shortcut-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .shortcut-item {
    padding: 14px;
    border-radius: 10px;
  }

  .shortcut-item__title {
    font-size: 13px;
  }

  .shortcut-item__desc {
    font-size: 11px;
    margin-top: 6px;
  }

  .status-grid {
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }

  .execution-grid {
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }

  .status-item,
  .execution-grid__item {
    padding: 10px 12px;
    border-radius: 8px;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .status-item__label,
  .execution-grid__label {
    font-size: 11px;
  }

  .section-header {
    font-size: 14px;
  }

  :deep(.el-card) {
    border-radius: 12px;
  }

  :deep(.el-card__header) {
    padding: 12px 14px;
  }

  :deep(.el-card__body) {
    padding: 14px;
  }

  :deep(.el-table) {
    font-size: 11px;
  }

  :deep(.el-table th.el-table__cell) {
    font-size: 11px;
    padding: 8px 0;
  }

  :deep(.el-table td.el-table__cell) {
    font-size: 11px;
    padding: 8px 0;
  }

  :deep(.el-button) {
    font-size: 12px;
    padding: 8px 12px;
  }

  :deep(.el-tag) {
    font-size: 11px;
    padding: 2px 6px;
  }

  .feed-card :deep(.el-table) {
    max-height: 300px;
  }
}
</style>
