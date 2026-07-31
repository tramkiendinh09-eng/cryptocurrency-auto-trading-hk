<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>决策审计</span>
          <el-tag type="info">纸面 / 影子 / 实盘</el-tag>
        </div>
      </template>
      <el-form :model="queryParams" :inline="true" class="query-form">
        <el-form-item label="执行状态">
          <el-select v-model="queryParams.executionStatus" clearable placeholder="全部" style="width: 160px">
            <el-option
              v-for="item in executionStatusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="订单状态">
          <el-select v-model="queryParams.orderStatus" clearable placeholder="全部" style="width: 180px">
            <el-option
              v-for="item in orderStatusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="decisionRuns" v-loading="loading">
        <el-table-column prop="traceId" label="追踪ID" min-width="180" />
        <el-table-column prop="symbol" label="交易对" width="120" />
        <el-table-column label="模式" width="120">
          <template #default="scope">
            {{ formatRuntimeMode(scope.row.mode) }}
          </template>
        </el-table-column>
        <el-table-column label="事件强度" width="120">
          <template #default="scope">
            <el-tag :type="eventStrengthTag(resolveEventStrength(scope.row))">
              {{ formatEventStrength(resolveEventStrength(scope.row)) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="scope">
            {{ formatAction(scope.row.action) }}
          </template>
        </el-table-column>
        <el-table-column label="执行状态" width="120">
          <template #default="scope">
            <el-tag :type="executionStatusTag(scope.row.executionStatus)">
              {{ formatExecutionStatus(scope.row.executionStatus || 'pending') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="订单状态" width="120">
          <template #default="scope">
            <el-tag :type="orderStatusTag(scope.row.orderStatus)">
              {{ formatOrderStatus(scope.row.orderStatus || 'PENDING') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="120" />
        <el-table-column label="模型" min-width="180" show-overflow-tooltip>
          <template #default="scope">
            {{ formatDecisionModel(scope.row) }}
          </template>
        </el-table-column>
        <el-table-column label="提示词" min-width="220" show-overflow-tooltip>
          <template #default="scope">
            {{ formatPromptAuditSummary(scope.row) }}
          </template>
        </el-table-column>
        <el-table-column label="市场来源" min-width="220" show-overflow-tooltip>
          <template #default="scope">
            {{ formatMarketSourceSummary(scope.row) }}
          </template>
        </el-table-column>
        <el-table-column label="交易记忆" min-width="260" show-overflow-tooltip>
          <template #default="scope">
            <div class="trade-memory-cell">
              <el-tag
                v-if="resolveTradeMemoryStatus(scope.row) !== '-'"
                size="small"
                :type="tradeMemoryStatusTag(resolveTradeMemoryStatus(scope.row))"
              >
                {{ resolveTradeMemoryStatus(scope.row) }}
              </el-tag>
              <span>{{ formatTradeMemoryOutcome(scope.row) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="summaryReason" label="摘要" min-width="220" show-overflow-tooltip />
        <el-table-column label="对话记录" width="140">
          <template #default="scope">
            <el-button
              link
              type="primary"
              :disabled="!(scope.row.agentMessages || []).length"
              @click="handleViewTranscript(scope.row)"
            >
              {{ (scope.row.agentMessages || []).length ? '查看记录' : '无记录' }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="回放" width="160" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="handleReplayAction(scope.row)">
              {{ replaySessionMap[scope.row.traceId] ? '查看回放' : '影子回放' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <pagination
        v-show="total > 0"
        :total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="loadDecisionRuns"
      />
    </el-card>

    <el-drawer v-model="replayDrawerOpen" title="回放对比" size="42%">
      <div v-loading="replayLoading" class="replay-drawer">
        <el-empty v-if="!replayLoading && !replayComparison.sessionId" description="未加载回放对比" />
        <template v-else>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="会话ID">{{ replayComparison.sessionId }}</el-descriptions-item>
            <el-descriptions-item label="源追踪ID">{{ replayComparison.sourceTraceId || '-' }}</el-descriptions-item>
            <el-descriptions-item label="回放追踪ID">{{ replayComparison.replayTraceId || '-' }}</el-descriptions-item>
            <el-descriptions-item label="操作匹配">
              <el-tag :type="replayComparison.actionMatched ? 'success' : 'warning'">
                {{ replayComparison.actionMatched ? '匹配' : '变更' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="执行差异">
              <el-tag :type="replayComparison.executionStatusChanged ? 'warning' : 'success'">
                {{ replayComparison.executionStatusChanged ? '变更' : '稳定' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="订单差异">
              <el-tag :type="replayComparison.orderStatusChanged ? 'warning' : 'success'">
                {{ replayComparison.orderStatusChanged ? '变更' : '稳定' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <el-row :gutter="16" class="replay-compare-grid">
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span>原始</span>
                </template>
                <el-descriptions :column="1" size="small">
                  <el-descriptions-item label="操作">{{ formatAction(replayComparison.originalDecision?.action) }}</el-descriptions-item>
                  <el-descriptions-item label="执行">{{ formatExecutionStatus(replayComparison.originalDecision?.executionStatus) }}</el-descriptions-item>
                  <el-descriptions-item label="订单">{{ formatOrderStatus(replayComparison.originalDecision?.orderStatus) }}</el-descriptions-item>
                  <el-descriptions-item label="模型">{{ formatDecisionModel(replayComparison.originalDecision) }}</el-descriptions-item>
                  <el-descriptions-item label="提示词">{{ formatPromptAuditSummary(replayComparison.originalDecision) }}</el-descriptions-item>
                  <el-descriptions-item label="风险">{{ buildReplayRiskSummary(replayComparison.originalRiskHits) }}</el-descriptions-item>
                  <el-descriptions-item label="摘要">{{ replayComparison.originalDecision?.summaryReason || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="订单引用">{{ replayComparison.originalOrder?.orderRef || '-' }}</el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span>回放</span>
                </template>
                <el-descriptions :column="1" size="small">
                  <el-descriptions-item label="操作">{{ formatAction(replayComparison.replayDecision?.action) }}</el-descriptions-item>
                  <el-descriptions-item label="执行">{{ formatExecutionStatus(replayComparison.replayDecision?.executionStatus) }}</el-descriptions-item>
                  <el-descriptions-item label="订单">{{ formatOrderStatus(replayComparison.replayDecision?.orderStatus) }}</el-descriptions-item>
                  <el-descriptions-item label="模型">{{ formatDecisionModel(replayComparison.replayDecision) }}</el-descriptions-item>
                  <el-descriptions-item label="提示词">{{ formatPromptAuditSummary(replayComparison.replayDecision) }}</el-descriptions-item>
                  <el-descriptions-item label="风险">{{ buildReplayRiskSummary(replayComparison.replayRiskHits) }}</el-descriptions-item>
                  <el-descriptions-item label="摘要">{{ replayComparison.replayDecision?.summaryReason || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="订单引用">{{ replayComparison.replayOrder?.orderRef || '-' }}</el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>
          </el-row>
        </template>
      </div>
    </el-drawer>

    <el-drawer v-model="transcriptDrawerOpen" title="代理对话记录" size="46%">
      <div class="replay-drawer">
        <el-empty v-if="!selectedDecision.traceId" description="未选择对话记录" />
        <template v-else>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="追踪ID">{{ selectedDecision.traceId }}</el-descriptions-item>
              <el-descriptions-item label="交易对">{{ selectedDecision.symbol || '-' }}</el-descriptions-item>
              <el-descriptions-item label="操作">{{ formatAction(selectedDecision.action) }}</el-descriptions-item>
              <el-descriptions-item label="模型">{{ formatDecisionModel(selectedDecision) }}</el-descriptions-item>
              <el-descriptions-item label="提示词">{{ formatPromptAuditSummary(selectedDecision) }}</el-descriptions-item>
            </el-descriptions>

          <el-table
            :data="buildTranscriptRows(selectedDecision)"
            class="transcript-table"
            empty-text="无对话记录"
          >
            <el-table-column prop="roundNo" label="轮次" width="80" />
            <el-table-column prop="speakerAgent" label="发言方" min-width="140" />
            <el-table-column prop="targetAgent" label="目标方" min-width="140" />
            <el-table-column label="类型" width="120">
              <template #default="scope">
                {{ formatMessageType(scope.row.messageType) }}
              </template>
            </el-table-column>
            <el-table-column prop="templateCode" label="模板" min-width="160" show-overflow-tooltip />
            <el-table-column prop="modelCode" label="模型" min-width="140" show-overflow-tooltip />
            <el-table-column prop="summaryText" label="摘要" min-width="220" show-overflow-tooltip />
            <el-table-column prop="contentPreview" label="内容" min-width="220" show-overflow-tooltip />
          </el-table>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script>
/**
 * 决策审计页面工具函数模块
 * 提供决策查询构建、格式化等辅助函数
 */

import { formatTradeLabel } from '@/utils/tradeLabels'

export { executionStatusTag, orderStatusTag } from '@/utils/tradeExecutionStatus'

/**
 * 构建决策查询参数
 * @param {Object} filters - 过滤条件
 * @returns {Object} 查询参数对象
 */
export function buildDecisionQuery(filters = {}) {
  const query = {}
  if (filters.pageNum) {
    query.pageNum = filters.pageNum
  }
  if (filters.pageSize) {
    query.pageSize = filters.pageSize
  }
  if (filters.executionStatus) {
    query.executionStatus = filters.executionStatus
  }
  if (filters.orderStatus) {
    query.orderStatus = filters.orderStatus
  }
  return query
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

export function formatDecisionPromptSource(value) {
  const normalized = String(value || '').trim().toLowerCase()
  if (!normalized) {
    return ''
  }
  if (normalized === 'deliberation_referee') {
    return '会审裁判采纳'
  }
  return formatTradeLabel('promptSource', value) || String(value || '').trim()
}

export function formatPromptAuditSummary(row = {}) {
  const resolvedTemplateCode = String(row?.resolvedTemplateCode || '').trim()
  const bindingTemplateCode = String(row?.bindingTemplateCode || '').trim()
  const promptSource = String(row?.promptSource || '').trim()
  const promptTemplateFallbackUsed = Boolean(row?.promptTemplateFallbackUsed)
  const templateCode = resolvedTemplateCode || bindingTemplateCode
  const parts = [templateCode, formatDecisionPromptSource(promptSource)].filter(Boolean)
  if (promptTemplateFallbackUsed) {
    parts.push('回退')
  }
  return parts.length ? parts.join(' / ') : '-'
}

export function resolveEventStrength(row = {}) {
  return String(row?.eventStrength || row?.featureSnapshot?.eventStrength || '').trim() || '-'
}

export function eventStrengthTag(strength) {
  switch (String(strength || '').trim().toLowerCase()) {
    case 'strong':
      return 'danger'
    case 'normal':
      return 'warning'
    case 'noise':
      return 'info'
    default:
      return 'info'
  }
}

export function extractMarketSourceConfig(row = {}) {
  const direct = row?.marketSourceConfig
  if (direct && typeof direct === 'object') {
    return direct
  }
  const nested = row?.featureSnapshot?.snapshot?.marketSourceConfig
  if (nested && typeof nested === 'object') {
    return nested
  }
  return {}
}

export function formatMarketSourceSummary(row = {}) {
  const config = extractMarketSourceConfig(row)
  const vendorCode = String(config?.vendorCode || config?.vendor_code || '').trim()
  const transportType = String(config?.transportType || config?.transport_type || '').trim()
  const updateTime = String(config?.updateTime || config?.updated_at || '').trim()
  const updateLabel = updateTime ? `\u914d\u7f6e\u66f4\u65b0: ${updateTime}` : ''
  const parts = [vendorCode, formatTradeLabel('transportType', transportType) || transportType, updateLabel].filter(Boolean)
  return parts.length ? parts.join(' / ') : '-'
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

export function formatTradeMemoryOutcome(row = {}) {
  const tradeMemoryStatus = extractTradeMemoryStatus(row)
  const lifecycleStatus = extractLifecycleStatus(row)
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
  const status = resolveTradeMemoryStatus(row)
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

export function buildLatestReplaySessionMap(sessions = []) {
  return sessions.reduce((accumulator, session) => {
    if (!session?.sourceTraceId) {
      return accumulator
    }
    const current = accumulator[session.sourceTraceId]
    if (!current || Number(session.id || 0) > Number(current.id || 0)) {
      accumulator[session.sourceTraceId] = session
    }
    return accumulator
  }, {})
}

export function resolveReplayActionLabel(row = {}, replaySessions = {}) {
  return replaySessions[row.traceId] ? '查看回放' : '影子回放'
}

export function buildReplayRiskSummary(riskHits = []) {
  if (!Array.isArray(riskHits) || !riskHits.length) {
    return '-'
  }
  const ruleCodes = riskHits
    .map((item) => String(item?.ruleCode || '').trim())
    .filter(Boolean)
  if (!ruleCodes.length) {
    return '-'
  }
  return `${riskHits.length} 次 / ${ruleCodes.join(' / ')}`
}

export function parseAgentMessageContent(contentJson) {
  if (!contentJson) {
    return {}
  }
  try {
    const parsed = typeof contentJson === 'string' ? JSON.parse(contentJson) : contentJson
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

export function formatAgentMessagePreview(message = {}) {
  const parsed = parseAgentMessageContent(message.contentJson)
  const detailParts = ['bias', 'stance', 'decision', 'action', 'confidence', 'reason', 'risk_note', 'template_code', 'model_code']
    .map((key) => {
      if (parsed[key] == null || !String(parsed[key]).trim()) {
        return ''
      }
      return `${key}: ${String(parsed[key]).trim()}`
    })
    .filter(Boolean)
  if (message.summaryText) {
    const summaryText = String(message.summaryText).trim()
    if (!detailParts.length) {
      return summaryText
    }
    const detailText = detailParts.join(' / ')
    return detailText.length > summaryText.length ? `${summaryText} / ${detailText}` : summaryText
  }
  if (detailParts.length) {
    return detailParts.join(' / ')
  }
  const serialized = JSON.stringify(parsed)
  return serialized === '{}' ? '-' : serialized
}

export function buildTranscriptRows(row = {}) {
  const messages = Array.isArray(row?.agentMessages) ? row.agentMessages : []
  return messages.map((message) => {
    const parsed = parseAgentMessageContent(message.contentJson)
    return {
      ...message,
      roundNo: message.roundNo ?? 0,
      speakerAgent: message.speakerAgent || '-',
      targetAgent: message.targetAgent || '-',
      messageType: message.messageType || '-',
      templateCode: message.templateCode || parsed.template_code || parsed.templateCode || '-',
      modelCode: message.modelCode || parsed.model_code || parsed.modelCode || '-',
      summaryText: message.summaryText || '-',
      contentPreview: formatAgentMessagePreview(message)
    }
  })
}

export function formatRuntimeMode(value) {
  return formatTradeLabel('runtimeMode', value) || '-'
}

export function formatEventStrength(value) {
  return formatTradeLabel('eventStrength', value) || '-'
}

export function formatAction(value) {
  return formatTradeLabel('action', value) || '-'
}

export function formatExecutionStatus(value) {
  return formatTradeLabel('executionStatus', value) || '-'
}

export function formatOrderStatus(value) {
  return formatTradeLabel('orderStatus', value) || '-'
}

export function formatMessageType(value) {
  const text = String(value || '').trim()
  if (!text) {
    return '-'
  }
  const messageTypeMap = {
    proposal: '提议',
    challenge: '质疑',
    critique: '复核',
    conclusion: '结论',
    referee_review: '复核',
    final_decision: '最终裁决',
    revision: '修正',
    response: '响应',
    request: '请求',
    summary: '总结',
    system: '系统'
  }
  return messageTypeMap[text.toLowerCase()] || text
}
</script>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { listDecisionRuns } from '@/api/dca/decisionAudit'
import { dispatchReplay, getReplayComparison, listReplaySessions } from '@/api/dca/replay'
import { executionStatusTag, orderStatusTag } from '@/utils/tradeExecutionStatus'

const loading = ref(false)
const decisionRuns = ref([])
const total = ref(0)
const replayLoading = ref(false)
const replayDrawerOpen = ref(false)
const transcriptDrawerOpen = ref(false)
const replayComparison = ref({})
const replaySessionMap = ref({})
const selectedDecision = ref({})
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  executionStatus: '',
  orderStatus: ''
})
const executionStatusOptions = [
  { label: '已成交', value: 'filled' },
  { label: '待执行', value: 'pending' },
  { label: '部分成交', value: 'partial' },
  { label: '已取消', value: 'canceled' },
  { label: '已过期', value: 'expired' },
  { label: '执行失败', value: 'failed' },
  { label: '已拦截', value: 'blocked' },
  { label: '已跳过', value: 'skipped' }
]
const orderStatusOptions = [
  { label: '已成交', value: 'FILLED' },
  { label: '待处理', value: 'PENDING' },
  { label: '部分成交', value: 'PARTIALLY_FILLED' },
  { label: '已取消', value: 'CANCELED' },
  { label: '已过期', value: 'EXPIRED' },
  { label: '已拒绝', value: 'REJECTED' },
  { label: '已拦截', value: 'BLOCKED' },
  { label: '已跳过', value: 'SKIPPED' }
]

async function loadDecisionRuns() {
  loading.value = true
  try {
    const response = await listDecisionRuns(buildDecisionQuery(queryParams))
    decisionRuns.value = response?.rows || response?.data || []
    total.value = response?.total || decisionRuns.value.length
  } catch (error) {
    decisionRuns.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function loadReplaySessions() {
  try {
    const response = await listReplaySessions()
    replaySessionMap.value = buildLatestReplaySessionMap(response?.data || [])
  } catch (error) {
    replaySessionMap.value = {}
  }
}

function storeReplaySession(session) {
  if (!session?.sourceTraceId) {
    return
  }
  replaySessionMap.value = {
    ...replaySessionMap.value,
    [session.sourceTraceId]: session
  }
}

function handleQuery() {
  queryParams.pageNum = 1
  loadDecisionRuns()
}

function resetQuery() {
  queryParams.pageNum = 1
  queryParams.executionStatus = ''
  queryParams.orderStatus = ''
  loadDecisionRuns()
}

async function openReplayCompare(row) {
  const session = replaySessionMap.value[row?.traceId]
  if (!session?.id) {
    ElMessage.warning('当前追踪ID还没有回放会话')
    return
  }
  replayLoading.value = true
  replayDrawerOpen.value = true
  try {
    const response = await getReplayComparison(session.id)
    replayComparison.value = response?.data || {}
  } catch (error) {
    replayComparison.value = {}
    ElMessage.error('加载回放对比失败')
  } finally {
    replayLoading.value = false
  }
}

async function handleReplayAction(row) {
  if (!row?.traceId) {
    ElMessage.warning('缺少追踪ID，无法发起回放')
    return
  }
  const session = replaySessionMap.value[row?.traceId]
  if (session?.id) {
    await openReplayCompare(row)
    return
  }
  try {
    const response = await dispatchReplay(row?.traceId)
    const replaySession = response?.data
    if (replaySession?.id) {
      storeReplaySession(replaySession)
    } else {
      await loadReplaySessions()
    }
    ElMessage.success('已加入影子回放队列')
  } catch (error) {
    ElMessage.error('发起回放失败')
  }
}

function handleViewTranscript(row) {
  selectedDecision.value = row || {}
  transcriptDrawerOpen.value = true
}

onMounted(() => {
  loadDecisionRuns()
  loadReplaySessions()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.query-form {
  margin-bottom: 16px;
}

.replay-drawer {
  height: 100%;
  overflow-y: auto;
}

.replay-compare-grid {
  margin-top: 16px;
}

.transcript-table {
  margin-top: 16px;
}

.trade-memory-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
