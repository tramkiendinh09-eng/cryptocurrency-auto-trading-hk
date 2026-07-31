<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>数据源绑定</span>
          <div class="card-header__actions">
            <el-button type="primary" v-hasPermi="['dca:tradeSourceBinding:add']" @click="handleAdd">添加绑定</el-button>
            <el-button plain @click="getList">刷新</el-button>
          </div>
        </div>
      </template>

      <div class="toolbar">
        <el-select v-model="queryParams.strategyId" clearable filterable placeholder="策略" style="width: 220px" @change="handleQuery">
          <el-option v-for="item in strategyOptions" :key="item.id" :label="item.strategyName || item.strategyKey" :value="item.id" />
        </el-select>
        <el-select v-model="queryParams.sourceId" clearable filterable placeholder="数据源" style="width: 240px" @change="handleQuery">
          <el-option v-for="item in sourceOptions" :key="item.id" :label="item.configName" :value="item.id" />
        </el-select>
        <el-select v-model="queryParams.eventType" clearable placeholder="事件" style="width: 180px" @change="handleQuery">
          <el-option v-for="item in eventTypeOptions" :key="item" :label="formatTradeLabel('eventType', item)" :value="item" />
        </el-select>
        <el-select v-model="queryParams.enabled" clearable placeholder="状态" style="width: 160px" @change="handleQuery">
          <el-option label="启用" :value="true" />
          <el-option label="禁用" :value="false" />
        </el-select>
      </div>

      <el-table v-loading="loading" :data="bindingList" empty-text="无数据源绑定">
        <el-table-column prop="bindingName" label="绑定名称" min-width="180" />
        <el-table-column label="策略" min-width="180">
          <template #default="scope">
            {{ resolveStrategyName(scope.row.strategyId) }}
          </template>
        </el-table-column>
        <el-table-column label="数据源" min-width="220">
          <template #default="scope">
            {{ resolveSourceName(scope.row.sourceId) }}
          </template>
        </el-table-column>
        <el-table-column label="事件" width="140">
          <template #default="scope">
            {{ formatTradeLabel('eventType', scope.row.eventType) }}
          </template>
        </el-table-column>
        <el-table-column label="交易对" min-width="180">
          <template #default="scope">
            <el-space wrap>
              <el-tag v-for="item in parseJsonArray(scope.row.symbolScopeJson)" :key="item" effect="plain">{{ item }}</el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="交易所" min-width="160">
          <template #default="scope">
            <el-space wrap>
              <el-tag v-for="item in parseJsonArray(scope.row.exchangeScopeJson)" :key="item" type="success" effect="plain">{{ item }}</el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="模式" min-width="160">
          <template #default="scope">
            <el-space wrap>
              <el-tag v-for="item in parseJsonArray(scope.row.modeScopeJson)" :key="item" type="warning" effect="plain">
                {{ formatTradeLabel('runtimeMode', item) }}
              </el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.enabled ? 'success' : 'info'">{{ scope.row.enabled ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button link type="primary" v-hasPermi="['dca:tradeSourceBinding:edit']" @click="handleUpdate(scope.row)">修改</el-button>
            <el-button link type="danger" v-hasPermi="['dca:tradeSourceBinding:remove']" @click="handleDelete(scope.row)">删除</el-button>
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
            <div class="detail-card__header">绑定详情</div>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="策略">{{ previewStrategyName }}</el-descriptions-item>
            <el-descriptions-item label="事件类型">{{ formatTradeLabel('eventType', previewBinding?.eventType) || '--' }}</el-descriptions-item>
            <el-descriptions-item label="交易对范围">{{ parseJsonArray(previewBinding?.symbolScopeJson).join(', ') || '--' }}</el-descriptions-item>
            <el-descriptions-item label="交易所范围">{{ parseJsonArray(previewBinding?.exchangeScopeJson).join(', ') || '--' }}</el-descriptions-item>
            <el-descriptions-item label="运行模式">{{ formatTradeLabels('runtimeMode', parseJsonArray(previewBinding?.modeScopeJson)).join(', ') || '--' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        <el-card shadow="never" class="detail-card detail-card--wide">
          <template #header>
            <div class="detail-card__header">数据源详情</div>
          </template>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="配置名称">{{ previewSource?.configName || '--' }}</el-descriptions-item>
            <el-descriptions-item label="数据分类">{{ formatTradeLabel('dataCategory', previewSource?.dataCategory) || previewSource?.dataCategory || '--' }}</el-descriptions-item>
            <el-descriptions-item label="数据子类型">{{ previewSource?.dataSubType || '--' }}</el-descriptions-item>
            <el-descriptions-item label="接入方式">{{ formatTradeLabel('transportType', previewSource?.transportType) || previewSource?.transportType || '--' }}</el-descriptions-item>
            <el-descriptions-item label="REST 地址">{{ previewSource?.apiUrl || '--' }}</el-descriptions-item>
            <el-descriptions-item label="响应路径">{{ previewSource?.responsePath || '--' }}</el-descriptions-item>
            <el-descriptions-item label="WS 地址">{{ previewSource?.wsBaseUrl || '--' }}</el-descriptions-item>
            <el-descriptions-item label="WS 订阅模板">{{ previewSource?.wsStreamNameTemplate || '--' }}</el-descriptions-item>
          </el-descriptions>
          <pre class="preview-content">{{ previewSourceFieldMapping }}</pre>
        </el-card>
      </div>
    </el-card>

    <el-dialog v-model="open" :title="title" width="760px" append-to-body>
      <el-form ref="bindingRef" :model="form" :rules="rules" label-width="140px">
        <TradeFormSection title="基础信息" description="先确定这条绑定归属哪个策略、绑定到哪个数据源，以及它负责的事件类型。">
          <el-form-item label="绑定名称" prop="bindingName">
            <el-input v-model="form.bindingName" placeholder="主要新闻源" />
          </el-form-item>
          <el-form-item label="策略">
            <el-select v-model="form.strategyId" clearable filterable placeholder="允许不绑定策略的全局绑定" style="width: 100%">
              <el-option v-for="item in strategyOptions" :key="item.id" :label="item.strategyName || item.strategyKey" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="数据源" prop="sourceId">
            <el-select v-model="form.sourceId" filterable placeholder="选择数据源" style="width: 100%">
              <el-option
                v-for="item in sourceOptions"
                :key="item.id"
                :label="`${item.configName}（${formatTradeLabel('dataCategory', item.dataCategory) || item.dataCategory || '未分类'}）${item.enabled === '1' ? '' : ' [禁用]'}`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="事件类型" prop="eventType">
            <el-select v-model="form.eventType" filterable placeholder="选择事件类型" style="width: 100%">
              <el-option
                v-for="item in eventTypeOptions"
                :key="item"
                :label="formatTradeLabel('eventType', item)"
                :value="item"
              />
            </el-select>
          </el-form-item>
        </TradeFormSection>

        <TradeFormSection title="生效范围" description="再限定这条绑定对哪些交易对、交易所和运行模式生效。">
          <el-form-item label="交易对" prop="symbols">
            <el-select v-model="form.symbols" multiple placeholder="选择 V1 交易对" style="width: 100%">
              <el-option v-for="item in sourceBindingSymbolOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="交易所" prop="exchanges">
            <el-select v-model="form.exchanges" multiple placeholder="选择交易所" style="width: 100%">
              <el-option v-for="item in sourceBindingExchangeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="运行模式" prop="runtimeModes">
            <el-select v-model="form.runtimeModes" multiple placeholder="选择运行模式" style="width: 100%">
              <el-option
                v-for="item in sourceBindingRuntimeModeOptions"
                :key="item"
                :label="formatTradeLabel('runtimeMode', item)"
                :value="item"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.enabled" />
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
function trimValue(value) {
  return String(value || '').trim()
}

export const sourceBindingSymbolOptions = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
export const sourceBindingExchangeOptions = ['BINANCE', 'OKX']
export const sourceBindingRuntimeModeOptions = ['paper', 'shadow', 'live']

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

export function createTradeSourceBindingForm(binding = {}) {
  return {
    id: binding.id,
    bindingName: String(binding.bindingName || ''),
    strategyId: binding.strategyId ?? null,
    sourceId: binding.sourceId ?? null,
    eventType: trimValue(binding.eventType || '').toLowerCase(),
    symbols: parseJsonArray(binding.symbolScopeJson).map((item) => item.toUpperCase()),
    exchanges: parseJsonArray(binding.exchangeScopeJson).map((item) => item.toUpperCase()),
    runtimeModes: parseJsonArray(binding.modeScopeJson).map((item) => item.toLowerCase()),
    enabled: binding.enabled !== false
  }
}

export function buildTradeSourceBindingPayload(form = {}) {
  return {
    id: form.id,
    bindingName: trimValue(form.bindingName),
    strategyId: form.strategyId ?? null,
    sourceId: form.sourceId ?? null,
    eventType: trimValue(form.eventType).toLowerCase(),
    symbolScopeJson: JSON.stringify(normalizeArray(form.symbols, (item) => item.toUpperCase())),
    exchangeScopeJson: JSON.stringify(normalizeArray(form.exchanges, (item) => item.toUpperCase())),
    modeScopeJson: JSON.stringify(normalizeArray(form.runtimeModes, (item) => item.toLowerCase())),
    enabled: Boolean(form.enabled)
  }
}

export function validateTradeSourceBindingPayload(form = {}) {
  const payload = buildTradeSourceBindingPayload(form)
  if (!payload.bindingName) {
    throw new Error('绑定名称不能为空')
  }
  if (!payload.sourceId) {
    throw new Error('数据源不能为空')
  }
  if (!payload.eventType) {
    throw new Error('事件类型不能为空')
  }
  const symbols = parseJsonArray(payload.symbolScopeJson)
  const exchanges = parseJsonArray(payload.exchangeScopeJson)
  const runtimeModes = parseJsonArray(payload.modeScopeJson)
  if (!symbols.length) {
    throw new Error('请至少选择一个交易对')
  }
  if (!exchanges.length) {
    throw new Error('请至少选择一个交易所')
  }
  if (!runtimeModes.length) {
    throw new Error('请至少选择一个运行模式')
  }
  const unsupportedSymbol = symbols.find((item) => !sourceBindingSymbolOptions.includes(item))
  if (unsupportedSymbol) {
    throw new Error(`不支持的 V1 交易对: ${unsupportedSymbol}`)
  }
  const unsupportedExchange = exchanges.find((item) => !sourceBindingExchangeOptions.includes(item))
  if (unsupportedExchange) {
    throw new Error(`不支持的 V1 交易所: ${unsupportedExchange}`)
  }
  const unsupportedMode = runtimeModes.find((item) => !sourceBindingRuntimeModeOptions.includes(item))
  if (unsupportedMode) {
    throw new Error(`不支持的运行模式: ${unsupportedMode}`)
  }
  return payload
}
function findSourceById(options, sourceId) {
  if (sourceId == null || sourceId === '') {
    return null
  }
  return (Array.isArray(options) ? options : []).find((item) => Number(item?.id) === Number(sourceId)) || null
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
</script>

<script setup>
import { computed, getCurrentInstance, reactive, ref } from 'vue'

import TradeFormSection from '@/components/trade/TradeFormSection.vue'
import { listApi } from '@/api/dca/market'
import { addTradeSourceBinding, delTradeSourceBinding, listTradeSourceBinding, updateTradeSourceBinding } from '@/api/dca/tradeSourceBinding'
import { listTradeStrategy } from '@/api/dca/tradeStrategy'
import { formatTradeLabel, formatTradeLabels } from '@/utils/tradeLabels'

const { proxy } = getCurrentInstance()

const eventTypeOptions = ['market_tick', 'news', 'onchain', 'social', 'liquidation', 'announcement']

const loading = ref(false)
const submitting = ref(false)
const open = ref(false)
const title = ref('添加数据源绑定')
const bindingRef = ref()
const bindingList = ref([])
const total = ref(0)
const strategyOptions = ref([])
const sourceOptions = ref([])
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  strategyId: null,
  sourceId: null,
  eventType: '',
  enabled: ''
})
const form = reactive(createTradeSourceBindingForm({
  symbols: sourceBindingSymbolOptions,
  exchanges: sourceBindingExchangeOptions,
  runtimeModes: sourceBindingRuntimeModeOptions,
  enabled: true
}))
const rules = {
  bindingName: [{ required: true, message: '绑定名称不能为空', trigger: 'blur' }],
  sourceId: [{ required: true, message: '请选择数据源', trigger: 'change' }],
  eventType: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  symbols: [{ required: true, message: '请至少选择一个交易对', trigger: 'change' }],
  exchanges: [{ required: true, message: '请至少选择一个交易所', trigger: 'change' }],
  runtimeModes: [{ required: true, message: '请至少选择一个模式', trigger: 'change' }]
}
const strategyMap = computed(() => new Map(strategyOptions.value.map((item) => [item.id, item])))
const sourceMap = computed(() => new Map(sourceOptions.value.map((item) => [item.id, item])))
const previewBinding = computed(() => (open.value ? form : (bindingList.value[0] || null)))
const previewSource = computed(() => findSourceById(sourceOptions.value, previewBinding.value?.sourceId))
const previewStrategyName = computed(() => resolveStrategyName(previewBinding.value?.strategyId))
const previewSourceFieldMapping = computed(() => prettyJson(previewSource.value?.fieldMappingJson))

function resetForm(binding = {}) {
  Object.assign(form, createTradeSourceBindingForm({
    symbols: sourceBindingSymbolOptions,
    exchanges: sourceBindingExchangeOptions,
    runtimeModes: sourceBindingRuntimeModeOptions,
    enabled: true,
    ...binding
  }))
  bindingRef.value?.clearValidate()
}

function resolveStrategyName(strategyId) {
  if (!strategyId) {
    return '全局'
  }
  const strategy = strategyMap.value.get(strategyId)
  return strategy?.strategyName || strategy?.strategyKey || `#${strategyId}`
}

function resolveSourceName(sourceId) {
  const source = sourceMap.value.get(sourceId)
  return source?.configName || `#${sourceId}`
}

async function loadOptions() {
  const [strategyResponse, sourceResponse] = await Promise.all([
    listTradeStrategy({ pageNum: 1, pageSize: 200 }),
    listApi({ pageNum: 1, pageSize: 200 })
  ])
  strategyOptions.value = strategyResponse?.rows || []
  sourceOptions.value = sourceResponse?.rows || []
}

function handleQuery() {
  queryParams.pageNum = 1
  getList()
}

async function getList() {
  loading.value = true
  try {
    const response = await listTradeSourceBinding({
      ...queryParams
    })
    bindingList.value = response?.rows || []
    total.value = response?.total || bindingList.value.length
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  resetForm()
  title.value = '添加数据源绑定'
  open.value = true
}

function handleUpdate(row) {
  resetForm(row)
  title.value = '修改数据源绑定'
  open.value = true
}

async function submitForm() {
  await bindingRef.value?.validate()
  submitting.value = true
  try {
    const payload = validateTradeSourceBindingPayload(form)
    if (payload.id) {
      await updateTradeSourceBinding(payload)
      proxy?.$modal?.msgSuccess?.('数据源绑定已更新')
    } else {
      await addTradeSourceBinding(payload)
      proxy?.$modal?.msgSuccess?.('数据源绑定已新增')
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
    await proxy?.$modal?.confirm?.(`确认删除数据源绑定“${row.bindingName}”吗？`)
    await delTradeSourceBinding(row.id)
    proxy?.$modal?.msgSuccess?.('数据源绑定已删除')
    await getList()
  } catch (error) {
    // ignore when cancelled
  }
}

Promise.all([loadOptions(), getList()])
function findSourceById(options, sourceId) {
  if (sourceId == null || sourceId === '') {
    return null
  }
  return (Array.isArray(options) ? options : []).find((item) => Number(item?.id) === Number(sourceId)) || null
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
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.6fr);
  gap: 16px;
  margin-top: 16px;
}
.detail-card {
  min-width: 0;
}
.detail-card__header {
  font-weight: 600;
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
