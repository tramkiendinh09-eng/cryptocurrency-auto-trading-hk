<template>
  <div class="app-container">
    <el-row :gutter="12" class="mb12">
      <el-col :xs="24" :sm="8">
        <el-card shadow="never">
          <div class="stat-label">最近7天成功率</div>
          <div class="stat-value">{{ notifyStats.successRate ?? 100 }}%</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="never">
          <div class="stat-label">今日发送</div>
          <div class="stat-value">{{ notifyStats.todayCount ?? 0 }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="never">
          <div class="stat-label">本周失败</div>
          <div class="stat-value">{{ notifyStats.weekFailed ?? 0 }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-form ref="queryFormRef" :model="queryParams" :inline="true">
      <el-form-item label="类型" prop="channelType">
        <el-select v-model="queryParams.channelType" clearable placeholder="所有类型" style="width: 160px">
          <el-option label="Email" value="email" />
          <el-option label="Telegram" value="telegram" />
          <el-option label="DingTalk" value="dingtalk" />
          <el-option label="Feishu" value="feishu" />
          <el-option label="Webhook" value="webhook" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-select v-model="queryParams.status" clearable placeholder="所有状态" style="width: 160px">
          <el-option label="待处理" :value="0" />
          <el-option label="发送中" :value="1" />
          <el-option label="成功" :value="2" />
          <el-option label="失败" :value="3" />
        </el-select>
      </el-form-item>
      <el-form-item label="标题" prop="title">
        <el-input v-model="queryParams.title" clearable placeholder="标题" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="追踪ID" prop="traceId">
        <el-input v-model="queryParams.traceId" clearable placeholder="trace-..." @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="接收人" prop="recipient">
        <el-input v-model="queryParams.recipient" clearable placeholder="ops@example.com / chat id" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="日期范围">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
          value-format="YYYY-MM-DD"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button type="danger" icon="Delete" :disabled="multiple" v-hasPermi="['dca:notify:remove']" @click="handleDelete">删除</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="success" icon="Refresh" @click="handleResendFailed">重试失败</el-button>
      </el-col>
    </el-row>

    <el-table v-loading="loading" :data="recordList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column prop="channelName" label="渠道" min-width="160" show-overflow-tooltip />
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="traceId" label="追踪ID" min-width="180" show-overflow-tooltip />
      <el-table-column prop="recipient" label="接收人" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagMap[row.status] || 'info'">{{ statusLabelMap[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="retryCount" label="重试" width="90" />
      <el-table-column prop="sendTime" label="发送时间" width="180">
        <template #default="{ row }">
          {{ parseTime(row.sendTime) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleView(row)">详情</el-button>
          <el-button v-if="row.status === 3" link type="success" @click="handleResend(row)">重试</el-button>
          <el-button link type="danger" v-hasPermi="['dca:notify:remove']" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <pagination
      v-show="total > 0"
      :total="total"
      v-model:page="queryParams.pageNum"
      v-model:limit="queryParams.pageSize"
      @pagination="loadRecords"
    />

    <el-dialog v-model="detailOpen" title="通知详情" width="820px" append-to-body>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="渠道">{{ recordDetail.channelName }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ recordDetail.channelType }}</el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">{{ recordDetail.title }}</el-descriptions-item>
        <el-descriptions-item label="追踪ID" :span="2">{{ recordDetail.traceId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="接收人">{{ recordDetail.recipient }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusLabelMap[recordDetail.status] || recordDetail.status }}</el-descriptions-item>
        <el-descriptions-item label="重试">{{ recordDetail.retryCount }}</el-descriptions-item>
        <el-descriptions-item label="发送时间">{{ parseTime(recordDetail.sendTime) }}</el-descriptions-item>
      </el-descriptions>
      <el-divider>内容</el-divider>
      <div class="detail-block"><pre>{{ recordDetail.content }}</pre></div>
      <template v-if="recordDetail.errorMsg">
        <el-divider>错误</el-divider>
        <el-alert :title="recordDetail.errorMsg" type="error" :closable="false" />
      </template>
      <template v-if="recordDetail.templateVars">
        <el-divider>模板变量</el-divider>
        <div class="detail-block"><pre>{{ formatJson(recordDetail.templateVars) }}</pre></div>
      </template>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="detailOpen = false">关闭</el-button>
          <el-button v-if="recordDetail.status === 3" type="primary" @click="handleResend(recordDetail)">重试</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
/**
 * 通知记录页面工具函数模块
 * 提供记录查询构建等辅助函数
 */

function text(value) {
  return String(value ?? '').trim()
}

export function createRecordQuery(query = {}) {
  return {
    pageNum: Number(query.pageNum ?? 1),
    pageSize: Number(query.pageSize ?? 10),
    channelType: text(query.channelType) || undefined,
    status: query.status ?? undefined,
    title: text(query.title) || undefined,
    traceId: text(query.traceId) || undefined,
    recipient: text(query.recipient) || undefined
  }
}
</script>

<script setup>
import { getCurrentInstance, reactive, ref, toRefs } from 'vue'

import { getNotifyRecord, getNotifyStats, listNotifyRecord, resendNotify } from '@/api/dca/notify'

const { proxy } = getCurrentInstance()

const loading = ref(false)
const detailOpen = ref(false)
const total = ref(0)
const ids = ref([])
const multiple = ref(true)
const dateRange = ref([])
const recordList = ref([])
const recordDetail = ref({})
const notifyStats = ref({})
const queryFormRef = ref()

const statusLabelMap = {
  0: 'Pending',
  1: 'Sending',
  2: 'Success',
  3: 'Failed'
}

const statusTagMap = {
  0: 'info',
  1: 'warning',
  2: 'success',
  3: 'danger'
}

const data = reactive({
  queryParams: createRecordQuery()
})

const { queryParams } = toRefs(data)

async function loadStats() {
  const response = await getNotifyStats()
  notifyStats.value = response?.data || {}
}

async function loadRecords() {
  loading.value = true
  try {
    const params = proxy.addDateRange(createRecordQuery(queryParams.value), dateRange.value)
    const response = await listNotifyRecord(params)
    recordList.value = response?.rows || []
    total.value = response?.total || 0
  } finally {
    loading.value = false
  }
}

async function handleQuery() {
  queryParams.value.pageNum = 1
  await loadRecords()
}

async function resetQuery() {
  queryFormRef.value?.resetFields()
  dateRange.value = []
  Object.assign(queryParams.value, createRecordQuery())
  await loadRecords()
}

function handleSelectionChange(selection) {
  ids.value = selection.map((item) => item.id)
  multiple.value = !selection.length
}

async function handleView(row) {
  const response = await getNotifyRecord(row.id)
  recordDetail.value = response?.data || {}
  detailOpen.value = true
}

async function handleResend(row) {
  await resendNotify(row.id)
  proxy?.$modal?.msgSuccess?.('Notification requeued')
  detailOpen.value = false
  await Promise.all([loadRecords(), loadStats()])
}

async function handleResendFailed() {
  const failedIds = recordList.value.filter((item) => item.status === 3).map((item) => item.id)
  if (!failedIds.length) {
    proxy?.$modal?.msgWarning?.('No failed records in current page')
    return
  }
  await Promise.all(failedIds.map((id) => resendNotify(id)))
  proxy?.$modal?.msgSuccess?.('Failed records requeued')
  await Promise.all([loadRecords(), loadStats()])
}

async function handleDelete(row) {
  const deleteIds = row?.id ? row.id : ids.value
  await proxy?.$modal?.confirm?.(`Delete notification record ${deleteIds}?`)
  await proxy.request({
    url: `/dca/notify/records/${deleteIds}`,
    method: 'delete'
  })
  proxy?.$modal?.msgSuccess?.('Notification record deleted')
  await Promise.all([loadRecords(), loadStats()])
}

function formatJson(value) {
  try {
    const parsed = typeof value === 'string' ? JSON.parse(value) : value
    return JSON.stringify(parsed, null, 2)
  } catch {
    return value
  }
}

Promise.all([loadRecords(), loadStats()])
</script>

<style scoped>
.mb12 {
  margin-bottom: 12px;
}

.stat-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  text-transform: uppercase;
}

.stat-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 700;
}

.detail-block {
  max-height: 280px;
  overflow: auto;
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
}

.detail-block pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
