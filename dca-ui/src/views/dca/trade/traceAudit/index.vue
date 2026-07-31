<template>
  <div v-loading="loading" class="app-container trace-audit-page">
    <el-card shadow="never" class="query-card">
      <el-form inline @submit.prevent>
        <el-form-item label="追踪ID">
          <el-input
            v-model.trim="traceId"
            clearable
            placeholder="请输入追踪ID"
            style="width: 420px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleQuery">查询</el-button>
          <el-button @click="handleReset">清空</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-empty
      v-if="!hasSearched"
      description="请输入追踪ID后查询审计明细"
    />

    <el-empty
      v-else-if="!hasData"
      description="未查询到该追踪ID的审计数据"
    />

    <template v-else>
      <el-row :gutter="16" class="section-grid">
        <el-col :span="24">
          <el-card shadow="never">
            <template #header>
              <div class="section-header">
                <span>概览</span>
                <el-tag :type="traceAuditStatusTag(auditState.summary.executionStatus)">
                  {{ formatExecutionStatus(auditState.summary.executionStatus || 'unknown') }}
                </el-tag>
              </div>
            </template>
            <el-descriptions :column="4" border>
              <el-descriptions-item label="追踪ID">{{ auditState.summary.traceId || '-' }}</el-descriptions-item>
              <el-descriptions-item label="交易对">{{ auditState.summary.symbol || '-' }}</el-descriptions-item>
              <el-descriptions-item label="交易所">{{ auditState.summary.exchangeCode || '-' }}</el-descriptions-item>
              <el-descriptions-item label="模式">{{ formatRuntimeMode(auditState.summary.mode) }}</el-descriptions-item>
              <el-descriptions-item label="动作">{{ formatAction(auditState.summary.action) }}</el-descriptions-item>
              <el-descriptions-item label="置信度">{{ formatPercent(auditState.summary.confidence) }}</el-descriptions-item>
              <el-descriptions-item label="订单状态">{{ formatOrderStatus(auditState.summary.orderStatus) }}</el-descriptions-item>
              <el-descriptions-item label="首条时间">{{ auditState.summary.createdAt || '-' }}</el-descriptions-item>
              <el-descriptions-item label="事件数">{{ auditState.summary.eventCount ?? 0 }}</el-descriptions-item>
              <el-descriptions-item label="风控命中">{{ auditState.summary.riskHitCount ?? 0 }}</el-descriptions-item>
              <el-descriptions-item label="成交数">{{ auditState.summary.fillCount ?? 0 }}</el-descriptions-item>
              <el-descriptions-item label="通知数">{{ auditState.summary.notifyCount ?? 0 }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="section-grid">
        <el-col :span="14">
          <el-card shadow="never" class="full-height-card">
            <template #header>
              <div class="section-header">
                <span>事件时间线</span>
                <span class="section-count">{{ auditState.events.length }} 条</span>
              </div>
            </template>
            <el-empty v-if="!auditState.events.length" description="暂无事件" />
            <el-timeline v-else class="event-timeline">
              <el-timeline-item
                v-for="event in auditState.events"
                :key="event.id || `${event.eventType}-${event.createdAt}`"
                :timestamp="event.createdAt || '-'"
                placement="top"
              >
                <el-card shadow="hover" class="timeline-card">
                  <div class="timeline-card__header">
                    <div>
                      <div class="timeline-card__title">{{ event.displayTitle || event.eventType || '-' }}</div>
                      <div class="timeline-card__subtitle">{{ event.displaySubtitle || '-' }}</div>
                    </div>
                    <el-tag size="small">{{ formatEventType(event.eventType || 'unknown') }}</el-tag>
                  </div>
                  <div class="timeline-card__meta">{{ formatTraceAuditEventMeta(event) }}</div>
                  <pre class="json-block">{{ formatTraceAuditJson(event.payload) }}</pre>
                </el-card>
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </el-col>

        <el-col :span="10">
          <el-row :gutter="16">
            <el-col :span="24">
              <el-card shadow="never">
                <template #header>
                  <div class="section-header">
                    <span>决策</span>
                    <el-tag :type="traceAuditStatusTag(auditState.decision?.executionStatus)">
                      {{ formatExecutionStatus(auditState.decision?.executionStatus || 'unknown') }}
                    </el-tag>
                  </div>
                </template>
                <el-empty v-if="!auditState.decision" description="暂无决策记录" />
                <el-descriptions v-else :column="1" size="small" border>
                  <el-descriptions-item label="动作">{{ formatAction(auditState.decision.action) }}</el-descriptions-item>
                  <el-descriptions-item label="置信度">{{ formatPercent(auditState.decision.confidence) }}</el-descriptions-item>
                  <el-descriptions-item label="模型">{{ formatDecisionModel(auditState.decision) }}</el-descriptions-item>
                  <el-descriptions-item label="提示词来源">{{ formatPromptSource(auditState.decision.promptSource) }}</el-descriptions-item>
                  <el-descriptions-item label="绑定模板">{{ auditState.decision.bindingTemplateCode || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="回退模板">{{ auditState.decision.fallbackTemplateCode || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="实际模板">{{ auditState.decision.resolvedTemplateCode || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="触发原因">{{ auditState.decision.triggerReason || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="摘要">{{ auditState.decision.summaryReason || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="交易记忆">
                    <div class="trade-memory-cell">
                      <el-tag
                        v-if="resolveTradeMemoryStatus(auditState.decision) !== '-'"
                        size="small"
                        :type="tradeMemoryStatusTag(resolveTradeMemoryStatus(auditState.decision))"
                      >
                        {{ resolveTradeMemoryStatus(auditState.decision) }}
                      </el-tag>
                      <span>{{ formatTradeMemoryOutcome(auditState) }}</span>
                    </div>
                  </el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>

            <el-col :span="24" class="section-gap">
              <el-card shadow="never">
                <template #header>
                  <div class="section-header">
                    <span>风控命中</span>
                    <span class="section-count">{{ auditState.riskHits.length }} 条</span>
                  </div>
                </template>
                <el-empty v-if="!auditState.riskHits.length" description="暂无风控命中" />
                <el-table v-else :data="auditState.riskHits" size="small">
                  <el-table-column prop="createdAt" label="时间" min-width="150" />
                  <el-table-column prop="ruleCode" label="规则编码" min-width="160" show-overflow-tooltip />
                  <el-table-column prop="reason" label="原因" min-width="220" show-overflow-tooltip />
                </el-table>
              </el-card>
            </el-col>
          </el-row>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="section-grid">
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>
              <div class="section-header">
                <span>订单与成交</span>
                <el-tag :type="traceAuditStatusTag(auditState.order?.executionStatus)">
                  {{ formatExecutionStatus(auditState.order?.executionStatus || 'unknown') }}
                </el-tag>
              </div>
            </template>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="订单方向">{{ formatOrderSide(auditState.order?.side) }}</el-descriptions-item>
              <el-descriptions-item label="订单引用">{{ auditState.order?.orderRef || '-' }}</el-descriptions-item>
              <el-descriptions-item label="执行参数">{{ formatOrderExecutionMeta(auditState.order) }}</el-descriptions-item>
              <el-descriptions-item label="订单状态">{{ formatOrderStatus(auditState.order?.orderStatus) }}</el-descriptions-item>
              <el-descriptions-item label="执行状态">{{ formatExecutionStatus(auditState.order?.executionStatus) }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ auditState.order?.createdAt || '-' }}</el-descriptions-item>
            </el-descriptions>
            <div class="subsection-title">成交明细</div>
            <el-empty v-if="!auditState.fills.length" description="暂无成交" />
            <el-table v-else :data="auditState.fills" size="small">
              <el-table-column prop="createdAt" label="时间" min-width="150" />
              <el-table-column prop="orderRef" label="订单引用" min-width="160" show-overflow-tooltip />
              <el-table-column prop="fillPrice" label="成交价格" min-width="120" />
              <el-table-column prop="fillQuantity" label="成交数量" min-width="120" />
            </el-table>
          </el-card>
        </el-col>

        <el-col :span="12">
          <el-card shadow="never">
            <template #header>
              <div class="section-header">
                <span>持仓与盈亏</span>
              </div>
            </template>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item
                v-for="item in tradeAuditSummaryRows"
                :key="item.key"
                :label="item.label"
              >
                <span :style="{ color: item.tone === 'success' ? '#67c23a' : item.tone === 'danger' ? '#f56c6c' : undefined }">
                  {{ item.value }}
                </span>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="section-grid">
        <el-col :span="24">
          <el-card shadow="never">
            <template #header>
              <div class="section-header">
                <span>通知记录</span>
                <span class="section-count">{{ auditState.notifications.length }} 条</span>
              </div>
            </template>
            <el-empty v-if="!auditState.notifications.length" description="暂无通知记录" />
            <el-table v-else :data="auditState.notifications" size="small">
              <el-table-column prop="createTime" label="时间" min-width="160" />
              <el-table-column prop="channelName" label="通知渠道" min-width="140" show-overflow-tooltip />
              <el-table-column prop="channelType" label="渠道类型" min-width="120" />
              <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
              <el-table-column label="状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="notifyStatusTag(scope.row.status)">
                    {{ formatNotifyStatus(scope.row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="errorMsg" label="错误信息" min-width="220" show-overflow-tooltip />
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="section-grid">
        <el-col :span="24">
          <el-card shadow="never">
            <template #header>
              <div class="section-header">
                <span>原始数据</span>
              </div>
            </template>
            <pre class="json-block json-block--large">{{ formatTraceAuditJson(auditState) }}</pre>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script>
/**
 * 追踪审计页面工具函数模块
 * 提供追踪审计状态构建、数据格式化等辅助函数
 */

import { formatTradeLabel } from '@/utils/tradeLabels'

export function buildTraceAuditState(payload) {
  return {
    summary: payload?.summary || {},
    events: Array.isArray(payload?.events) ? payload.events : [],
    decision: payload?.decision || null,
    riskHits: Array.isArray(payload?.riskHits) ? payload.riskHits : [],
    order: payload?.order || null,
    fills: Array.isArray(payload?.fills) ? payload.fills : [],
    tradeSummary: payload?.tradeSummary || null,
    positionSnapshot: payload?.positionSnapshot || null,
    pnlSnapshot: payload?.pnlSnapshot || null,
    notifications: Array.isArray(payload?.notifications) ? payload.notifications : []
  }
}

function formatTradeAuditValue(value) {
  return value === undefined || value === null || value === '' ? '-' : String(value)
}

function formatTradeAuditPnl(value) {
  if (value === undefined || value === null || value === '') {
    return '-'
  }
  const amount = Number(value)
  if (Number.isNaN(amount)) {
    return String(value)
  }
  const sign = amount > 0 ? '+' : ''
  return `${sign}${amount.toFixed(4)}`
}

function formatTradeAuditPnlTone(value) {
  const amount = Number(value)
  if (Number.isNaN(amount)) {
    return 'info'
  }
  if (amount > 0) {
    return 'success'
  }
  if (amount < 0) {
    return 'danger'
  }
  return 'info'
}

export function buildTradeAuditSummaryRows(state = {}) {
  const tradeSummary = state?.tradeSummary || {}
  const positionSnapshot = state?.positionSnapshot || {}
  const pnlSnapshot = state?.pnlSnapshot || {}
  const realizedPnl = tradeSummary.realizedPnl ?? pnlSnapshot.realizedPnl
  const rows = [
    { key: 'positionSide', label: '持仓方向', value: formatPositionSide(tradeSummary.positionSide || positionSnapshot.side) },
    { key: 'fillQuantity', label: '成交数量', value: formatTradeAuditValue(tradeSummary.fillQuantity) },
    { key: 'openPrice', label: '开仓价格', value: formatTradeAuditValue(tradeSummary.openPrice) },
    { key: 'closePrice', label: '平仓价格', value: formatTradeAuditValue(tradeSummary.closePrice) },
    { key: 'realizedPnl', label: '已实现盈亏', value: formatTradeAuditPnl(realizedPnl), tone: formatTradeAuditPnlTone(realizedPnl) },
    { key: 'positionQuantity', label: '剩余仓位', value: formatTradeAuditValue(tradeSummary.positionQuantity ?? positionSnapshot.positionQuantity) },
    { key: 'entryPrice', label: '当前持仓均价', value: formatTradeAuditValue(tradeSummary.entryPrice ?? positionSnapshot.entryPrice) },
    { key: 'unrealizedPnl', label: '持仓浮盈亏', value: formatTradeAuditValue(positionSnapshot.unrealizedPnl ?? pnlSnapshot.unrealizedPnl) },
    { key: 'accountEquity', label: '账户权益', value: formatTradeAuditValue(pnlSnapshot.accountEquity) },
    { key: 'dailyPnl', label: '当日盈亏', value: formatTradeAuditValue(pnlSnapshot.dailyPnl) },
    { key: 'positionCreatedAt', label: '持仓时间', value: formatTradeAuditValue(positionSnapshot.createdAt) },
    { key: 'maxDrawdownPct', label: '最大回撤', value: formatTradeAuditValue(pnlSnapshot.maxDrawdownPct) }
  ]
  const tradeMemoryStatus = resolveTradeMemoryStatus(state?.decision || {})
  if (tradeMemoryStatus !== '-') {
    rows.push({ key: 'tradeMemoryStatus', label: '交易记忆状态', value: tradeMemoryStatus })
  }
  const tradeMemoryOutcome = formatTradeMemoryOutcome(state)
  if (tradeMemoryOutcome !== '-') {
    rows.push({ key: 'tradeMemoryLesson', label: '交易记忆结论', value: tradeMemoryOutcome })
  }
  return rows
}

export function formatMemorySummary(row = {}) {
  const usage = row?.memoryUsage || row?.memory_usage || {}
  const counts = usage?.short_term_counts || usage?.shortTermCounts || {}
  const longTermCount = Number(usage?.long_term_count ?? usage?.longTermCount ?? 0)
  const shortTotal = ['market', 'news', 'onchain', 'social', 'supervisor_decision']
    .map((key) => Number(counts?.[key] || 0))
    .reduce((sum, value) => sum + value, 0)
  if (!shortTotal && !longTermCount) {
    return '-'
  }
  return `?? ${shortTotal} / ?? ${longTermCount}`
}

function extractLifecycleStatus(row = {}) {
  const direct = row?.lifecycleStatus || row?.lifecycle_status
  if (direct && typeof direct === 'object') {
    return direct
  }
  const nested = row?.featureSnapshot?.snapshot?.lifecycleStatus
  if (nested && typeof nested === 'object') {
    return nested
  }
  return {}
}

function extractTradeMemoryStatus(row = {}) {
  const direct = row?.tradeMemoryStatus || row?.trade_memory_status
  if (direct && typeof direct === 'object') {
    return direct
  }
  const nested = row?.featureSnapshot?.snapshot?.tradeMemoryStatus
  if (nested && typeof nested === 'object') {
    return nested
  }
  return {}
}

export function resolveTradeMemoryStatus(row = {}) {
  const tradeMemoryStatus = extractTradeMemoryStatus(row)
  const lifecycleStatus = extractLifecycleStatus(row)
  return String(
    tradeMemoryStatus?.status ||
      lifecycleStatus?.memory_status ||
      lifecycleStatus?.memoryStatus ||
      ''
  ).trim() || '-'
}

export function tradeMemoryStatusTag(status) {
  switch (String(status || '').trim().toLowerCase()) {
    case 'stored':
      return 'success'
    case 'failed':
      return 'danger'
    case 'rejected':
      return 'warning'
    default:
      return 'info'
  }
}

export function formatTradeMemoryOutcome(state = {}) {
  const decision = state?.decision || state
  const tradeMemoryStatus = extractTradeMemoryStatus(decision)
  const lifecycleStatus = extractLifecycleStatus(decision)
  const lessonText = String(
    tradeMemoryStatus?.lesson_text ||
      tradeMemoryStatus?.lessonText ||
      lifecycleStatus?.memory?.lesson_text ||
      lifecycleStatus?.memory?.lessonText ||
      ''
  ).trim()
  if (lessonText) {
    return lessonText
  }
  const status = resolveTradeMemoryStatus(decision)
  const reason = String(
    tradeMemoryStatus?.reason ||
      lifecycleStatus?.memory_reason ||
      lifecycleStatus?.memoryReason ||
      ''
  ).trim()
  if (status !== '-' && reason) {
    return `${status} / ${reason}`
  }
  return status
}

export function traceAuditStatusTag(status) {
  const normalized = String(status || '').trim().toLowerCase()
  if (normalized === 'filled' || normalized === 'success') {
    return 'success'
  }
  if (normalized === 'submitted' || normalized === 'pending' || normalized === 'partial') {
    return 'warning'
  }
  if (normalized === 'blocked' || normalized === 'failed' || normalized === 'rejected' || normalized === 'canceled') {
    return 'danger'
  }
  return 'info'
}

export function formatTraceAuditEventMeta(event = {}) {
  const payload = event?.payload || {}
  const eventType = String(event?.eventType || '').trim().toLowerCase()
  if (eventType === 'market_tick') {
    return `价格 ${fallbackText(payload.price)} | 成交量 ${fallbackText(payload.volume)}`
  }
  if (eventType === 'news' || eventType === 'social') {
    return `来源 ${fallbackText(payload.source)} | 事件时间 ${fallbackText(payload.event_time)} | 分数 ${fallbackText(payload.score)}`
  }
  if (eventType === 'onchain') {
    return `钱包 ${fallbackText(payload.wallet || payload.address)} | 流向 ${fallbackText(payload.flow)} | 金额USD ${fallbackText(payload.amountUsd || payload.amount_usd)}`
  }
  if (eventType === 'source_health') {
    return `来源类型 ${fallbackText(payload.source_type)} | 状态 ${formatTradeLabel('sourceStatus', payload.source_status) || fallbackText(payload.source_status)} | 原因 ${fallbackText(payload.reason)}`
  }
  return Object.entries(payload)
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${fallbackText(value)}`)
    .join(' | ')
}

export function formatTraceAuditJson(value) {
  try {
    return JSON.stringify(value ?? {}, null, 2)
  } catch (error) {
    return '{}'
  }
}

export function formatDecisionModel(row = {}) {
  const modelCode = String(row?.modelCode || '').trim()
  const modelProvider = String(row?.modelProvider || '').trim()
  if (modelCode && modelProvider) {
    return `${modelCode} / ${modelProvider}`
  }
  if (modelCode) {
    return modelCode
  }
  if (modelProvider) {
    return modelProvider
  }
  return '-'
}


export function formatOrderExecutionMeta(order = {}) {
  const parts = []
  if (order.action) {
    parts.push(String(order.action))
  }
  if (order.orderType) {
    parts.push(String(order.orderType))
  }
  if (order.positionSide) {
    parts.push(String(order.positionSide))
  }
  if (order.reduceOnly === true || order.reduceOnly === false) {
    parts.push(`reduceOnly=${order.reduceOnly}`)
  }
  if (order.tdMode) {
    parts.push(String(order.tdMode))
  }
  if (order.leverage !== undefined && order.leverage !== null && order.leverage !== '') {
    parts.push(`${order.leverage}x`)
  }
  if (order.limitPrice !== undefined && order.limitPrice !== null && order.limitPrice !== '') {
    parts.push(`px ${order.limitPrice}`)
  }
  if (order.quantityBase !== undefined && order.quantityBase !== null && order.quantityBase !== '') {
    parts.push(`qty ${order.quantityBase}`)
  }
  if (order.okxEnhancedExecution === true) {
    parts.push('OKX+')
  }
  return parts.length ? parts.join(' / ') : '-'
}

function fallbackText(value) {
  return value === undefined || value === null || value === '' ? '-' : String(value)
}

export function formatRuntimeMode(value) {
  return formatTradeLabel('runtimeMode', value) || '-'
}

export function formatAction(value) {
  return formatTradeLabel('action', value) || '-'
}

export function normalizePositionSide(value) {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'buy') {
    return 'long'
  }
  if (normalized === 'sell') {
    return 'short'
  }
  if (['long', 'short', 'flat'].includes(normalized)) {
    return normalized
  }
  return normalized
}

export function formatPositionSide(value) {
  return formatTradeLabel('orderSide', normalizePositionSide(value)) || '-'
}

export function formatOrderSide(value) {
  return formatTradeLabel('orderSide', value) || '-'
}

export function formatExecutionStatus(value) {
  return formatTradeLabel('executionStatus', value) || '-'
}

export function formatOrderStatus(value) {
  return formatTradeLabel('orderStatus', value) || '-'
}

export function formatEventType(value) {
  return formatTradeLabel('eventType', value) || '-'
}

export function formatPromptSource(value) {
  return formatTradeLabel('promptSource', value) || '-'
}
</script>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getTraceAuditDetail } from '@/api/dca/traceAudit'

const route = useRoute()

const loading = ref(false)
const traceId = ref('')
const hasSearched = ref(false)
const auditState = ref(buildTraceAuditState())

const hasData = computed(() => {
  return Boolean(auditState.value.summary?.traceId)
})

const tradeAuditSummaryRows = computed(() => buildTradeAuditSummaryRows(auditState.value))

async function handleQuery() {
  if (!traceId.value) {
    ElMessage.warning('请输入追踪ID')
    return
  }
  hasSearched.value = true
  loading.value = true
  try {
    const response = await getTraceAuditDetail(traceId.value)
    auditState.value = buildTraceAuditState(response?.data)
  } catch (error) {
    auditState.value = buildTraceAuditState()
    ElMessage.error('加载追踪审计失败')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  traceId.value = ''
  hasSearched.value = false
  auditState.value = buildTraceAuditState()
}

function formatPercent(value) {
  if (value === undefined || value === null || value === '') {
    return '-'
  }
  return `${value}%`
}

function formatNotifyStatus(status) {
  if (status === 0) return '待发送'
  if (status === 1) return '发送中'
  if (status === 2) return '成功'
  if (status === 3) return '失败'
  return '-'
}

function notifyStatusTag(status) {
  if (status === 2) return 'success'
  if (status === 1) return 'warning'
  if (status === 3) return 'danger'
  return 'info'
}

onMounted(() => {
  const initialTraceId = String(route.query.traceId || '').trim()
  if (initialTraceId) {
    traceId.value = initialTraceId
    handleQuery()
  }
})
</script>

<style scoped>
.query-card {
  margin-bottom: 16px;
}

.section-grid {
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-count {
  color: #909399;
  font-size: 12px;
}

.full-height-card :deep(.el-card__body) {
  max-height: 980px;
  overflow: auto;
}

.event-timeline {
  padding-left: 6px;
}

.timeline-card {
  border: 1px solid #ebeef5;
}

.timeline-card__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.timeline-card__title {
  color: #303133;
  font-weight: 600;
  line-height: 1.5;
}

.timeline-card__subtitle {
  margin-top: 4px;
  color: #909399;
  font-size: 12px;
}

.timeline-card__meta {
  margin-top: 12px;
  color: #606266;
  line-height: 1.6;
}

.trade-memory-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.subsection-title {
  margin: 16px 0 12px;
  color: #303133;
  font-weight: 600;
}

.section-gap {
  margin-top: 16px;
}

.json-block {
  margin-top: 12px;
  padding: 12px;
  overflow: auto;
  border-radius: 10px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.json-block--large {
  max-height: 520px;
}
</style>
