<template>
  <div class="app-container replay-console">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>历史回放控制台</span>
          <div class="card-header__actions">
            <el-tag type="warning">影子 / 回放</el-tag>
            <el-button type="primary" link @click="loadReplaySessions">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table :data="replaySessions" v-loading="loading">
        <el-table-column prop="createdAt" label="创建时间" min-width="168" />
        <el-table-column prop="sessionName" label="会话" min-width="180" show-overflow-tooltip />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="replayStatusTag(scope.row.status)">
              {{ formatReplayStatus(scope.row.status || 'queued') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="symbol" label="交易对" width="120" />
        <el-table-column prop="exchangeCode" label="交易所" width="120" />
        <el-table-column label="模式" width="120">
          <template #default="scope">
            {{ formatRuntimeMode(scope.row.mode) }}
          </template>
        </el-table-column>
        <el-table-column prop="sourceTraceId" label="源追踪ID" min-width="180" show-overflow-tooltip />
        <el-table-column prop="replayTraceId" label="回放追踪ID" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" min-width="220" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="openCompare(scope.row)">对比</el-button>
            <el-button link type="primary" @click="openEvents(scope.row)">事件</el-button>
            <el-button
              link
              type="primary"
              :disabled="!scope.row.sourceTraceId"
              @click="openSource(scope.row)"
            >
              原始数据
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <pagination
        v-show="total > 0"
        :total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="loadReplaySessions"
      />
    </el-card>

    <el-drawer v-model="compareDrawerOpen" title="回放对比" size="42%">
      <div v-loading="compareLoading" class="drawer-body">
        <el-empty v-if="!compareLoading && !replayComparison.sessionId" description="未加载回放对比" />
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

          <el-row :gutter="16" class="compare-grid">
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
                  <el-descriptions-item label="摘要">{{ replayComparison.replayDecision?.summaryReason || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="订单引用">{{ replayComparison.replayOrder?.orderRef || '-' }}</el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>
          </el-row>
        </template>
      </div>
    </el-drawer>

    <el-drawer v-model="eventsDrawerOpen" title="回放事件" size="40%">
      <div v-loading="eventsLoading" class="drawer-body">
        <el-table :data="replayEvents" size="small" empty-text="无回放事件">
          <el-table-column prop="createdAt" label="时间" min-width="160" />
          <el-table-column label="类型" width="140">
            <template #default="scope">
              {{ formatEventType(scope.row.eventType) }}
            </template>
          </el-table-column>
          <el-table-column prop="traceId" label="追踪ID" min-width="180" show-overflow-tooltip />
          <el-table-column prop="payloadJson" label="负载" min-width="220" show-overflow-tooltip />
        </el-table>
      </div>
    </el-drawer>

    <el-drawer v-model="sourceDrawerOpen" title="回放源数据" size="40%">
      <div v-loading="sourceLoading" class="drawer-body">
        <el-empty v-if="!sourceLoading && !replaySource.traceId" description="未加载回放源数据" />
        <template v-else>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="追踪ID">{{ replaySource.traceId || '-' }}</el-descriptions-item>
            <el-descriptions-item label="模式">{{ formatRuntimeMode(replaySource.mode) }}</el-descriptions-item>
            <el-descriptions-item label="交易对">{{ replaySource.symbol || '-' }}</el-descriptions-item>
            <el-descriptions-item label="交易所">{{ replaySource.exchangeCode || '-' }}</el-descriptions-item>
            <el-descriptions-item label="事件数量">{{ replaySource.eventBundle?.length || 0 }}</el-descriptions-item>
          </el-descriptions>
          <pre class="source-payload">{{ formatSourcePayload(replaySource.eventBundle) }}</pre>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script>
/**
 * 历史回放控制台工具函数模块
 * 提供回放会话数据提取、状态格式化等辅助函数
 */

import { formatTradeLabel } from '@/utils/tradeLabels'

/**
 * 从API响应中提取回放会话行数据
 * @param {Object} response - API响应对象
 * @returns {Array} 回放会话数组
 */
export function extractReplaySessionRows(response) {
  if (Array.isArray(response?.data)) {
    return response.data
  }
  if (Array.isArray(response?.rows)) {
    return response.rows
  }
  return []
}

/**
 * 从API响应中提取回放事件行数据
 * @param {Object} response - API响应对象
 * @returns {Array} 回放事件数组
 */
export function extractReplayEventRows(response) {
  if (Array.isArray(response?.data)) {
    return response.data
  }
  if (Array.isArray(response?.rows)) {
    return response.rows
  }
  return []
}

/**
 * 获取回放状态对应的标签类型
 * @param {string} status - 回放状态值
 * @returns {string} Element Plus标签类型
 */
export function replayStatusTag(status) {
  const normalized = String(status || '').trim().toLowerCase()
  if (normalized === 'running') {
    return 'warning'
  }
  if (normalized === 'completed') {
    return 'success'
  }
  if (normalized === 'failed') {
    return 'danger'
  }
  return 'info'
}

/**
 * 格式化决策模型显示文本
 * @param {Object} row - 决策记录对象
 * @returns {string} 格式化后的模型显示文本
 */
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

/**
 * 格式化回放状态显示文本
 * @param {string} value - 回放状态值
 * @returns {string} 格式化后的显示文本
 */
export function formatReplayStatus(value) {
  return formatTradeLabel('replayStatus', value) || '-'
}

/**
 * 格式化运行模式显示文本
 * @param {string} value - 运行模式值
 * @returns {string} 格式化后的显示文本
 */
export function formatRuntimeMode(value) {
  return formatTradeLabel('runtimeMode', value) || '-'
}

/**
 * 格式化操作类型显示文本
 * @param {string} value - 操作类型值
 * @returns {string} 格式化后的显示文本
 */
export function formatAction(value) {
  return formatTradeLabel('action', value) || '-'
}

/**
 * 格式化执行状态显示文本
 * @param {string} value - 执行状态值
 * @returns {string} 格式化后的显示文本
 */
export function formatExecutionStatus(value) {
  return formatTradeLabel('executionStatus', value) || '-'
}

/**
 * 格式化订单状态显示文本
 * @param {string} value - 订单状态值
 * @returns {string} 格式化后的显示文本
 */
export function formatOrderStatus(value) {
  return formatTradeLabel('orderStatus', value) || '-'
}

/**
 * 格式化事件类型显示文本
 * @param {string} value - 事件类型值
 * @returns {string} 格式化后的显示文本
 */
export function formatEventType(value) {
  return formatTradeLabel('eventType', value) || '-'
}
</script>

<script setup>
/**
 * 历史回放控制台组合式API
 * 提供回放会话列表加载、对比查看、事件查看等功能
 */

import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import {
  getReplayComparison,
  getReplaySource,
  listReplayEvents,
  listReplaySessions
} from '@/api/dca/replay'

/** 加载状态 */
const loading = ref(false)
/** 回放会话列表数据 */
const replaySessions = ref([])
/** 总记录数 */
const total = ref(0)
/** 查询参数 */
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10
})

/** 对比加载状态 */
const compareLoading = ref(false)
/** 对比抽屉显示状态 */
const compareDrawerOpen = ref(false)
/** 回放对比数据 */
const replayComparison = ref({})

/** 事件加载状态 */
const eventsLoading = ref(false)
/** 事件抽屉显示状态 */
const eventsDrawerOpen = ref(false)
/** 回放事件列表 */
const replayEvents = ref([])

/** 源数据加载状态 */
const sourceLoading = ref(false)
/** 源数据抽屉显示状态 */
const sourceDrawerOpen = ref(false)
/** 回放源数据 */
const replaySource = ref({})

/**
 * 加载回放会话列表
 * 从API获取回放会话数据
 */
async function loadReplaySessions() {
  loading.value = true
  try {
    const response = await listReplaySessions({ ...queryParams })
    replaySessions.value = extractReplaySessionRows(response)
    total.value = response?.total || replaySessions.value.length
  } catch (error) {
    replaySessions.value = []
    ElMessage.error('加载回放会话失败')
  } finally {
    loading.value = false
  }
}

/**
 * 打开回放对比抽屉
 * @param {Object} session - 回放会话对象
 */
async function openCompare(session) {
  compareLoading.value = true
  compareDrawerOpen.value = true
  try {
    const response = await getReplayComparison(session.id)
    replayComparison.value = response?.data || {}
  } catch (error) {
    replayComparison.value = {}
    ElMessage.error('加载回放对比失败')
  } finally {
    compareLoading.value = false
  }
}

/**
 * 打开回放事件抽屉
 * @param {Object} session - 回放会话对象
 */
async function openEvents(session) {
  eventsLoading.value = true
  eventsDrawerOpen.value = true
  try {
    const response = await listReplayEvents(session.id)
    replayEvents.value = extractReplayEventRows(response)
  } catch (error) {
    replayEvents.value = []
    ElMessage.error('加载回放事件失败')
  } finally {
    eventsLoading.value = false
  }
}

/**
 * 打开回放源数据抽屉
 * @param {Object} session - 回放会话对象
 */
async function openSource(session) {
  if (!session?.sourceTraceId) {
    ElMessage.warning('当前回放会话缺少源追踪ID')
    return
  }
  sourceLoading.value = true
  sourceDrawerOpen.value = true
  try {
    const response = await getReplaySource(session.sourceTraceId)
    replaySource.value = response?.data || {}
  } catch (error) {
    replaySource.value = {}
    ElMessage.error('加载回放源数据失败')
  } finally {
    sourceLoading.value = false
  }
}

/**
 * 格式化源数据负载为JSON字符串
 * @param {Array} eventBundle - 事件包数组
 * @returns {string} 格式化后的JSON字符串
 */
function formatSourcePayload(eventBundle) {
  try {
    return JSON.stringify(eventBundle || [], null, 2)
  } catch (error) {
    return '[]'
  }
}

// 组件挂载时加载回放会话列表
onMounted(() => {
  loadReplaySessions()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-header__actions {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.drawer-body {
  min-height: 240px;
}

.compare-grid {
  margin-top: 16px;
}

.source-payload {
  margin-top: 16px;
  max-height: 420px;
  padding: 12px;
  overflow: auto;
  border-radius: 12px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.5;
}
</style>
