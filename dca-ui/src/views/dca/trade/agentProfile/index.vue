<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>智能代理配置</span>
          <div class="card-header__actions">
            <el-button type="primary" v-hasPermi="['dca:tradeAgentProfile:add']" @click="handleAdd">添加代理</el-button>
            <el-button plain @click="getList">刷新</el-button>
          </div>
        </div>
      </template>

      <div class="toolbar">
        <el-select v-model="queryParams.agentType" clearable placeholder="代理类型" style="width: 180px" @change="handleQuery">
          <el-option v-for="item in tradeAgentTypeOptions" :key="item" :label="formatTradeLabel('agentType', item)" :value="item" />
        </el-select>
        <el-select v-model="queryParams.enabled" clearable placeholder="状态" style="width: 160px" @change="handleQuery">
          <el-option label="启用" :value="true" />
          <el-option label="禁用" :value="false" />
        </el-select>
      </div>

      <el-table
        v-loading="loading"
        :data="profileList"
        row-key="id"
        highlight-current-row
        empty-text="无代理配置"
        @current-change="handleCurrentChange"
      >
        <el-table-column prop="agentCode" label="代理编码" min-width="160" />
        <el-table-column prop="agentName" label="代理名称" min-width="180" />
        <el-table-column label="类型" width="120">
          <template #default="scope">
            {{ formatTradeLabel('agentType', scope.row.agentType) || scope.row.agentType }}
          </template>
        </el-table-column>
        <el-table-column label="LLM" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.llmEnabled ? 'success' : 'info'">
              {{ scope.row.llmEnabled ? '开启' : '关闭' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="对话" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.dialogueEnabled ? 'warning' : 'info'">
              {{ scope.row.dialogueEnabled ? `R${scope.row.maxDialogueRounds || 0}` : '关闭' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结构模式" min-width="160">
          <template #default="scope">
            {{ formatTradeLabel('outputSchema', scope.row.structuredSchemaCode) || scope.row.structuredSchemaCode }}
          </template>
        </el-table-column>
        <el-table-column prop="defaultTemplateCode" label="默认模板" min-width="180" show-overflow-tooltip />
        <el-table-column label="默认模型" min-width="160" show-overflow-tooltip>
          <template #default="scope">
            {{ modelLabel(scope.row.defaultModelId) }}
          </template>
        </el-table-column>
        <el-table-column prop="timeoutSeconds" label="超时(秒)" width="120" />
        <el-table-column prop="speakOrder" label="顺序" width="100" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.enabled ? 'success' : 'info'">
              {{ scope.row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button link type="primary" v-hasPermi="['dca:tradeAgentProfile:edit']" @click="handleUpdate(scope.row)">修改</el-button>
            <el-button link type="danger" v-hasPermi="['dca:tradeAgentProfile:remove']" @click="handleDelete(scope.row)">删除</el-button>
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
            <div class="detail-card__header">代理详情</div>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="代理编码">{{ previewProfile?.agentCode || '--' }}</el-descriptions-item>
            <el-descriptions-item label="代理类型">{{ formatTradeLabel('agentType', previewProfile?.agentType) || previewProfile?.agentType || '--' }}</el-descriptions-item>
            <el-descriptions-item label="结构模式">{{ formatTradeLabel('outputSchema', previewProfile?.structuredSchemaCode) || previewProfile?.structuredSchemaCode || '--' }}</el-descriptions-item>
            <el-descriptions-item label="默认模型">{{ modelLabel(previewProfile?.defaultModelId) }}</el-descriptions-item>
            <el-descriptions-item label="默认模板">{{ previewProfile?.defaultTemplateCode || '--' }}</el-descriptions-item>
            <el-descriptions-item label="默认回退模板">{{ previewProfile?.defaultFallbackTemplateCode || '--' }}</el-descriptions-item>
            <el-descriptions-item label="默认输出模式">{{ formatTradeLabel('outputSchema', previewProfile?.defaultOutputSchemaCode) || previewProfile?.defaultOutputSchemaCode || '--' }}</el-descriptions-item>
            <el-descriptions-item label="超时秒数">{{ previewProfile?.timeoutSeconds || '--' }}</el-descriptions-item>
            <el-descriptions-item label="最大重试">{{ previewProfile?.maxRetries ?? '--' }}</el-descriptions-item>
            <el-descriptions-item label="发言顺序">{{ previewProfile?.speakOrder ?? '--' }}</el-descriptions-item>
          </el-descriptions>
          <div class="preview-tags">
            <el-tag v-for="item in previewCapabilityTags" :key="item" size="small" effect="plain">
              {{ item }}
            </el-tag>
          </div>
        </el-card>
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">工具策略</div>
          </template>
          <pre class="preview-content">{{ previewToolPolicyText }}</pre>
        </el-card>
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">运行选项</div>
          </template>
          <div class="preview-tags">
            <el-tag v-if="previewProfile?.temperatureOverride != null" size="small" type="warning" effect="plain">
              temperature={{ previewProfile.temperatureOverride }}
            </el-tag>
            <el-tag v-if="previewProfile?.topPOverride != null" size="small" type="warning" effect="plain">
              top_p={{ previewProfile.topPOverride }}
            </el-tag>
            <el-tag v-if="previewProfile?.maxTokensOverride != null" size="small" type="warning" effect="plain">
              max_tokens={{ previewProfile.maxTokensOverride }}
            </el-tag>
          </div>
          <pre class="preview-content">{{ previewRuntimeOptionsText }}</pre>
        </el-card>
      </div>
    </el-card>

    <el-dialog v-model="open" :title="title" width="860px" append-to-body>
      <el-form ref="profileRef" :model="form" :rules="rules" label-width="150px">
        <TradeFormSection title="代理基础" description="先确定代理身份、类型、输出结构，以及这条配置是否启用。">
          <el-form-item label="代理编码" prop="agentCode">
            <el-select v-model="form.agentCode" filterable placeholder="选择代理编码" style="width: 100%">
              <el-option v-for="item in tradeAgentCodeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="代理名称" prop="agentName">
            <el-input v-model="form.agentName" placeholder="市场专家" />
          </el-form-item>
          <el-form-item label="代理类型" prop="agentType">
            <el-select v-model="form.agentType" filterable placeholder="选择代理类型" style="width: 100%">
              <el-option v-for="item in tradeAgentTypeOptions" :key="item" :label="formatTradeLabel('agentType', item)" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="结构模式" prop="structuredSchemaCode">
            <el-select v-model="form.structuredSchemaCode" filterable allow-create default-first-option placeholder="选择模式" style="width: 100%">
              <el-option v-for="item in tradeAgentSchemaOptions" :key="item" :label="formatTradeLabel('outputSchema', item)" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.enabled" />
          </el-form-item>
        </TradeFormSection>

        <TradeFormSection title="默认模型与提示词" description="这里是 Agent 的主配置入口；提示词绑定只用于按策略、品种或事件强度做高级覆盖。">
          <el-form-item label="默认模型" prop="defaultModelId">
            <el-select v-model="form.defaultModelId" clearable filterable placeholder="选择默认模型" style="width: 100%">
              <el-option
                v-for="item in modelOptions"
                :key="item.id"
                :label="item.modelName || item.name || item.modelCode || `#${item.id}`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="默认模板" prop="defaultTemplateCode">
            <el-select v-model="form.defaultTemplateCode" clearable filterable allow-create default-first-option placeholder="选择默认模板" style="width: 100%">
              <el-option v-for="item in templateOptions" :key="item.id || item.code" :label="item.code" :value="item.code" />
            </el-select>
          </el-form-item>
          <el-form-item label="默认回退模板">
            <el-select v-model="form.defaultFallbackTemplateCode" clearable filterable allow-create default-first-option placeholder="可选回退模板" style="width: 100%">
              <el-option v-for="item in templateOptions" :key="`${item.id || item.code}-fallback`" :label="item.code" :value="item.code" />
            </el-select>
          </el-form-item>
          <el-form-item label="默认输出模式" prop="defaultOutputSchemaCode">
            <el-select v-model="form.defaultOutputSchemaCode" clearable filterable allow-create default-first-option placeholder="默认继承结构模式" style="width: 100%">
              <el-option v-for="item in tradeAgentSchemaOptions" :key="item" :label="formatTradeLabel('outputSchema', item)" :value="item" />
            </el-select>
          </el-form-item>
        </TradeFormSection>

        <TradeFormSection title="运行行为" description="这里配置是否调用模型、是否允许对话、多轮上限，以及超时和采样参数。">
          <el-form-item label="启用 LLM">
            <el-switch v-model="form.llmEnabled" />
          </el-form-item>
          <el-form-item label="启用对话">
            <el-switch v-model="form.dialogueEnabled" />
          </el-form-item>
          <el-form-item label="对话轮数" prop="maxDialogueRounds">
            <el-input-number v-model="form.maxDialogueRounds" :min="0" :max="2" :step="1" style="width: 100%" />
          </el-form-item>
          <el-form-item label="发言顺序" prop="speakOrder">
            <el-input-number v-model="form.speakOrder" :min="0" :max="999" :step="1" style="width: 100%" />
          </el-form-item>
          <el-form-item label="超时秒数" prop="timeoutSeconds">
            <el-input-number v-model="form.timeoutSeconds" :min="1" :max="300" :step="1" style="width: 100%" />
          </el-form-item>
          <el-form-item label="最大重试" prop="maxRetries">
            <el-input-number v-model="form.maxRetries" :min="0" :max="10" :step="1" style="width: 100%" />
          </el-form-item>
          <el-form-item label="温度">
            <el-input-number v-model="form.temperatureOverride" :min="0" :max="1" :step="0.05" style="width: 100%" />
          </el-form-item>
          <el-form-item label="Top P">
            <el-input-number v-model="form.topPOverride" :min="0" :max="1" :step="0.05" style="width: 100%" />
          </el-form-item>
          <el-form-item label="最大 Token">
            <el-input-number v-model="form.maxTokensOverride" :min="1" :max="16000" :step="100" style="width: 100%" />
          </el-form-item>
        </TradeFormSection>

        <TradeFormSection title="工具与高级配置" description="常用工具白名单、黑名单和回退策略可直接配置，更复杂的约束放在高级 JSON 中。">
          <el-form-item label="允许工具">
            <TradeEditableTags
              v-model="form.toolAllowList"
              :options="toolPolicyOptionPool"
              placeholder="输入或选择允许调用的工具"
            />
          </el-form-item>
          <el-form-item label="禁止工具">
            <TradeEditableTags
              v-model="form.toolDenyList"
              :options="toolPolicyOptionPool"
              placeholder="输入或选择禁止调用的工具"
            />
          </el-form-item>
          <el-form-item label="回退策略">
            <el-input v-model="form.runtimeFallback" placeholder="RULE" />
          </el-form-item>
          <el-form-item label="高级工具策略">
            <TradeAdvancedJsonEditor
              v-model="form.toolPolicyJson"
              title="工具策略 JSON"
              description="这里保留允许/禁止列表之外的高级工具约束。"
              placeholder='{"require":["market_snapshot"]}'
              :rows="4"
            />
          </el-form-item>
          <el-form-item label="高级运行选项">
            <TradeAdvancedJsonEditor
              v-model="form.runtimeOptionsJson"
              title="运行选项 JSON"
              description="这里保留回退策略之外的高级运行选项。"
              placeholder='{"fallback":"RULE"}'
              :rows="4"
            />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="可选运行备注" />
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
 * 智能代理配置页面工具函数模块
 * 提供代理配置表单创建、数据转换、验证等辅助函数
 */

/**
 * 去除字符串首尾空白
 * @param {*} value - 输入值
 * @returns {string} 去除空白后的字符串
 */
function trimValue(value) {
  return String(value ?? '').trim()
}

/**
 * 解析JSON对象
 * @param {*} value - 输入值
 * @param {Object} fallback - 默认值
 * @returns {Object} 解析后的对象
 */
function parseJsonObject(value, fallback = {}) {
  if (!value || !trimValue(value)) {
    return { ...fallback }
  }
  const parsed = typeof value === 'string' ? JSON.parse(value) : value
  return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : { ...fallback }
}

/**
 * 标准化字符串数组
 * @param {Array} values - 输入数组
 * @returns {Array} 标准化后的数组
 */
function normalizeStringArray(values = []) {
  return Array.from(
    new Set(
      (Array.isArray(values) ? values : [])
        .map((item) => trimValue(item))
        .filter(Boolean)
    )
  )
}

/**
 * 格式化JSON为美化的字符串
 * @param {*} value - 输入值
 * @returns {string} 格式化后的JSON字符串
 */
function prettyJson(value) {
  try {
    return JSON.stringify(parseJsonObject(value), null, 2)
  } catch {
    return '{}'
  }
}

/**
 * 格式化可选JSON为美化的字符串
 * @param {*} value - 输入值
 * @returns {string} 格式化后的JSON字符串，空对象返回空字符串
 */
function prettyOptionalJson(value) {
  const parsed = parseJsonObject(value)
  return Object.keys(parsed).length ? JSON.stringify(parsed, null, 2) : ''
}

/**
 * 将对象序列化为JSON字符串
 * @param {*} value - 输入值
 * @returns {string} JSON字符串
 */
function stringifyJson(value) {
  return JSON.stringify(parseJsonObject(value))
}

/**
 * 解析可选数字值
 * @param {*} value - 输入值
 * @returns {number|null} 解析后的数字或null
 */
function parseOptionalNumber(value) {
  if (value == null || value === '') {
    return null
  }
  const parsed = Number(value)
  return Number.isNaN(parsed) ? null : parsed
}

export const tradeAgentCodeOptions = [
  'market_agent',
  'news_agent',
  'onchain_agent',
  'social_agent',
  'supervisor_agent',
  'deliberation_referee'
]
export const tradeAgentTypeOptions = ['RULE', 'LLM', 'HYBRID']
export const tradeAgentSchemaOptions = ['agent_view_v1', 'supervisor_decision_v1', 'deliberation_referee_v1']
export const toolPolicyOptionPool = ['market_snapshot', 'news_context', 'onchain_context', 'social_context']

/**
 * 剥离代理工具策略中的允许和禁止列表
 * @param {*} value - 工具策略JSON
 * @returns {Object} 剥离后的工具策略对象
 */
function stripTradeAgentToolPolicy(value) {
  const parsed = parseJsonObject(value)
  delete parsed.allow
  delete parsed.deny
  return parsed
}

/**
 * 剥离代理运行选项中的回退策略
 * @param {*} value - 运行选项JSON
 * @returns {Object} 剥离后的运行选项对象
 */
function stripTradeAgentRuntimeOptions(value) {
  const parsed = parseJsonObject(value)
  delete parsed.fallback
  return parsed
}

/**
 * 构建代理工具策略
 * @param {Object} form - 表单数据
 * @returns {Object} 工具策略对象
 */
function buildTradeAgentToolPolicy(form = {}) {
  const payload = stripTradeAgentToolPolicy(form.toolPolicyJson)
  const rawToolPolicy = parseJsonObject(form.toolPolicyJson)
  const allow = Array.isArray(form.toolAllowList)
    ? normalizeStringArray(form.toolAllowList)
    : normalizeStringArray(rawToolPolicy.allow)
  const deny = Array.isArray(form.toolDenyList)
    ? normalizeStringArray(form.toolDenyList)
    : normalizeStringArray(rawToolPolicy.deny)
  if (allow.length) {
    payload.allow = allow
  }
  if (deny.length) {
    payload.deny = deny
  }
  return payload
}

/**
 * 构建代理运行选项
 * @param {Object} form - 表单数据
 * @returns {Object} 运行选项对象
 */
function buildTradeAgentRuntimeOptions(form = {}) {
  const payload = stripTradeAgentRuntimeOptions(form.runtimeOptionsJson)
  const rawRuntimeOptions = parseJsonObject(form.runtimeOptionsJson)
  const fallback = trimValue(
    Object.prototype.hasOwnProperty.call(form, 'runtimeFallback')
      ? form.runtimeFallback
      : rawRuntimeOptions.fallback
  )
  if (fallback) {
    payload.fallback = fallback
  }
  return payload
}

/**
 * 创建智能代理配置表单对象
 * @param {Object} profile - 代理配置数据
 * @returns {Object} 表单对象
 */
export function createTradeAgentProfileForm(profile = {}) {
  const rawToolPolicy = parseJsonObject(profile.toolPolicyJson)
  const rawRuntimeOptions = parseJsonObject(profile.runtimeOptionsJson)
  return {
    id: profile.id,
    agentCode: trimValue(profile.agentCode).toLowerCase(),
    agentName: trimValue(profile.agentName),
    agentType: trimValue(profile.agentType).toUpperCase() || 'RULE',
    enabled: profile.enabled !== false,
    llmEnabled: Boolean(profile.llmEnabled),
    dialogueEnabled: Boolean(profile.dialogueEnabled),
    maxDialogueRounds: parseOptionalNumber(profile.maxDialogueRounds) ?? 0,
    speakOrder: parseOptionalNumber(profile.speakOrder) ?? 100,
    timeoutSeconds: parseOptionalNumber(profile.timeoutSeconds) ?? 30,
    maxRetries: parseOptionalNumber(profile.maxRetries) ?? 1,
    temperatureOverride: parseOptionalNumber(profile.temperatureOverride),
    topPOverride: parseOptionalNumber(profile.topPOverride),
    maxTokensOverride: parseOptionalNumber(profile.maxTokensOverride),
    structuredSchemaCode: trimValue(profile.structuredSchemaCode),
    defaultModelId: profile.defaultModelId ?? null,
    defaultTemplateCode: trimValue(profile.defaultTemplateCode),
    defaultFallbackTemplateCode: trimValue(profile.defaultFallbackTemplateCode),
    defaultOutputSchemaCode: trimValue(profile.defaultOutputSchemaCode),
    toolAllowList: normalizeStringArray(rawToolPolicy.allow),
    toolDenyList: normalizeStringArray(rawToolPolicy.deny),
    runtimeFallback: trimValue(rawRuntimeOptions.fallback),
    toolPolicyJson: prettyOptionalJson(stripTradeAgentToolPolicy(profile.toolPolicyJson)),
    runtimeOptionsJson: prettyOptionalJson(stripTradeAgentRuntimeOptions(profile.runtimeOptionsJson)),
    remark: trimValue(profile.remark)
  }
}

/**
 * 构建智能代理配置提交数据
 * @param {Object} form - 表单数据
 * @returns {Object} 提交数据对象
 */
export function buildTradeAgentProfilePayload(form = {}) {
  return {
    id: form.id,
    agentCode: trimValue(form.agentCode).toLowerCase(),
    agentName: trimValue(form.agentName),
    agentType: trimValue(form.agentType).toUpperCase(),
    enabled: Boolean(form.enabled),
    llmEnabled: Boolean(form.llmEnabled),
    dialogueEnabled: Boolean(form.dialogueEnabled),
    maxDialogueRounds: parseOptionalNumber(form.dialogueEnabled ? form.maxDialogueRounds : 0) ?? 0,
    speakOrder: parseOptionalNumber(form.speakOrder) ?? 100,
    timeoutSeconds: parseOptionalNumber(form.timeoutSeconds) ?? 30,
    maxRetries: parseOptionalNumber(form.maxRetries) ?? 1,
    temperatureOverride: parseOptionalNumber(form.temperatureOverride),
    topPOverride: parseOptionalNumber(form.topPOverride),
    maxTokensOverride: parseOptionalNumber(form.maxTokensOverride),
    structuredSchemaCode: trimValue(form.structuredSchemaCode),
    defaultModelId: form.defaultModelId ?? null,
    defaultTemplateCode: trimValue(form.defaultTemplateCode) || null,
    defaultFallbackTemplateCode: trimValue(form.defaultFallbackTemplateCode) || null,
    defaultOutputSchemaCode: trimValue(form.defaultOutputSchemaCode) || trimValue(form.structuredSchemaCode),
    toolPolicyJson: JSON.stringify(buildTradeAgentToolPolicy(form)),
    runtimeOptionsJson: JSON.stringify(buildTradeAgentRuntimeOptions(form)),
    remark: trimValue(form.remark) || null
  }
}

/**
 * 验证智能代理配置提交数据
 * @param {Object} form - 表单数据
 * @returns {Object} 验证通过后的提交数据
 * @throws {Error} 验证失败时抛出错误
 */
export function validateTradeAgentProfilePayload(form = {}) {
  const payload = buildTradeAgentProfilePayload(form)
  if (!payload.agentCode) {
    throw new Error('代理编码不能为空')
  }
  if (!tradeAgentCodeOptions.includes(payload.agentCode)) {
    throw new Error(`不支持的代理编码: ${payload.agentCode}`)
  }
  if (!payload.agentName) {
    throw new Error('代理名称不能为空')
  }
  if (!tradeAgentTypeOptions.includes(payload.agentType)) {
    throw new Error(`不支持的代理类型: ${payload.agentType}`)
  }
  if (!payload.structuredSchemaCode) {
    throw new Error('结构模式不能为空')
  }
  if (payload.llmEnabled) {
    if (payload.defaultModelId == null) {
      throw new Error('启用 LLM 时默认模型不能为空')
    }
    if (!payload.defaultTemplateCode) {
      throw new Error('启用 LLM 时默认模板不能为空')
    }
  }
  if (payload.agentCode === 'supervisor_agent' && payload.defaultOutputSchemaCode !== 'supervisor_decision_v1') {
    throw new Error('主管代理默认输出模式必须为 supervisor_decision_v1')
  }
  if (['market_agent', 'news_agent', 'onchain_agent', 'social_agent'].includes(payload.agentCode) && payload.defaultOutputSchemaCode !== 'agent_view_v1') {
    throw new Error('专家代理默认输出模式必须为 agent_view_v1')
  }
  try {
    stringifyJson(form.toolPolicyJson)
    stringifyJson(form.runtimeOptionsJson)
  } catch {
    throw new Error('工具策略 JSON 和运行选项 JSON 必须是合法对象')
  }
  if (payload.agentType === 'RULE' && payload.llmEnabled) {
    throw new Error('规则型代理不支持启用 LLM')
  }
  if (payload.dialogueEnabled && (payload.maxDialogueRounds < 0 || payload.maxDialogueRounds > 2)) {
    throw new Error('对话轮数超出当前系统允许范围')
  }
  if (payload.timeoutSeconds < 1) {
    throw new Error('超时秒数必须大于 0')
  }
  return payload
}
</script>

<script setup>
/**
 * 智能代理配置页面组合式API
 * 提供代理配置列表加载、新增、编辑、删除等功能
 */

import { computed, getCurrentInstance, reactive, ref } from 'vue'

import { addTradeAgentProfile, delTradeAgentProfile, listTradeAgentProfile, updateTradeAgentProfile } from '@/api/dca/tradeAgentProfile'
import { listAiModel } from '@/api/dca/ai'
import { listTemplate } from '@/api/dca/template'
import TradeAdvancedJsonEditor from '@/components/trade/TradeAdvancedJsonEditor.vue'
import TradeEditableTags from '@/components/trade/TradeEditableTags.vue'
import TradeFormSection from '@/components/trade/TradeFormSection.vue'
import { formatTradeLabel } from '@/utils/tradeLabels'

const { proxy } = getCurrentInstance()

/** 加载状态 */
const loading = ref(false)
/** 提交状态 */
const submitting = ref(false)
/** 弹窗显示状态 */
const open = ref(false)
/** 弹窗标题 */
const title = ref('添加智能代理')
/** 表单引用 */
const profileRef = ref()
/** 代理配置列表数据 */
const profileList = ref([])
/** 总记录数 */
const total = ref(0)
/** 模板选项列表 */
const templateOptions = ref([])
/** 模型选项列表 */
const modelOptions = ref([])
/** 当前选中的代理ID */
const currentProfileId = ref(null)
/** 查询参数 */
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  agentType: '',
  enabled: ''
})
/** 表单数据 */
const form = reactive(createTradeAgentProfileForm({
  agentType: 'RULE',
  enabled: true,
  llmEnabled: false,
  dialogueEnabled: false,
  maxDialogueRounds: 0
}))
/** 表单验证规则 */
const rules = {
  agentCode: [{ required: true, message: '代理编码不能为空', trigger: 'change' }],
  agentName: [{ required: true, message: '代理名称不能为空', trigger: 'blur' }],
  agentType: [{ required: true, message: '代理类型不能为空', trigger: 'change' }],
  structuredSchemaCode: [{ required: true, message: '结构模式不能为空', trigger: 'change' }]
}

/**
 * 根据ID查找模型
 * @param {number|string} id - 模型ID
 * @returns {Object|null} 模型对象或null
 */
function findModelById(id) {
  if (id == null || id === '') {
    return null
  }
  return modelOptions.value.find((item) => String(item.id) === String(id)) || null
}

/**
 * 获取模型显示标签
 * @param {number|string} id - 模型ID
 * @returns {string} 模型标签文本
 */
function modelLabel(id) {
  const model = findModelById(id)
  if (!model) {
    return id == null || id === '' ? '--' : `#${id}`
  }
  return model.modelName || model.name || model.modelCode || `#${model.id}`
}

/**
 * 加载引用选项（模板和模型）
 */
async function loadReferenceOptions() {
  const [templateResponse, modelResponse] = await Promise.all([
    listTemplate({ pageNum: 1, pageSize: 200 }),
    listAiModel({ pageNum: 1, pageSize: 200 })
  ])
  templateOptions.value = (templateResponse?.rows || []).filter((item) => Number(item.isActive ?? 1) === 1)
  modelOptions.value = (modelResponse?.rows || []).filter((item) => Number(item.isEnabled ?? item.enabled ?? 1) === 1)
}

/** 当前选中的代理配置计算属性 */
const selectedProfile = computed(() => profileList.value.find((item) => item.id === currentProfileId.value) || null)
/** 预览代理配置计算属性 */
const previewProfile = computed(() => (open.value ? form : (selectedProfile.value || profileList.value[0] || null)))
/** 预览能力标签计算属性 */
const previewCapabilityTags = computed(() => {
  const profile = previewProfile.value
  if (!profile) {
    return []
  }
  return [
    profile.enabled === false ? '已禁用' : '已启用',
    profile.llmEnabled ? 'LLM 已开启' : 'LLM 已关闭',
    profile.dialogueEnabled ? `对话 ${profile.maxDialogueRounds || 0} 轮` : '对话已关闭'
  ]
})
/** 预览工具策略文本计算属性 */
const previewToolPolicyText = computed(() => (previewProfile.value ? prettyJson(buildTradeAgentToolPolicy(previewProfile.value)) : '--'))
/** 预览运行选项文本计算属性 */
const previewRuntimeOptionsText = computed(() => (previewProfile.value ? prettyJson(buildTradeAgentRuntimeOptions(previewProfile.value)) : '--'))

/**
 * 重置表单
 * @param {Object} profile - 代理配置数据
 */
function resetForm(profile = {}) {
  Object.assign(form, createTradeAgentProfileForm({
    agentType: 'RULE',
    enabled: true,
    llmEnabled: false,
    dialogueEnabled: false,
    maxDialogueRounds: 0,
    ...profile
  }))
  profileRef.value?.clearValidate()
}

/**
 * 处理表格行选中变化
 * @param {Object} row - 选中的行数据
 */
function handleCurrentChange(row) {
  currentProfileId.value = row?.id ?? null
}

/**
 * 处理查询操作
 */
function handleQuery() {
  queryParams.pageNum = 1
  getList()
}

/**
 * 加载代理配置列表
 */
async function getList() {
  loading.value = true
  try {
    const response = await listTradeAgentProfile({
      ...queryParams
    })
    profileList.value = response?.rows || []
    total.value = response?.total || profileList.value.length
    const stillExists = profileList.value.some((item) => item.id === currentProfileId.value)
    currentProfileId.value = stillExists ? currentProfileId.value : (profileList.value[0]?.id ?? null)
  } finally {
    loading.value = false
  }
}

/**
 * 处理新增代理配置操作
 */
function handleAdd() {
  resetForm()
  title.value = '添加智能代理'
  open.value = true
}

/**
 * 处理编辑代理配置操作
 * @param {Object} row - 要编辑的代理配置数据
 */
function handleUpdate(row) {
  resetForm(row)
  title.value = '修改智能代理'
  open.value = true
}

/**
 * 提交表单
 */
async function submitForm() {
  await profileRef.value?.validate()
  submitting.value = true
  try {
    const payload = validateTradeAgentProfilePayload(form)
    if (payload.id) {
      await updateTradeAgentProfile(payload)
      proxy?.$modal?.msgSuccess?.('代理配置已更新')
    } else {
      await addTradeAgentProfile(payload)
      proxy?.$modal?.msgSuccess?.('代理配置已新增')
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

/**
 * 处理删除代理配置操作
 * @param {Object} row - 要删除的代理配置数据
 */
async function handleDelete(row) {
  try {
    await proxy?.$modal?.confirm?.(`确认删除代理配置”${row.agentName}”吗？`)
    await delTradeAgentProfile(row.id)
    proxy?.$modal?.msgSuccess?.('代理配置已删除')
    await getList()
  } catch (error) {
    // ignore when cancelled
  }
}

// 初始化加载引用选项和列表
loadReferenceOptions()
getList()
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

.detail-card__header {
  font-weight: 600;
}

.preview-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.preview-content {
  margin: 0;
  padding: 12px;
  min-height: 160px;
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
