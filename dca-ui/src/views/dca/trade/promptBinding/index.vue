<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>提示词绑定</span>
          <div class="card-header__actions">
            <el-button type="primary" v-hasPermi="['dca:tradePromptBinding:add']" @click="handleAdd">添加绑定</el-button>
            <el-button plain v-hasPermi="['dca:template:list']" @click="openPromptTemplateConsole">管理提示词模板</el-button>
            <el-button plain @click="getList">刷新</el-button>
          </div>
        </div>
      </template>

      <div class="toolbar">
        <el-select v-model="queryParams.strategyId" clearable filterable placeholder="策略" style="width: 220px" @change="handleQuery">
          <el-option v-for="item in strategyOptions" :key="item.id" :label="item.strategyName || item.strategyKey" :value="item.id" />
        </el-select>
        <el-select v-model="queryParams.bindingScope" clearable placeholder="绑定范围" style="width: 220px" @change="handleQuery">
          <el-option v-for="item in promptBindingScopeOptions" :key="item" :label="formatTradeLabel('promptScope', item)" :value="item" />
        </el-select>
        <el-select v-model="queryParams.enabled" clearable placeholder="状态" style="width: 160px" @change="handleQuery">
          <el-option label="启用" :value="true" />
          <el-option label="禁用" :value="false" />
        </el-select>
      </div>

      <el-table v-loading="loading" :data="bindingList" empty-text="无提示词绑定">
        <el-table-column prop="bindingName" label="绑定名称" min-width="180" />
        <el-table-column label="策略" min-width="180">
          <template #default="scope">
            {{ resolveStrategyName(scope.row.strategyId) }}
          </template>
        </el-table-column>
        <el-table-column label="版本" min-width="120">
          <template #default="scope">
            {{ scope.row.strategyVersionId ? `#${scope.row.strategyVersionId}` : '最新' }}
          </template>
        </el-table-column>
        <el-table-column label="范围" width="180">
          <template #default="scope">
            {{ formatTradeLabel('promptScope', scope.row.bindingScope) }}
          </template>
        </el-table-column>
        <el-table-column prop="templateCode" label="模板" min-width="180" show-overflow-tooltip />
        <el-table-column label="输出模式" min-width="180">
          <template #default="scope">
            {{ formatTradeLabel('outputSchema', scope.row.outputSchemaCode) || scope.row.outputSchemaCode }}
          </template>
        </el-table-column>
        <el-table-column label="模式" min-width="180">
          <template #default="scope">
            <el-space wrap>
              <el-tag v-for="item in parseJsonArray(scope.row.modeScopeJson)" :key="item" type="warning" effect="plain">
                {{ formatTradeLabel('runtimeMode', item) }}
              </el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="事件强度" min-width="180">
          <template #default="scope">
            <el-space wrap>
              <el-tag v-for="item in parseJsonArray(scope.row.eventStrengthScopeJson)" :key="item" type="danger" effect="plain">
                {{ formatTradeLabel('eventStrength', item) }}
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
            <el-button link type="primary" v-hasPermi="['dca:tradePromptBinding:edit']" @click="handleUpdate(scope.row)">修改</el-button>
            <el-button link type="danger" v-hasPermi="['dca:tradePromptBinding:remove']" @click="handleDelete(scope.row)">删除</el-button>
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
            <el-descriptions-item label="绑定范围">{{ formatTradeLabel('promptScope', previewBinding?.bindingScope) || '--' }}</el-descriptions-item>
            <el-descriptions-item label="策略版本">
              {{ previewBinding?.strategyVersionId ? '#' + previewBinding.strategyVersionId : '最新' }}
            </el-descriptions-item>
            <el-descriptions-item label="输出模式">
              {{ formatTradeLabel('outputSchema', previewBinding?.outputSchemaCode) || previewBinding?.outputSchemaCode || '--' }}
            </el-descriptions-item>
            <el-descriptions-item label="运行模式">
              {{ formatTradeLabels('runtimeMode', parseJsonArray(previewBinding?.modeScopeJson)).join(', ') || '--' }}
            </el-descriptions-item>
            <el-descriptions-item label="事件强度">
              {{ formatTradeLabels('eventStrength', parseJsonArray(previewBinding?.eventStrengthScopeJson)).join(', ') || '--' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">模板预览</div>
          </template>
          <div class="preview-meta">
            <span>{{ activeTemplate?.code || previewBinding?.templateCode || '--' }}</span>
            <span v-if="activeTemplate?.version">v{{ activeTemplate.version }}</span>
          </div>
          <div class="preview-tags">
            <el-tag
              v-for="item in templateVariableList(activeTemplate)"
              :key="'template-' + item"
              size="small"
              effect="plain"
            >
              {{ item }}
            </el-tag>
          </div>
          <pre class="preview-content">{{ activeTemplate?.content || '--' }}</pre>
        </el-card>
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">备用模板与模型</div>
          </template>
          <div class="preview-meta">
            <span>{{ fallbackTemplate?.code || previewBinding?.fallbackTemplateCode || '未配置备用模板' }}</span>
            <span v-if="fallbackTemplate?.version">v{{ fallbackTemplate.version }}</span>
          </div>
          <div class="preview-tags">
            <el-tag
              v-for="item in templateVariableList(fallbackTemplate)"
              :key="'fallback-' + item"
              size="small"
              type="warning"
              effect="plain"
            >
              {{ item }}
            </el-tag>
          </div>
          <pre class="preview-content">{{ fallbackTemplate?.content || '--' }}</pre>
          <el-descriptions :column="1" border size="small" class="model-summary">
            <el-descriptions-item label="模型">{{ previewModelName }}</el-descriptions-item>
            <el-descriptions-item label="提供商">{{ previewModel?.provider || '--' }}</el-descriptions-item>
            <el-descriptions-item label="模型编码">{{ previewModel?.modelCode || previewModel?.modelVersion || '--' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </div>
    </el-card>

    <el-dialog v-model="open" :title="title" width="860px" append-to-body>
      <el-form ref="bindingRef" :model="form" :rules="rules" label-width="150px">
        <TradeFormSection title="覆盖规则基础" description="这里只配置相对 Agent Profile 默认值的高级覆盖范围；默认模型和模板请优先在 Agent Profile 中维护。">
          <el-form-item label="绑定名称" prop="bindingName">
            <el-input v-model="form.bindingName" placeholder="监督者影子绑定" />
          </el-form-item>
          <el-form-item label="策略">
            <el-select v-model="form.strategyId" clearable filterable placeholder="允许全局绑定" style="width: 100%" @change="handleStrategyChange">
              <el-option v-for="item in strategyOptions" :key="item.id" :label="item.strategyName || item.strategyKey" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="策略版本">
            <el-select v-model="form.strategyVersionId" clearable filterable placeholder="可选的精确版本范围" style="width: 100%">
              <el-option v-for="item in strategyVersionOptions" :key="item.id" :label="`v${item.versionNo || item.id}`" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="交易对">
            <el-select v-model="form.symbol" clearable placeholder="可选的交易对范围" style="width: 100%">
              <el-option v-for="item in promptBindingSymbolOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="交易所">
            <el-select v-model="form.exchangeCode" clearable placeholder="可选的交易所范围" style="width: 100%">
              <el-option v-for="item in promptBindingExchangeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="绑定范围" prop="bindingScope">
            <el-select v-model="form.bindingScope" filterable placeholder="选择范围" style="width: 100%" @change="syncOutputSchemaByScope">
              <el-option
                v-for="item in promptBindingScopeOptions"
                :key="item"
                :label="formatTradeLabel('promptScope', item)"
                :value="item"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="优先级" prop="priority">
            <el-input-number v-model="form.priority" :min="1" :max="999" :step="1" style="width: 100%" />
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.enabled" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="可选的范围备注" />
          </el-form-item>
        </TradeFormSection>

        <TradeFormSection title="可选覆盖项" description="这些字段都不是主配置。留空表示沿用 Agent Profile 默认值，只在需要按策略、品种或事件强度改写时填写。">
          <div class="binding-reference-actions">
            <el-button link type="primary" @click="openPromptTemplateConsole">管理提示词模板</el-button>
            <el-button link type="primary" @click="openAiModelConsole">管理 AI 模型</el-button>
            <el-button v-if="selectedModelMissing" link type="warning" @click="form.modelId = null">清空失效模型</el-button>
          </div>
          <el-alert
            v-if="selectedTemplateMissing || fallbackTemplateMissing || selectedModelMissing"
            type="warning"
            :closable="false"
            show-icon
            class="binding-reference-alert"
            :title="[
              selectedTemplateMissing ? `主模板未启用或不存在: ${form.templateCode}` : '',
              fallbackTemplateMissing ? `备用模板未启用或不存在: ${form.fallbackTemplateCode}` : '',
              selectedModelMissing ? `模型引用已失效: #${form.modelId}` : ''
            ].filter(Boolean).join('；')"
          />
          <el-form-item label="覆盖模板">
            <el-select v-model="form.templateCode" clearable filterable allow-create default-first-option placeholder="留空则使用 Agent Profile 默认模板" style="width: 100%">
              <el-option v-for="item in templateOptions" :key="item.id || item.code" :label="item.code" :value="item.code" />
            </el-select>
          </el-form-item>
          <el-form-item label="备用模板">
            <el-select v-model="form.fallbackTemplateCode" clearable filterable allow-create default-first-option placeholder="可选的备用模板" style="width: 100%">
              <el-option v-for="item in templateOptions" :key="`${item.id || item.code}-fallback`" :label="item.code" :value="item.code" />
            </el-select>
          </el-form-item>
          <el-form-item label="模型">
            <el-select v-model="form.modelId" clearable filterable placeholder="可选的模型覆盖" style="width: 100%">
              <el-option
                v-for="item in modelOptions"
                :key="item.id"
                :label="item.modelName || item.name || item.modelCode || `#${item.id}`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="覆盖输出模式">
            <el-select v-model="form.outputSchemaCode" clearable filterable allow-create default-first-option placeholder="留空则使用 Agent Profile 默认输出模式" style="width: 100%">
              <el-option
                v-for="item in promptBindingSchemaOptions"
                :key="item"
                :label="formatTradeLabel('outputSchema', item)"
                :value="item"
              />
            </el-select>
          </el-form-item>
        </TradeFormSection>

        <TradeFormSection title="触发范围" description="最后限定这条模板绑定在哪些运行模式、事件强度下生效。">
          <el-form-item label="运行模式" prop="runtimeModes">
            <el-select v-model="form.runtimeModes" multiple placeholder="选择运行模式" style="width: 100%">
              <el-option
                v-for="item in promptBindingRuntimeModeOptions"
                :key="item"
                :label="formatTradeLabel('runtimeMode', item)"
                :value="item"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="事件强度" prop="eventStrengths">
            <el-select v-model="form.eventStrengths" multiple placeholder="选择事件强度" style="width: 100%">
              <el-option
                v-for="item in promptBindingEventStrengthOptions"
                :key="item"
                :label="formatTradeLabel('eventStrength', item)"
                :value="item"
              />
            </el-select>
          </el-form-item>
        </TradeFormSection>
      </el-form>
      <div class="dialog-preview-grid">
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">模板预览</div>
          </template>
          <pre class="preview-content">{{ activeTemplate?.content || '--' }}</pre>
        </el-card>
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">模型摘要</div>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="策略">{{ previewStrategyName }}</el-descriptions-item>
            <el-descriptions-item label="模型">{{ previewModelName }}</el-descriptions-item>
            <el-descriptions-item label="备用模板">{{ fallbackTemplate?.code || form.fallbackTemplateCode || '--' }}</el-descriptions-item>
            <el-descriptions-item label="模板变量">
              {{ templateVariableList(activeTemplate).join(', ') || '--' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </div>
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
 * 提示词绑定页面工具函数模块
 * 提供绑定配置表单创建、数据转换、验证等辅助函数
 */

function trimValue(value) {
  return String(value ?? '').trim()
}

function parseInteger(value, fallback = null) {
  if (value == null || value === '') {
    return fallback
  }
  const parsed = Number.parseInt(String(value).trim(), 10)
  return Number.isNaN(parsed) ? fallback : parsed
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
  return Array.from(new Set((Array.isArray(values) ? values : []).map((item) => transform(trimValue(item))).filter(Boolean)))
}

export const promptBindingSymbolOptions = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
// 交易所选项从后端获取，此处保留默认值作为后备
export const promptBindingExchangeOptions = ['BINANCE', 'OKX']
export const promptBindingRuntimeModeOptions = ['paper', 'shadow', 'live']
export const promptBindingEventStrengthOptions = ['strong', 'normal', 'noise']
export const promptBindingScopeOptions = ['SUPERVISOR', 'MARKET_AGENT', 'NEWS_AGENT', 'ONCHAIN_AGENT', 'SOCIAL_AGENT', 'DELIBERATION_REFEREE']
export const promptBindingSchemaOptions = ['supervisor_decision_v1', 'agent_view_v1', 'deliberation_referee_v1']

function defaultSchemaForScope(scope) {
  if (scope === 'SUPERVISOR') {
    return 'supervisor_decision_v1'
  }
  if (scope === 'DELIBERATION_REFEREE') {
    return 'deliberation_referee_v1'
  }
  if (['MARKET_AGENT', 'NEWS_AGENT', 'ONCHAIN_AGENT', 'SOCIAL_AGENT'].includes(scope)) {
    return 'agent_view_v1'
  }
  return ''
}

export function createTradePromptBindingForm(binding = {}) {
  return {
    id: binding.id,
    bindingName: trimValue(binding.bindingName),
    strategyId: binding.strategyId ?? null,
    strategyVersionId: binding.strategyVersionId ?? null,
    symbol: trimValue(binding.symbol).toUpperCase() || '',
    exchangeCode: trimValue(binding.exchangeCode).toUpperCase() || '',
    bindingScope: trimValue(binding.bindingScope).toUpperCase() || 'SUPERVISOR',
    templateCode: trimValue(binding.templateCode),
    fallbackTemplateCode: trimValue(binding.fallbackTemplateCode),
    modelId: binding.modelId ?? null,
    outputSchemaCode: trimValue(binding.outputSchemaCode),
    priority: parseInteger(binding.priority, 100) ?? 100,
    runtimeModes: parseJsonArray(binding.modeScopeJson).map((item) => item.toLowerCase()),
    eventStrengths: parseJsonArray(binding.eventStrengthScopeJson).map((item) => item.toLowerCase()),
    enabled: binding.enabled !== false,
    remark: trimValue(binding.remark)
  }
}

function optionIncludesTemplateCode(options, code) {
  return Boolean(findTemplateByCode(options, code))
}

function optionIncludesModelId(options, modelId) {
  return Boolean(findModelById(options, modelId))
}

export function buildTradePromptBindingPayload(form = {}, referenceOptions = {}) {
  const modelId = form.modelId ?? null
  const normalizedModelId = (
    modelId == null
    || !Array.isArray(referenceOptions.modelOptions)
    || optionIncludesModelId(referenceOptions.modelOptions, modelId)
  )
    ? modelId
    : null
  return {
    id: form.id,
    bindingName: trimValue(form.bindingName),
    strategyId: form.strategyId ?? null,
    strategyVersionId: form.strategyVersionId ?? null,
    symbol: trimValue(form.symbol).toUpperCase() || null,
    exchangeCode: trimValue(form.exchangeCode).toUpperCase() || null,
    bindingScope: trimValue(form.bindingScope).toUpperCase(),
    templateCode: trimValue(form.templateCode) || null,
    fallbackTemplateCode: trimValue(form.fallbackTemplateCode) || null,
    modelId: normalizedModelId,
    outputSchemaCode: trimValue(form.outputSchemaCode) || null,
    priority: parseInteger(form.priority, 100) ?? 100,
    modeScopeJson: JSON.stringify(normalizeArray(form.runtimeModes, (item) => item.toLowerCase())),
    eventStrengthScopeJson: JSON.stringify(normalizeArray(form.eventStrengths, (item) => item.toLowerCase())),
    enabled: Boolean(form.enabled),
    remark: trimValue(form.remark) || null
  }
}

export function validateTradePromptBindingPayload(form = {}, referenceOptions = {}) {
  const payload = buildTradePromptBindingPayload(form, referenceOptions)
  if (!payload.bindingName) {
    throw new Error('绑定名称不能为空')
  }
  if (!payload.bindingScope) {
    throw new Error('绑定范围不能为空')
  }
  if (!promptBindingScopeOptions.includes(payload.bindingScope)) {
    throw new Error(`不支持的绑定范围: ${payload.bindingScope}`)
  }
  if (payload.templateCode && Array.isArray(referenceOptions.templateOptions) && !optionIncludesTemplateCode(referenceOptions.templateOptions, payload.templateCode)) {
    throw new Error(`提示词模板不存在或未启用: ${payload.templateCode}`)
  }
  if (
    payload.fallbackTemplateCode
    && Array.isArray(referenceOptions.templateOptions)
    && !optionIncludesTemplateCode(referenceOptions.templateOptions, payload.fallbackTemplateCode)
  ) {
    throw new Error(`备用提示词模板不存在或未启用: ${payload.fallbackTemplateCode}`)
  }
  if (payload.fallbackTemplateCode && !payload.templateCode) {
    throw new Error('填写备用模板时必须同时填写覆盖模板')
  }
  if (payload.symbol && !promptBindingSymbolOptions.includes(payload.symbol)) {
    throw new Error(`不支持的 V1 交易对: ${payload.symbol}`)
  }
  if (payload.exchangeCode && !promptBindingExchangeOptions.includes(payload.exchangeCode)) {
    throw new Error(`不支持的 V1 交易所: ${payload.exchangeCode}`)
  }
  const runtimeModes = parseJsonArray(payload.modeScopeJson)
  const eventStrengths = parseJsonArray(payload.eventStrengthScopeJson)
  if (!runtimeModes.length) {
    throw new Error('请至少选择一个运行模式')
  }
  if (!eventStrengths.length) {
    throw new Error('请至少选择一个事件强度')
  }
  const unsupportedMode = runtimeModes.find((item) => !promptBindingRuntimeModeOptions.includes(item))
  if (unsupportedMode) {
    throw new Error(`不支持的运行模式: ${unsupportedMode}`)
  }
  const unsupportedStrength = eventStrengths.find((item) => !promptBindingEventStrengthOptions.includes(item))
  if (unsupportedStrength) {
    throw new Error(`不支持的事件强度: ${unsupportedStrength}`)
  }
  const expectedSchema = defaultSchemaForScope(payload.bindingScope)
  if (!payload.outputSchemaCode) {
    return payload
  }
  if (expectedSchema === 'supervisor_decision_v1' && payload.outputSchemaCode !== expectedSchema) {
    throw new Error('监督者范围必须使用监督者决策输出模式')
  }
  if (expectedSchema === 'agent_view_v1' && payload.outputSchemaCode !== expectedSchema) {
    throw new Error('专家范围必须使用专家视图输出模式')
  }
  if (
    payload.bindingScope === 'DELIBERATION_REFEREE'
    && !['agent_view_v1', 'deliberation_referee_v1'].includes(payload.outputSchemaCode)
  ) {
    throw new Error('复核裁判范围必须使用允许的输出模式')
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
function findModelById(options, modelId) {
  if (modelId == null || modelId === '') {
    return null
  }
  return (Array.isArray(options) ? options : []).find((item) => Number(item?.id) === Number(modelId)) || null
}
function templateVariableList(template) {
  if (!template) {
    return []
  }
  return parseJsonArray(template.variables)
}
</script>

<script setup>
import { computed, getCurrentInstance, reactive, ref } from 'vue'

import TradeFormSection from '@/components/trade/TradeFormSection.vue'
import { listAiModel } from '@/api/dca/ai'
import { listTemplate } from '@/api/dca/template'
import { addTradePromptBinding, delTradePromptBinding, listTradePromptBinding, updateTradePromptBinding } from '@/api/dca/tradePromptBinding'
import { listTradeStrategy, listTradeStrategyVersions } from '@/api/dca/tradeStrategy'
import { formatTradeLabel, formatTradeLabels } from '@/utils/tradeLabels'

const { proxy } = getCurrentInstance()

const loading = ref(false)
const submitting = ref(false)
const open = ref(false)
const title = ref('添加提示词绑定')
const bindingRef = ref()
const bindingList = ref([])
const total = ref(0)
const strategyOptions = ref([])
const strategyVersionOptions = ref([])
const templateOptions = ref([])
const modelOptions = ref([])
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  strategyId: null,
  bindingScope: '',
  enabled: ''
})
const form = reactive(createTradePromptBindingForm({
  bindingScope: 'SUPERVISOR',
  runtimeModes: ['shadow'],
  eventStrengths: ['normal'],
  enabled: true
}))
const strategyMap = computed(() => new Map(strategyOptions.value.map((item) => [item.id, item])))
const previewBinding = computed(() => (open.value ? form : (bindingList.value[0] || null)))
const activeTemplate = computed(() => findTemplateByCode(templateOptions.value, previewBinding.value?.templateCode))
const fallbackTemplate = computed(() => findTemplateByCode(templateOptions.value, previewBinding.value?.fallbackTemplateCode))
const previewModel = computed(() => findModelById(modelOptions.value, previewBinding.value?.modelId))
const previewStrategyName = computed(() => resolveStrategyName(previewBinding.value?.strategyId))
const previewModelName = computed(() => (
  previewModel.value?.modelName
  || previewModel.value?.name
  || previewModel.value?.modelCode
  || (previewBinding.value?.modelId ? '#' + previewBinding.value.modelId : '--')
))
const selectedTemplateMissing = computed(() => Boolean(form.templateCode) && !findTemplateByCode(templateOptions.value, form.templateCode))
const fallbackTemplateMissing = computed(() => Boolean(form.fallbackTemplateCode) && !findTemplateByCode(templateOptions.value, form.fallbackTemplateCode))
const selectedModelMissing = computed(() => form.modelId != null && !findModelById(modelOptions.value, form.modelId))
const rules = {
  bindingName: [{ required: true, message: '绑定名称不能为空', trigger: 'blur' }],
  bindingScope: [{ required: true, message: '绑定范围不能为空', trigger: 'change' }],
  runtimeModes: [{ required: true, message: '请至少选择一个运行模式', trigger: 'change' }],
  eventStrengths: [{ required: true, message: '请至少选择一个事件强度', trigger: 'change' }]
}

function resolveStrategyName(strategyId) {
  if (!strategyId) {
    return '全局'
  }
  const strategy = strategyMap.value.get(strategyId)
  return strategy?.strategyName || strategy?.strategyKey || `#${strategyId}`
}

function resetForm(binding = {}) {
  Object.assign(form, createTradePromptBindingForm({
    bindingScope: 'SUPERVISOR',
    runtimeModes: ['shadow'],
    eventStrengths: ['normal'],
    enabled: true,
    ...binding
  }))
  bindingRef.value?.clearValidate()
}

function syncOutputSchemaByScope(scope) {
  if (form.outputSchemaCode) {
    form.outputSchemaCode = defaultSchemaForScope(scope)
  }
}

async function loadStrategyVersions(strategyId) {
  if (!strategyId) {
    strategyVersionOptions.value = []
    return
  }
  const response = await listTradeStrategyVersions(strategyId)
  strategyVersionOptions.value = response?.data || response || []
}

async function handleStrategyChange(strategyId) {
  form.strategyVersionId = null
  await loadStrategyVersions(strategyId)
}

function openPromptTemplateConsole() {
  proxy?.$router?.push?.('/trade/prompt-template')
}

function openAiModelConsole() {
  proxy?.$router?.push?.('/ai')
}

async function loadOptions() {
  const [strategyResponse, templateResponse, modelResponse] = await Promise.all([
    listTradeStrategy({ pageNum: 1, pageSize: 200 }),
    listTemplate({ pageNum: 1, pageSize: 200 }),
    listAiModel({ pageNum: 1, pageSize: 200 })
  ])
  strategyOptions.value = strategyResponse?.rows || []
  templateOptions.value = (templateResponse?.rows || []).filter((item) => Number(item.isActive ?? 1) === 1)
  modelOptions.value = (modelResponse?.rows || []).filter((item) => Number(item.isEnabled ?? item.enabled ?? 1) === 1)
}

function handleQuery() {
  queryParams.pageNum = 1
  getList()
}

async function getList() {
  loading.value = true
  try {
    const response = await listTradePromptBinding({
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
  strategyVersionOptions.value = []
  title.value = '添加提示词绑定'
  open.value = true
}

async function handleUpdate(row) {
  resetForm(row)
  await loadStrategyVersions(row.strategyId)
  title.value = '修改提示词绑定'
  open.value = true
}

async function submitForm() {
  await bindingRef.value?.validate()
  submitting.value = true
  try {
    const payload = validateTradePromptBindingPayload(form, {
      templateOptions: templateOptions.value,
      modelOptions: modelOptions.value
    })
    if (payload.id) {
      await updateTradePromptBinding(payload)
      proxy?.$modal?.msgSuccess?.('提示词绑定已更新')
    } else {
      await addTradePromptBinding(payload)
      proxy?.$modal?.msgSuccess?.('提示词绑定已新增')
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
    await proxy?.$modal?.confirm?.(`确认删除提示词绑定“${row.bindingName}”吗？`)
    await delTradePromptBinding(row.id)
    proxy?.$modal?.msgSuccess?.('提示词绑定已删除')
    await getList()
  } catch (error) {
    // ignore when cancelled
  }
}

Promise.all([loadOptions(), getList()])
function findTemplateByCode(options, code) {
  const normalized = trimValue(code)
  if (!normalized) {
    return null
  }
  return (Array.isArray(options) ? options : []).find((item) => trimValue(item?.code) === normalized) || null
}
function findModelById(options, modelId) {
  if (modelId == null || modelId === '') {
    return null
  }
  return (Array.isArray(options) ? options : []).find((item) => Number(item?.id) === Number(modelId)) || null
}
function templateVariableList(template) {
  if (!template) {
    return []
  }
  return parseJsonArray(template.variables)
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
.binding-reference-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.binding-reference-alert {
  margin-bottom: 16px;
}
.detail-grid,
.dialog-preview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 16px;
}
.dialog-preview-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.detail-card {
  min-width: 0;
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
  min-height: 140px;
  border-radius: 10px;
  background: #f8fafc;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: auto;
}
.model-summary {
  margin-top: 12px;
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .detail-grid,
  .dialog-preview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
