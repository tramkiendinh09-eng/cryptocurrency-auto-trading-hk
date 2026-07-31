<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>通知策略</span>
          <div class="card-header__actions">
            <el-button type="primary" v-hasPermi="['dca:tradeNotifyPolicy:add']" @click="handleAdd">添加策略</el-button>
            <el-button plain @click="getList">刷新</el-button>
          </div>
        </div>
      </template>

      <div class="toolbar">
        <el-select v-model="queryParams.policyScope" clearable placeholder="范围" style="width: 180px" @change="handleQuery">
          <el-option label="全局" value="GLOBAL" />
          <el-option label="策略" value="STRATEGY" />
        </el-select>
        <el-select v-model="queryParams.strategyId" clearable filterable placeholder="策略" style="width: 220px" @change="handleQuery">
          <el-option v-for="item in strategyOptions" :key="item.id" :label="item.strategyName || item.strategyKey" :value="item.id" />
        </el-select>
        <el-select v-model="queryParams.enabled" clearable placeholder="状态" style="width: 160px" @change="handleQuery">
          <el-option label="启用" :value="true" />
          <el-option label="禁用" :value="false" />
        </el-select>
      </div>

      <el-table
        v-loading="loading"
        :data="policyList"
        row-key="id"
        highlight-current-row
        empty-text="无通知策略"
        @current-change="handleCurrentChange"
      >
        <el-table-column prop="policyName" label="策略名称" min-width="180" />
        <el-table-column label="范围" width="140">
          <template #default="scope">
            <el-tag :type="scope.row.policyScope === 'STRATEGY' ? 'warning' : 'info'">
              {{ formatTradeLabel('policyScope', scope.row.policyScope) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="策略" min-width="180">
          <template #default="scope">
            {{ resolveStrategyName(scope.row.strategyId) }}
          </template>
        </el-table-column>
        <el-table-column label="事件" min-width="180">
          <template #default="scope">
            <el-space wrap>
              <el-tag v-for="item in parseJsonArray(scope.row.eventScopeJson)" :key="item" effect="plain">
                {{ formatTradeLabel('eventType', item) }}
              </el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="严重程度" min-width="180">
          <template #default="scope">
            <el-space wrap>
              <el-tag v-for="item in parseJsonArray(scope.row.severityScopeJson)" :key="item" type="danger" effect="plain">
                {{ formatTradeLabel('severity', item) }}
              </el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="模式" min-width="180">
          <template #default="scope">
            <el-space wrap>
              <el-tag v-for="item in parseJsonArray(scope.row.modeScopeJson)" :key="item" type="success" effect="plain">
                {{ formatTradeLabel('runtimeMode', item) }}
              </el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="通知渠道" min-width="220">
          <template #default="scope">
            {{ formatChannelNames(scope.row.channelBindings) }}
          </template>
        </el-table-column>
        <el-table-column prop="throttleSeconds" label="限速(秒)" width="120" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.enabled ? 'success' : 'info'">{{ scope.row.enabled ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button link type="primary" v-hasPermi="['dca:tradeNotifyPolicy:edit']" @click="handleUpdate(scope.row)">修改</el-button>
            <el-button link type="danger" v-hasPermi="['dca:tradeNotifyPolicy:remove']" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
            </el-table>
      <pagination
        v-show="total > 0"
        :total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="getList"
      />
      <div class="detail-grid">
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">策略详情</div>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="范围">{{ formatTradeLabel('policyScope', previewPolicy?.policyScope) || '--' }}</el-descriptions-item>
            <el-descriptions-item label="策略">{{ previewStrategyName }}</el-descriptions-item>
            <el-descriptions-item label="模板">{{ previewPolicy?.notifyTemplateCode || previewPolicy?.templateCode || '--' }}</el-descriptions-item>
            <el-descriptions-item label="事件">{{ formatTradeLabels('eventType', parseJsonArray(previewPolicy?.eventScopeJson)).join(', ') || '--' }}</el-descriptions-item>
            <el-descriptions-item label="严重程度">{{ formatTradeLabels('severity', parseJsonArray(previewPolicy?.severityScopeJson)).join(', ') || '--' }}</el-descriptions-item>
            <el-descriptions-item label="模式">{{ formatTradeLabels('runtimeMode', parseJsonArray(previewPolicy?.modeScopeJson)).join(', ') || '--' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">渠道详情</div>
          </template>
          <div class="preview-tags">
            <el-tag v-for="item in previewChannelList" :key="item.id" size="small" effect="plain">
              {{ item.channelName }} / {{ item.channelType }} / {{ item.isEnabled === 1 ? '启用' : '禁用' }}
            </el-tag>
          </div>
          <pre class="preview-content">{{ previewChannelSummary }}</pre>
        </el-card>
        <el-card shadow="never" class="detail-card detail-card--wide">
          <template #header>
            <div class="detail-card__header">模板预览</div>
          </template>
          <div class="preview-meta">
            <span>{{ previewTemplate?.code || previewPolicy?.notifyTemplateCode || previewPolicy?.templateCode || '--' }}</span>
            <span v-if="previewTemplate?.version">v{{ previewTemplate.version }}</span>
          </div>
          <div class="preview-tags">
            <el-tag v-for="item in previewTemplateVariables" :key="item" size="small" type="warning" effect="plain">
              {{ item }}
            </el-tag>
          </div>
          <pre class="preview-content">{{ previewTemplateContent }}</pre>
        </el-card>
      </div>
    </el-card>

    <el-dialog v-model="open" :title="title" width="760px" append-to-body>
      <el-form ref="policyRef" :model="form" :rules="rules" label-width="140px">
        <TradeFormSection title="策略基础" description="先确定通知策略的名称、适用范围，以及它是否是全局策略还是策略专属策略。">
          <el-form-item label="策略名称" prop="policyName">
            <el-input v-model="form.policyName" placeholder="运行时风险升级" />
          </el-form-item>
          <el-form-item label="范围" prop="policyScope">
            <el-radio-group v-model="form.policyScope">
              <el-radio label="global">全局</el-radio>
              <el-radio label="strategy">策略</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.policyScope === 'strategy'" label="策略" prop="strategyId">
            <el-select v-model="form.strategyId" filterable clearable placeholder="选择策略" style="width: 100%">
              <el-option v-for="item in strategyOptions" :key="item.id" :label="item.strategyName || item.strategyKey" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.enabled" />
          </el-form-item>
        </TradeFormSection>

        <TradeFormSection title="触发范围" description="这里决定哪些事件、严重级别和运行模式会命中这条通知策略。">
          <el-form-item label="事件范围" prop="eventScopes">
            <el-select v-model="form.eventScopes" multiple filterable placeholder="选择事件" style="width: 100%">
              <el-option
                v-for="item in eventScopeOptions"
                :key="item"
                :label="formatTradeLabel('eventType', item)"
                :value="item"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="严重程度范围" prop="severityScopes">
            <el-select v-model="form.severityScopes" multiple placeholder="选择严重程度" style="width: 100%">
              <el-option
                v-for="item in severityScopeOptions"
                :key="item"
                :label="formatTradeLabel('severity', item)"
                :value="item"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="运行模式" prop="modeScopes">
            <el-select v-model="form.modeScopes" multiple placeholder="选择模式" style="width: 100%">
              <el-option
                v-for="item in modeScopeOptions"
                :key="item"
                :label="formatTradeLabel('runtimeMode', item)"
                :value="item"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="限速秒数" prop="throttleSeconds">
            <el-input-number v-model="form.throttleSeconds" :min="0" :max="86400" :step="30" style="width: 100%" />
          </el-form-item>
        </TradeFormSection>

        <TradeFormSection title="投递配置" description="最后指定要发往哪些通知渠道，并绑定使用哪一个通知模板。">
          <el-form-item label="通知渠道" prop="selectedChannelIds">
            <el-select
              v-model="form.selectedChannelIds"
              multiple
              filterable
              :loading="channelLoading"
              placeholder="选择渠道"
              style="width: 100%"
            >
              <el-option
                v-for="item in channelOptions"
                :key="item.id"
                :label="`${item.channelName} (${item.channelType})${item.isEnabled === 1 ? '' : ' [禁用]'}`"
                :value="item.id"
              />
            </el-select>
            <div v-if="!channelLoading && !channelOptions.length" class="inline-hint">
              当前没有可用通知渠道，请先新增或启用通知渠道。
            </div>
          </el-form-item>
          <el-form-item label="模板编码" prop="notifyTemplateCode">
            <el-select
              v-model="form.notifyTemplateCode"
              clearable
              filterable
              allow-create
              default-first-option
              placeholder="notify.runtime.risk.v1"
              style="width: 100%"
            >
              <el-option v-for="item in templateOptions" :key="item.id || item.code" :label="item.code" :value="item.code" />
            </el-select>
          </el-form-item>
        </TradeFormSection>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="open = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
/**
 * 通知策略页面工具函数模块
 * 提供通知策略表单创建、数据转换等辅助函数
 */

function trimValue(value) {
  return String(value || '').trim()
}

function extractRows(response) {
  if (Array.isArray(response)) {
    return response
  }
  if (Array.isArray(response?.rows)) {
    return response.rows
  }
  if (Array.isArray(response?.data)) {
    return response.data
  }
  return []
}

export function parseJsonArray(value) {
  if (!value) {
    return []
  }
  if (Array.isArray(value)) {
    return value.map((item) => trimValue(item)).filter(Boolean)
  }
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed.map((item) => trimValue(item)).filter(Boolean) : []
  } catch {
    return []
  }
}

function normalizeArray(values, transform = (item) => item) {
  return Array.from(
    new Set((Array.isArray(values) ? values : []).map((item) => transform(trimValue(item))).filter(Boolean))
  )
}

export function createTradeNotifyPolicyForm(policy = {}) {
  return {
    id: policy.id,
    policyName: String(policy.policyName || ''),
    policyScope: trimValue(policy.policyScope || 'GLOBAL').toLowerCase(),
    strategyId: policy.strategyId ?? null,
    eventScopes: parseJsonArray(policy.eventScopeJson).map((item) => item.toLowerCase()),
    severityScopes: parseJsonArray(policy.severityScopeJson).map((item) => item.toUpperCase()),
    modeScopes: parseJsonArray(policy.modeScopeJson).map((item) => item.toLowerCase()),
    throttleSeconds: Number(policy.throttleSeconds ?? 0),
    notifyTemplateCode: String(policy.notifyTemplateCode || policy.templateCode || ''),
    enabled: policy.enabled !== false,
    selectedChannelIds: (Array.isArray(policy.channelBindings) ? policy.channelBindings : [])
      .map((item) => item?.channelId)
      .filter(Boolean)
  }
}

export function buildTradeNotifyPolicyPayload(form = {}) {
  const selectedChannelIds = normalizeArray(form.selectedChannelIds, (item) => Number(item)).filter((item) => Number.isFinite(item))
  return {
    id: form.id,
    policyName: trimValue(form.policyName),
    policyScope: trimValue(form.policyScope || 'global').toUpperCase(),
    strategyId: trimValue(form.policyScope || 'global').toLowerCase() === 'strategy' ? form.strategyId ?? null : null,
    eventScopeJson: JSON.stringify(normalizeArray(form.eventScopes, (item) => item.toLowerCase())),
    severityScopeJson: JSON.stringify(normalizeArray(form.severityScopes, (item) => item.toUpperCase())),
    modeScopeJson: JSON.stringify(normalizeArray(form.modeScopes, (item) => item.toLowerCase())),
    throttleSeconds: Number(form.throttleSeconds ?? 0),
    notifyTemplateCode: trimValue(form.notifyTemplateCode || form.templateCode),
    enabled: Boolean(form.enabled),
    channelBindings: selectedChannelIds.map((channelId, index) => ({
      channelId,
      channelOrder: index + 1,
      enabled: true
    }))
  }
}

export function validateTradeNotifyPolicyPayload(form = {}) {
  const payload = buildTradeNotifyPolicyPayload(form)
  if (!payload.policyName) {
    throw new Error('策略名称不能为空')
  }
  if (payload.policyScope === 'STRATEGY' && !payload.strategyId) {
    throw new Error('策略范围必须绑定策略')
  }
  if (!parseJsonArray(payload.eventScopeJson).length) {
    throw new Error('请至少选择一个事件')
  }
  if (!parseJsonArray(payload.severityScopeJson).length) {
    throw new Error('请至少选择一个严重程度')
  }
  if (!parseJsonArray(payload.modeScopeJson).length) {
    throw new Error('请至少选择一个运行模式')
  }
  if (!Array.isArray(payload.channelBindings) || !payload.channelBindings.length) {
    throw new Error('请至少选择一个通知渠道')
  }
  if (!payload.notifyTemplateCode) {
    throw new Error('通知模板不能为空')
  }
  return payload
}
function findTemplateByCode(options, code) {
  const normalized = trimValue(code)
  if (!normalized) {
    return null
  }
  return (Array.isArray(options) ? options : []).find((item) => trimValue(item?.code) === normalized) || null
}
function findChannelsByIds(options, ids) {
  const selected = new Set(Array.isArray(ids) ? ids.map((item) => Number(item)) : [])
  return (Array.isArray(options) ? options : []).filter((item) => selected.has(Number(item?.id)))
}
function prettyJson(value) {
  if (!value) {
    return '--'
  }
  if (typeof value === 'string') {
    try {
      return JSON.stringify(JSON.parse(value), null, 2)
    } catch {
      return value
    }
  }
  return JSON.stringify(value, null, 2)
}

function normalizeChannelOptions(response) {
  return extractRows(response)
    .map((item) => ({
      ...item,
      id: Number(item?.id),
      isEnabled: Number(item?.isEnabled ?? item?.enabled ?? 1)
    }))
    .filter((item) => Number.isFinite(item.id))
}
</script>

<script setup>
import { computed, getCurrentInstance, reactive, ref } from 'vue'

import TradeFormSection from '@/components/trade/TradeFormSection.vue'
import { listChannel, listEnabledChannel } from '@/api/dca/notify'
import { listTradeNotifyTemplate } from '@/api/dca/tradeNotifyTemplate'
import { addTradeNotifyPolicy, delTradeNotifyPolicy, listTradeNotifyPolicy, updateTradeNotifyPolicy } from '@/api/dca/tradeNotifyPolicy'
import { listTradeStrategy } from '@/api/dca/tradeStrategy'
import { formatTradeLabel, formatTradeLabels } from '@/utils/tradeLabels'

const { proxy } = getCurrentInstance()

const eventScopeOptions = ['decision', 'risk_guard_hit', 'execution', 'position', 'market_source_abnormal', 'runtime']
const severityScopeOptions = ['INFO', 'WARN', 'ERROR', 'CRITICAL']
const modeScopeOptions = ['paper', 'shadow', 'live']

const loading = ref(false)
const submitting = ref(false)
const open = ref(false)
const channelLoading = ref(false)
const title = ref('添加通知策略')
const policyRef = ref()
const policyList = ref([])
const total = ref(0)
const currentPolicyId = ref(null)
const strategyOptions = ref([])
const channelOptions = ref([])
const templateOptions = ref([])
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  policyScope: '',
  strategyId: null,
  enabled: ''
})
const form = reactive(createTradeNotifyPolicyForm())
const rules = {
  policyName: [{ required: true, message: '策略名称不能为空', trigger: 'blur' }],
  eventScopes: [{ required: true, message: '请至少选择一个事件', trigger: 'change' }],
  severityScopes: [{ required: true, message: '请至少选择一个严重程度', trigger: 'change' }],
  modeScopes: [{ required: true, message: '请至少选择一个运行模式', trigger: 'change' }],
  selectedChannelIds: [{ required: true, message: '请至少选择一个通知渠道', trigger: 'change' }]
}
const strategyMap = computed(() => new Map(strategyOptions.value.map((item) => [item.id, item])))
const channelMap = computed(() => new Map(channelOptions.value.map((item) => [item.id, item])))
const selectedPolicy = computed(() => policyList.value.find((item) => item.id === currentPolicyId.value) || null)
const previewPolicy = computed(() => (open.value ? form : (selectedPolicy.value || policyList.value[0] || null)))
const previewStrategyName = computed(() => resolveStrategyName(previewPolicy.value?.strategyId))
const previewChannelList = computed(() => findChannelsByIds(channelOptions.value, previewPolicy.value?.selectedChannelIds || previewPolicy.value?.channelBindings?.map((item) => item.channelId)))
const previewChannelSummary = computed(() => prettyJson(previewChannelList.value.map((item) => ({
  channelName: item.channelName,
  channelType: item.channelType,
  webhookUrl: item.webhookUrl,
  recipient: item.recipient,
  enabled: item.isEnabled
}))))
const previewTemplate = computed(() => findTemplateByCode(
  templateOptions.value,
  previewPolicy.value?.notifyTemplateCode || previewPolicy.value?.templateCode
))
const previewTemplateVariables = computed(() => parseJsonArray(previewTemplate.value?.variables))
const previewTemplateContent = computed(() => {
  if (!previewTemplate.value) {
    return '--'
  }
  const fragments = [previewTemplate.value.titleTemplate, previewTemplate.value.contentTemplate]
    .map((item) => trimValue(item))
    .filter(Boolean)
  return fragments.join('\n\n') || '--'
})

function resetForm(policy = {}) {
  Object.assign(form, createTradeNotifyPolicyForm(policy))
  policyRef.value?.clearValidate()
}

function handleCurrentChange(row) {
  currentPolicyId.value = row?.id ?? null
}

function resolveStrategyName(strategyId) {
  if (!strategyId) {
    return '全局'
  }
  const strategy = strategyMap.value.get(strategyId)
  return strategy?.strategyName || strategy?.strategyKey || `#${strategyId}`
}

function formatChannelNames(channelBindings = []) {
  const names = (Array.isArray(channelBindings) ? channelBindings : [])
    .map((item) => channelMap.value.get(item.channelId)?.channelName || `#${item.channelId}`)
  return names.join(', ') || '-'
}

async function loadOptions() {
  channelLoading.value = true
  try {
    const [strategyResult, channelResult, templateResult] = await Promise.allSettled([
      listTradeStrategy({ pageNum: 1, pageSize: 200 }),
      listChannel({ pageNum: 1, pageSize: 200 }),
      listTradeNotifyTemplate({ pageNum: 1, pageSize: 200 })
    ])

    if (strategyResult.status === 'fulfilled') {
      strategyOptions.value = extractRows(strategyResult.value)
    }

    let nextChannels = []
    if (channelResult.status === 'fulfilled') {
      nextChannels = normalizeChannelOptions(channelResult.value)
    }
    if (!nextChannels.length) {
      try {
        nextChannels = normalizeChannelOptions(await listEnabledChannel())
      } catch {
        nextChannels = nextChannels || []
      }
    }
    channelOptions.value = nextChannels

    if (templateResult.status === 'fulfilled') {
      templateOptions.value = extractRows(templateResult.value).filter((item) => Number(item.isActive ?? 1) === 1)
    }
  } finally {
    channelLoading.value = false
  }
}

function handleQuery() {
  queryParams.pageNum = 1
  getList()
}

async function getList() {
  loading.value = true
  try {
    const response = await listTradeNotifyPolicy({
      ...queryParams
    })
    policyList.value = response?.rows || []
    total.value = response?.total || policyList.value.length
    const stillExists = policyList.value.some((item) => item.id === currentPolicyId.value)
    currentPolicyId.value = stillExists ? currentPolicyId.value : (policyList.value[0]?.id ?? null)
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  await loadOptions()
  resetForm()
  title.value = '添加通知策略'
  open.value = true
}

async function handleUpdate(row) {
  await loadOptions()
  resetForm(row)
  title.value = '修改通知策略'
  open.value = true
}

async function submitForm() {
  await policyRef.value?.validate()
  submitting.value = true
  try {
    const payload = validateTradeNotifyPolicyPayload(form)
    if (payload.id) {
      await updateTradeNotifyPolicy(payload)
      proxy?.$modal?.msgSuccess?.('通知策略已更新')
    } else {
      await addTradeNotifyPolicy(payload)
      proxy?.$modal?.msgSuccess?.('通知策略已新增')
    }
    open.value = false
    await getList()
  } catch (error) {
    if (error?.message) {
      proxy?.$modal?.msgError?.(error.message)
    }
    throw error
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await proxy?.$modal?.confirm?.(`确认删除通知策略“${row.policyName}”吗？`)
    await delTradeNotifyPolicy(row.id)
    proxy?.$modal?.msgSuccess?.('通知策略已删除')
    await getList()
  } catch (error) {
    // ignore when cancelled
  }
}

Promise.all([loadOptions(), getList()])
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-header__actions,
.toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar {
  margin-bottom: 16px;
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 16px;
}
.detail-card {
  min-width: 0;
}
.detail-card--wide {
  grid-column: span 1;
}
.detail-card__header {
  font-weight: 600;
}
.preview-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.preview-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.preview-content {
  margin: 12px 0 0;
  padding: 12px;
  min-height: 120px;
  border-radius: 10px;
  background: #f8fafc;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: auto;
}

.inline-hint {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
