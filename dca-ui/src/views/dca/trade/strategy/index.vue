<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>交易策略</span>
          <div class="card-header__actions">
            <el-button type="primary" v-hasPermi="['dca:tradeStrategy:add']" @click="handleAdd">添加策略</el-button>
            <el-button plain @click="getList">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="strategyList" empty-text="暂无策略">
        <el-table-column label="键" prop="strategyKey" min-width="180" />
        <el-table-column label="名称" prop="strategyName" min-width="200" />
        <el-table-column label="模式" width="120">
          <template #default="scope">
            <el-tag :type="formatModeTag(scope.row.runtimeMode)">
              {{ formatModeLabel(scope.row.runtimeMode) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="交易对" min-width="180">
          <template #default="scope">
            <el-space wrap>
              <el-tag v-for="symbol in parseJsonArray(scope.row.symbolsJson)" :key="symbol" effect="plain">
                {{ symbol }}
              </el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="交易所" min-width="180">
          <template #default="scope">
            <el-space wrap>
              <el-tag
                v-for="exchange in parseJsonArray(scope.row.exchangesJson)"
                :key="exchange"
                type="success"
                effect="plain"
              >
                {{ exchange }}
              </el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.enabled ? 'success' : 'info'">
              {{ scope.row.enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="scope">
            <el-button
              link
              type="info"
              v-hasPermi="['dca:tradeStrategy:query']"
              @click="handleVersions(scope.row)"
            >
              版本
            </el-button>
            <el-button
              link
              type="warning"
              v-hasPermi="['dca:tradeStrategy:edit']"
              @click="handleBindings(scope.row)"
            >
              绑定
            </el-button>
            <el-button
              link
              type="primary"
              v-hasPermi="['dca:tradeStrategy:edit']"
              @click="handleUpdate(scope.row)"
            >
              编辑
            </el-button>
            <el-button
              link
              type="danger"
              v-hasPermi="['dca:tradeStrategy:remove']"
              @click="handleDelete(scope.row)"
            >
              删除
            </el-button>
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
    </el-card>

    <el-dialog v-model="open" :title="title" width="560px" append-to-body>
      <el-form ref="strategyRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="策略键" prop="strategyKey">
          <el-input v-model="form.strategyKey" placeholder="btc-breakout" :disabled="Boolean(form.id)" />
        </el-form-item>
        <el-form-item label="策略名称" prop="strategyName">
          <el-input v-model="form.strategyName" placeholder="BTC 突破策略" />
        </el-form-item>
        <el-form-item label="运行模式" prop="runtimeMode">
          <el-select v-model="form.runtimeMode" placeholder="选择模式" style="width: 100%">
            <el-option
              v-for="option in runtimeModeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="交易对" prop="symbols">
          <TradeEditableTags
            v-model="form.symbols"
            :options="tradeSymbolOptions"
            placeholder="输入或选择交易对"
          />
        </el-form-item>
        <el-form-item label="交易所" prop="exchanges">
          <TradeEditableTags
            v-model="form.exchanges"
            :options="tradeExchangeOptions"
            placeholder="输入或选择交易所"
          />
        </el-form-item>
        <el-form-item label="已启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <div class="strategy-config-panel">
          <div class="strategy-config-panel__title">结构化策略配置</div>
          <div class="strategy-config-grid">
            <el-form-item label="行情配置 ID">
              <el-input-number v-model="form.marketDataConfigId" :min="1" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="触发策略">
              <el-select v-model="form.triggerPolicyMode" placeholder="继承运行时" style="width: 100%">
                <el-option
                  v-for="option in strategyPolicyModeOptions"
                  :key="option.value || 'inherit'"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="监督策略">
              <el-select v-model="form.supervisorPolicyMode" placeholder="继承运行时" style="width: 100%">
                <el-option
                  v-for="option in strategyPolicyModeOptions"
                  :key="`supervisor-${option.value || 'inherit'}`"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="威科夫覆盖">
              <el-switch v-model="form.wyckoffOverrideEnabled" />
            </el-form-item>
            <el-form-item label="要求回踩">
              <el-switch v-model="form.wyckoffRequireRetestForReady" :disabled="!form.wyckoffOverrideEnabled" />
            </el-form-item>
            <el-form-item label="最大追价 %">
              <el-input-number v-model="form.wyckoffMaxReadyExtensionPct" :min="0" :step="0.1" :disabled="!form.wyckoffOverrideEnabled" style="width: 100%" />
            </el-form-item>
            <el-form-item label="诱多空量比">
              <el-input-number v-model="form.wyckoffTrapVolumeRatio" :min="0" :step="0.1" :disabled="!form.wyckoffOverrideEnabled" style="width: 100%" />
            </el-form-item>
            <el-form-item label="影线比例">
              <el-input-number v-model="form.wyckoffTrapWickRatio" :min="0" :max="1" :step="0.05" :disabled="!form.wyckoffOverrideEnabled" style="width: 100%" />
            </el-form-item>
            <el-form-item label="诱骗冷却K线">
              <el-input-number v-model="form.wyckoffTrapCooldownBars" :min="0" :step="1" :disabled="!form.wyckoffOverrideEnabled" style="width: 100%" />
            </el-form-item>
            <el-form-item label="最大仓位占比">
              <el-input-number v-model="form.riskMaxPositionRatio" :min="0" :max="1" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="最大日亏损">
              <el-input-number v-model="form.riskMaxDailyLoss" :step="50" style="width: 100%" />
            </el-form-item>
            <el-form-item label="最大连续失败">
              <el-input-number v-model="form.riskMaxConsecutiveFailures" :min="0" :step="1" style="width: 100%" />
            </el-form-item>
          </div>
        </div>
        <el-form-item label="高级配置" prop="configJson">
          <TradeAdvancedJsonEditor
            v-model="form.configJson"
            title="高级 JSON 配置"
            description="这里保留结构化表单未覆盖的高级字段。留空时只提交上面的结构化配置。"
            placeholder='{"specialistRouting":{"market_agent":["market"]}}'
            :rows="8"
          />
          <div class="form-tip">
            在此存储策略范围内未结构化暴露的数据源、路由与信号覆盖。此 JSON 在
            <code>trade_strategy_version.config_json</code>中进行版本控制。
          </div>
          <div class="form-tip">
            触发策略: {{ strategyConfigSummary.triggerPolicyMode }} |
            监督: {{ strategyConfigSummary.supervisorPolicyMode }} |
            威科夫: {{ strategyConfigSummary.wyckoffShorttermEnabled ? '覆盖' : '继承' }} |
            路由: {{ strategyConfigSummary.specialistRouting.join(', ') || '继承' }} |
            信号记忆覆盖: {{ strategyConfigSummary.signalMemoryOverrides.join(', ') || '无' }} |
            触发矩阵覆盖: {{ strategyConfigSummary.triggerMatrixOverridesCount }}
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="open = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="versionOpen" title="策略版本" width="760px" append-to-body>
      <div class="version-layout" v-loading="versionLoading">
        <el-table
          class="version-layout__table"
          :data="versionList"
          highlight-current-row
          empty-text="暂无版本"
          @current-change="handleVersionChange"
        >
          <el-table-column label="版本" prop="versionNo" width="100" />
          <el-table-column label="创建时间" prop="createdAt" min-width="180" />
        </el-table>
        <div class="version-layout__detail">
          <div class="version-layout__header">
            {{ activeVersion ? `版本 ${activeVersion.versionNo}` : '配置快照' }}
          </div>
          <pre class="version-layout__content">{{ activeVersionConfig }}</pre>
          <div class="version-layout__meta">
            触发策略: {{ activeVersionSummary.triggerPolicyMode }} |
            监督: {{ activeVersionSummary.supervisorPolicyMode }} |
            威科夫: {{ activeVersionSummary.wyckoffShorttermEnabled ? '覆盖' : '继承' }} |
            路由: {{ activeVersionSummary.specialistRouting.join(', ') || '继承' }} |
            信号记忆覆盖: {{ activeVersionSummary.signalMemoryOverrides.join(', ') || '无' }} |
            触发矩阵覆盖: {{ activeVersionSummary.triggerMatrixOverridesCount }}
          </div>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="bindingOpen" :title="bindingTitle" width="760px" append-to-body>
      <div class="binding-layout" v-loading="bindingLoading">
        <div class="binding-layout__summary">
          <div class="binding-layout__title">
            {{ bindingStrategy?.strategyName || bindingStrategy?.strategyKey || '策略' }}
          </div>
          <div class="binding-layout__subtitle">
            交易所: {{ parseJsonArray(bindingStrategy?.exchangesJson).join(', ') || '无' }}
          </div>
        </div>
        <el-table :data="bindingRows" empty-text="所选交易所无可用账户">
          <el-table-column label="交易所" prop="exchangeCode" width="140" />
          <el-table-column label="账户" prop="accountName" min-width="220" />
          <el-table-column label="账户状态" width="160">
            <template #default="scope">
              <el-tag :type="scope.row.accountEnabled ? 'success' : 'info'">
                {{ scope.row.accountEnabled ? '已启用' : '已禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="绑定" width="120">
            <template #default="scope">
              <el-switch v-model="scope.row.bindingEnabled" :disabled="!scope.row.accountEnabled" />
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="bindingOpen = false">取消</el-button>
          <el-button type="primary" :loading="bindingSubmitting" @click="submitBindings">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
/**
 * 交易策略页面脚本模块
 * 提供策略表单创建、数据转换、绑定行生成等工具函数
 */

/**
 * 标准化运行模式
 * @param {string} mode - 运行模式
 * @returns {string} 标准化后的模式字符串
 */
function normalizeMode(mode) {
  return String(mode || 'paper').trim().toLowerCase()
}

function parseOptionalNumber(value) {
  if (value == null || value === '') {
    return null
  }
  const parsed = Number(value)
  return Number.isNaN(parsed) ? null : parsed
}

/**
 * 解析JSON数组
 * @param {*} value - 待解析的值
 * @returns {Array} 解析后的数组
 */
export function parseJsonArray(value) {
  if (!value) {
    return []
  }
  if (Array.isArray(value)) {
    return value
  }
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : []
  } catch (error) {
    return []
  }
}

/**
 * 标准化范围行
 * @param {string} value - 输入值
 * @param {Function} transform - 转换函数
 * @returns {Array} 标准化后的数组
 */
function normalizeScopeLines(value, transform = (item) => item) {
  return Array.from(
    new Set(
      String(value || '')
        .split(/[\n,]/)
        .map((item) => transform(item.trim()))
        .filter(Boolean)
    )
  )
}

function normalizeScopeItems(values = [], transform = (item) => item) {
  return Array.from(
    new Set(
      (Array.isArray(values) ? values : [])
        .map((item) => transform(String(item || '').trim()))
        .filter(Boolean)
    )
  )
}

/**
 * 创建交易策略表单
 * @param {Object} strategy - 策略数据
 * @returns {Object} 表单对象
 */
export function createTradeStrategyForm(strategy = {}) {
  const strategyConfig = parseObjectJson(strategy.configJson)
  const riskConfig = parseObjectJson(strategyConfig.riskConfig)
  const triggerPolicy = parseObjectJson(strategyConfig.triggerPolicy)
  const wyckoffShortterm = parseObjectJson(triggerPolicy.wyckoffShortterm)
  const supervisorPolicy = parseObjectJson(strategyConfig.supervisorPolicy)
  return {
    id: strategy.id,
    strategyKey: String(strategy.strategyKey || ''),
    strategyName: String(strategy.strategyName || ''),
    runtimeMode: normalizeMode(strategy.runtimeMode),
    symbols: normalizeScopeItems(parseJsonArray(strategy.symbolsJson), (item) => item.toUpperCase()),
    exchanges: normalizeScopeItems(parseJsonArray(strategy.exchangesJson), (item) => item.toUpperCase()),
    marketDataConfigId: parseOptionalNumber(strategyConfig.marketDataConfigId),
    riskMaxPositionRatio: parseOptionalNumber(riskConfig.maxPositionRatio),
    riskMaxDailyLoss: parseOptionalNumber(riskConfig.maxDailyLoss),
    riskMaxConsecutiveFailures: parseOptionalNumber(riskConfig.maxConsecutiveFailures),
    triggerPolicyMode: String(triggerPolicy.mode || triggerPolicy.dispatchMode || '').trim(),
    wyckoffOverrideEnabled: Object.keys(wyckoffShortterm).length > 0,
    wyckoffRequireRetestForReady: wyckoffShortterm.requireRetestForReady !== false,
    wyckoffMaxReadyExtensionPct: parseOptionalNumber(wyckoffShortterm.maxReadyExtensionPct),
    wyckoffTrapVolumeRatio: parseOptionalNumber(wyckoffShortterm.trapVolumeRatio),
    wyckoffTrapWickRatio: parseOptionalNumber(wyckoffShortterm.trapWickRatio),
    wyckoffTrapCooldownBars: parseOptionalNumber(wyckoffShortterm.trapCooldownBars),
    supervisorPolicyMode: resolveSupervisorPolicyMode(supervisorPolicy),
    configJson: extractCustomStrategyConfig(strategy.configJson),
    enabled: strategy.enabled !== false
  }
}

/**
 * 构建交易策略提交数据
 * @param {Object} form - 表单数据
 * @returns {Object} 提交数据对象
 */
export function buildTradeStrategyPayload(form = {}) {
  return {
    id: form.id,
    strategyKey: String(form.strategyKey || '').trim(),
    strategyName: String(form.strategyName || '').trim(),
    runtimeMode: normalizeMode(form.runtimeMode),
    symbolsJson: JSON.stringify(normalizeScopeItems(form.symbols, (item) => item.toUpperCase())),
    exchangesJson: JSON.stringify(normalizeScopeItems(form.exchanges, (item) => item.toUpperCase())),
    configJson: normalizeStrategyConfigJson(form.configJson, form),
    enabled: Boolean(form.enabled)
  }
}

/**
 * 创建策略账户绑定行数据
 * @param {Object} strategy - 策略数据
 * @param {Array} accounts - 账户列表
 * @param {Array} bindings - 绑定列表
 * @returns {Array} 绑定行数据
 */
export function createTradeStrategyBindingRows(strategy = {}, accounts = [], bindings = []) {
  const allowedExchanges = new Set(
    parseJsonArray(strategy.exchangesJson).map((item) => String(item || '').trim().toUpperCase()).filter(Boolean)
  )
  const bindingMap = new Map(
    (Array.isArray(bindings) ? bindings : []).map((binding) => [
      `${String(binding.exchangeCode || '').trim().toUpperCase()}::${binding.accountId}`,
      binding
    ])
  )

  return (Array.isArray(accounts) ? accounts : [])
    .filter((account) => {
      const exchangeCode = String(account.exchangeCode || '').trim().toUpperCase()
      return allowedExchanges.size === 0 || allowedExchanges.has(exchangeCode)
    })
    .map((account) => {
      const exchangeCode = String(account.exchangeCode || '').trim().toUpperCase()
      const existingBinding = bindingMap.get(`${exchangeCode}::${account.id}`)
      return {
        accountId: account.id,
        exchangeCode,
        accountName: String(account.accountName || ''),
        accountEnabled: account.enabled !== false,
        bindingEnabled: existingBinding ? existingBinding.enabled !== false : false
      }
    })
}

/**
 * 构建策略绑定提交数据
 * @param {Array} rows - 绑定行数据
 * @returns {Array} 提交数据
 */
export function buildTradeStrategyBindingsPayload(rows = []) {
  return (Array.isArray(rows) ? rows : [])
    .filter((row) => row?.bindingEnabled)
    .map((row) => ({
      accountId: row.accountId,
      exchangeCode: String(row.exchangeCode || '').trim().toUpperCase(),
      enabled: true
    }))
}

/**
 * 格式化版本配置
 * @param {*} configJson - 配置JSON
 * @returns {string} 格式化后的JSON字符串
 */
export function formatVersionConfig(configJson) {
  if (!configJson) {
    return '{}'
  }
  if (typeof configJson === 'string') {
    try {
      return JSON.stringify(JSON.parse(configJson), null, 2)
    } catch (error) {
      return configJson
    }
  }
  return JSON.stringify(configJson, null, 2)
}

/** 策略快照基础字段集合 */
const STRATEGY_SNAPSHOT_BASE_KEYS = new Set([
  'strategyKey',
  'strategyName',
  'runtimeMode',
  'symbolsJson',
  'exchangesJson',
  'enabled'
])

/**
 * 解析对象JSON
 * @param {*} value - 待解析的值
 * @returns {Object} 解析后的对象
 */
function parseObjectJson(value) {
  if (!value) {
    return {}
  }
  if (typeof value === 'object' && !Array.isArray(value)) {
    return value
  }
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch (error) {
    return {}
  }
}

function cloneConfigObject(value) {
  return JSON.parse(JSON.stringify(parseObjectJson(value)))
}

function cleanupEmptyObject(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return value
  }
  Object.keys(value).forEach((key) => {
    const nested = value[key]
    if (nested && typeof nested === 'object' && !Array.isArray(nested)) {
      cleanupEmptyObject(nested)
      if (Object.keys(nested).length === 0) {
        delete value[key]
      }
    }
  })
  return value
}

function resolveSupervisorPolicyMode(value) {
  const supervisorPolicy = parseObjectJson(value)
  return String(
    supervisorPolicy.enabledWhen
    || supervisorPolicy.enabled_when
    || supervisorPolicy.mode
    || ''
  ).trim()
}

function stripStructuredStrategyConfig(value) {
  const parsed = cloneConfigObject(value)
  delete parsed.aiModelId
  delete parsed.marketDataConfigId

  const riskConfig = parseObjectJson(parsed.riskConfig)
  delete riskConfig.maxPositionRatio
  delete riskConfig.maxDailyLoss
  delete riskConfig.maxConsecutiveFailures
  if (Object.keys(riskConfig).length) {
    parsed.riskConfig = riskConfig
  } else {
    delete parsed.riskConfig
  }

  const triggerPolicy = parseObjectJson(parsed.triggerPolicy)
  delete triggerPolicy.mode
  delete triggerPolicy.dispatchMode
  const wyckoffShortterm = parseObjectJson(triggerPolicy.wyckoffShortterm)
  delete wyckoffShortterm.requireRetestForReady
  delete wyckoffShortterm.maxReadyExtensionPct
  delete wyckoffShortterm.trapVolumeRatio
  delete wyckoffShortterm.trapWickRatio
  delete wyckoffShortterm.trapCooldownBars
  if (Object.keys(wyckoffShortterm).length) {
    triggerPolicy.wyckoffShortterm = wyckoffShortterm
  } else {
    delete triggerPolicy.wyckoffShortterm
  }
  if (Object.keys(triggerPolicy).length) {
    parsed.triggerPolicy = triggerPolicy
  } else {
    delete parsed.triggerPolicy
  }

  const supervisorPolicy = parseObjectJson(parsed.supervisorPolicy)
  delete supervisorPolicy.mode
  delete supervisorPolicy.enabledWhen
  delete supervisorPolicy.enabled_when
  if (Object.keys(supervisorPolicy).length) {
    parsed.supervisorPolicy = supervisorPolicy
  } else {
    delete parsed.supervisorPolicy
  }
  return cleanupEmptyObject(parsed)
}

/**
 * 提取自定义策略配置
 * @param {*} value - 配置值
 * @returns {string} 自定义配置JSON字符串
 */
function extractCustomStrategyConfig(value) {
  const parsed = stripStructuredStrategyConfig(value)
  const customEntries = Object.entries(parsed).filter(([key]) => !STRATEGY_SNAPSHOT_BASE_KEYS.has(key))
  if (customEntries.length === 0) {
    return ''
  }
  return JSON.stringify(Object.fromEntries(customEntries), null, 2)
}

/**
 * 标准化策略配置JSON
 * @param {*} value - 配置值
 * @returns {string} 标准化后的JSON字符串
 */
function buildStructuredStrategyConfig(value, form = {}) {
  const parsed = cloneConfigObject(value)
  delete parsed.aiModelId
  const marketDataConfigId = parseOptionalNumber(form.marketDataConfigId)
  if (marketDataConfigId != null) {
    parsed.marketDataConfigId = marketDataConfigId
  } else {
    delete parsed.marketDataConfigId
  }

  const riskConfig = parseObjectJson(parsed.riskConfig)
  const riskMaxPositionRatio = parseOptionalNumber(form.riskMaxPositionRatio)
  const riskMaxDailyLoss = parseOptionalNumber(form.riskMaxDailyLoss)
  const riskMaxConsecutiveFailures = parseOptionalNumber(form.riskMaxConsecutiveFailures)
  if (riskMaxPositionRatio != null) {
    riskConfig.maxPositionRatio = riskMaxPositionRatio
  } else {
    delete riskConfig.maxPositionRatio
  }
  if (riskMaxDailyLoss != null) {
    riskConfig.maxDailyLoss = riskMaxDailyLoss
  } else {
    delete riskConfig.maxDailyLoss
  }
  if (riskMaxConsecutiveFailures != null) {
    riskConfig.maxConsecutiveFailures = riskMaxConsecutiveFailures
  } else {
    delete riskConfig.maxConsecutiveFailures
  }
  if (Object.keys(riskConfig).length) {
    parsed.riskConfig = riskConfig
  } else {
    delete parsed.riskConfig
  }

  const triggerPolicy = parseObjectJson(parsed.triggerPolicy)
  if (String(form.triggerPolicyMode || '').trim()) {
    triggerPolicy.mode = String(form.triggerPolicyMode || '').trim()
    delete triggerPolicy.dispatchMode
  } else {
    delete triggerPolicy.mode
    delete triggerPolicy.dispatchMode
  }
  if (form.wyckoffOverrideEnabled) {
    const wyckoffShortterm = parseObjectJson(triggerPolicy.wyckoffShortterm)
    wyckoffShortterm.requireRetestForReady = form.wyckoffRequireRetestForReady !== false
    const maxReadyExtensionPct = parseOptionalNumber(form.wyckoffMaxReadyExtensionPct)
    const trapVolumeRatio = parseOptionalNumber(form.wyckoffTrapVolumeRatio)
    const trapWickRatio = parseOptionalNumber(form.wyckoffTrapWickRatio)
    const trapCooldownBars = parseOptionalNumber(form.wyckoffTrapCooldownBars)
    if (maxReadyExtensionPct != null) {
      wyckoffShortterm.maxReadyExtensionPct = maxReadyExtensionPct
    } else {
      delete wyckoffShortterm.maxReadyExtensionPct
    }
    if (trapVolumeRatio != null) {
      wyckoffShortterm.trapVolumeRatio = trapVolumeRatio
    } else {
      delete wyckoffShortterm.trapVolumeRatio
    }
    if (trapWickRatio != null) {
      wyckoffShortterm.trapWickRatio = trapWickRatio
    } else {
      delete wyckoffShortterm.trapWickRatio
    }
    if (trapCooldownBars != null) {
      wyckoffShortterm.trapCooldownBars = trapCooldownBars
    } else {
      delete wyckoffShortterm.trapCooldownBars
    }
    triggerPolicy.wyckoffShortterm = wyckoffShortterm
  } else {
    delete triggerPolicy.wyckoffShortterm
  }
  if (Object.keys(triggerPolicy).length) {
    parsed.triggerPolicy = triggerPolicy
  } else {
    delete parsed.triggerPolicy
  }

  const supervisorPolicy = parseObjectJson(parsed.supervisorPolicy)
  if (String(form.supervisorPolicyMode || '').trim()) {
    supervisorPolicy.enabledWhen = String(form.supervisorPolicyMode || '').trim()
    delete supervisorPolicy.mode
    delete supervisorPolicy.enabled_when
  } else {
    delete supervisorPolicy.mode
    delete supervisorPolicy.enabledWhen
    delete supervisorPolicy.enabled_when
  }
  if (Object.keys(supervisorPolicy).length) {
    parsed.supervisorPolicy = supervisorPolicy
  } else {
    delete parsed.supervisorPolicy
  }
  return cleanupEmptyObject(parsed)
}

function normalizeStrategyConfigJson(value, form = {}) {
  const normalized = String(value || '').trim()
  if (!normalized) {
    const merged = buildStructuredStrategyConfig({}, form)
    return Object.keys(merged).length ? JSON.stringify(merged) : ''
  }
  const parsed = parseObjectJson(normalized)
  const merged = buildStructuredStrategyConfig(
    Object.keys(parsed).length === 0 && normalized !== '{}' ? {} : parsed,
    form
  )
  if (Object.keys(parsed).length === 0 && normalized !== '{}' && Object.keys(merged).length === 0) {
    return normalized
  }
  return Object.keys(merged).length ? JSON.stringify(merged) : ''
}

export function summarizeTradeStrategyConfig(value) {
  const parsed = parseObjectJson(value)
  const specialistRouting = Object.keys(parseObjectJson(parsed.specialistRouting))
  const signalMemoryOverrides = Object.keys(parseObjectJson(parsed.signalMemoryOverrides))
  const triggerMatrixOverrides = Array.isArray(parsed.triggerMatrixOverrides) ? parsed.triggerMatrixOverrides : []
  const wyckoffShortterm = parseObjectJson(parsed?.triggerPolicy?.wyckoffShortterm)
  return {
    triggerPolicyMode: String(parsed?.triggerPolicy?.mode || parsed?.triggerPolicy?.dispatchMode || 'inherit'),
    supervisorPolicyMode: resolveSupervisorPolicyMode(parsed?.supervisorPolicy) || 'inherit',
    wyckoffShorttermEnabled: Object.keys(wyckoffShortterm).length > 0,
    specialistRouting,
    signalMemoryOverrides,
    triggerMatrixOverridesCount: triggerMatrixOverrides.length
  }
}
</script>

<script setup>
/**
 * 交易策略页面组合式API
 * 提供策略管理、版本管理、账户绑定等功能
 */

import { computed, getCurrentInstance, reactive, ref } from 'vue'

import {
  addTradeStrategy,
  delTradeStrategy,
  listTradeStrategy,
  listTradeStrategyBindings,
  listTradeStrategyVersions,
  updateTradeStrategyBindings,
  updateTradeStrategy
} from '@/api/dca/tradeStrategy'
import { listExchangeAccount } from '@/api/dca/exchangeAccount'
import TradeAdvancedJsonEditor from '@/components/trade/TradeAdvancedJsonEditor.vue'
import TradeEditableTags from '@/components/trade/TradeEditableTags.vue'
import { formatModeLabel, formatModeTag } from '@/views/dca/trade/runtime/index.vue'

const { proxy } = getCurrentInstance()

/** 加载状态 */
const loading = ref(false)
/** 提交状态 */
const submitting = ref(false)
/** 弹窗显示状态 */
const open = ref(false)
/** 弹窗标题 */
const title = ref('Add Strategy')
/** 表单引用 */
const strategyRef = ref()
/** 策略列表 */
const strategyList = ref([])
const total = ref(0)
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10
})
/** 版本弹窗显示状态 */
const versionOpen = ref(false)
/** 版本加载状态 */
const versionLoading = ref(false)
/** 版本列表 */
const versionList = ref([])
/** 当前选中版本 */
const activeVersion = ref(null)
/** 绑定弹窗显示状态 */
const bindingOpen = ref(false)
/** 绑定加载状态 */
const bindingLoading = ref(false)
/** 绑定提交状态 */
const bindingSubmitting = ref(false)
/** 绑定行数据 */
const bindingRows = ref([])
/** 当前绑定策略 */
const bindingStrategy = ref(null)
/** 运行模式选项 */
const runtimeModeOptions = [
  { label: 'PAPER', value: 'paper' },
  { label: 'SHADOW', value: 'shadow' },
  { label: 'LIVE', value: 'live' }
]
const strategyPolicyModeOptions = [
  { label: '继承运行时', value: '' },
  { label: 'EVENT_GATED', value: 'EVENT_GATED' },
  { label: 'RULE_ONLY', value: 'RULE_ONLY' },
  { label: 'LLM_ALLOWED', value: 'LLM_ALLOWED' },
  { label: 'NO_DISPATCH', value: 'NO_DISPATCH' }
]
const tradeSymbolOptions = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
// 交易所选项从后端获取，此处保留默认值作为后备
const tradeExchangeOptions = ['BINANCE', 'OKX']
/** 表单数据 */
const form = reactive(createTradeStrategyForm())
/** 表单验证规则 */
const rules = {
  strategyKey: [{ required: true, message: '请输入策略编码', trigger: 'blur' }],
  strategyName: [{ required: true, message: '请输入策略名称', trigger: 'blur' }],
  runtimeMode: [{ required: true, message: '请选择运行模式', trigger: 'change' }],
  symbols: [{ required: true, message: '请至少选择一个交易对', trigger: 'change' }],
  exchanges: [{ required: true, message: '请至少选择一个交易所', trigger: 'change' }],
  configJson: [{
    validator: (_rule, value, callback) => {
      const normalized = String(value || '').trim()
      if (!normalized) {
        callback()
        return
      }
      try {
        const parsed = JSON.parse(normalized)
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
          callback(new Error('高级配置必须是 JSON 对象'))
          return
        }
        callback()
      } catch (error) {
        callback(new Error('高级配置必须是合法 JSON'))
      }
    },
    trigger: 'blur'
  }]
}
/** 当前版本配置计算属性 */
const activeVersionConfig = computed(() => formatVersionConfig(activeVersion.value?.configJson))
const activeVersionSummary = computed(() => summarizeTradeStrategyConfig(activeVersion.value?.configJson))
const strategyConfigSummary = computed(() => summarizeTradeStrategyConfig(buildStructuredStrategyConfig(form.configJson, form)))
/** 绑定弹窗标题计算属性 */
const bindingTitle = computed(() => {
  const strategyName = bindingStrategy.value?.strategyName || bindingStrategy.value?.strategyKey
  return strategyName ? `Account Bindings - ${strategyName}` : 'Account Bindings'
})

/**
 * 重置表单
 * @param {Object} strategy - 策略数据
 */
function resetForm(strategy = {}) {
  Object.assign(form, createTradeStrategyForm(strategy))
  strategyRef.value?.clearValidate()
}

/**
 * 获取策略列表
 */
async function getList() {
  loading.value = true
  try {
    const response = await listTradeStrategy({
      ...queryParams
    })
    strategyList.value = response?.rows || []
    total.value = response?.total || strategyList.value.length
  } finally {
    loading.value = false
  }
}

/**
 * 处理新增策略
 */
function handleAdd() {
  resetForm()
  title.value = 'Add Strategy'
  open.value = true
}

/**
 * 处理编辑策略
 * @param {Object} row - 策略行数据
 */
async function handleUpdate(row) {
  let latestConfigJson = ''
  if (row?.id) {
    try {
      const response = await listTradeStrategyVersions(row.id)
      const versions = response?.rows || response?.data || []
      latestConfigJson = versions[0]?.configJson || ''
    } catch (error) {
      proxy?.$modal?.msgWarning?.('Failed to load latest version config, continuing with base strategy fields only')
    }
  }
  resetForm({
    ...row,
    configJson: latestConfigJson
  })
  title.value = 'Edit Strategy'
  open.value = true
}

/**
 * 提交表单
 */
async function submitForm() {
  await strategyRef.value?.validate()
  submitting.value = true
  try {
    const payload = buildTradeStrategyPayload(form)
    if (payload.id) {
      await updateTradeStrategy(payload)
      proxy?.$modal?.msgSuccess?.('策略已更新')
    } else {
      await addTradeStrategy(payload)
      proxy?.$modal?.msgSuccess?.('策略已新增')
    }
    open.value = false
    await getList()
  } finally {
    submitting.value = false
  }
}

/**
 * 处理删除策略
 * @param {Object} row - 策略行数据
 */
async function handleDelete(row) {
  try {
    await proxy?.$modal?.confirm?.(`确认删除策略“${row.strategyName || row.strategyKey}”吗？`)
    await delTradeStrategy(row.id)
    proxy?.$modal?.msgSuccess?.('策略已删除')
    await getList()
  } catch (error) {
    // ignore when user cancels
  }
}

/**
 * 处理版本变更
 * @param {Object} row - 版本行数据
 */
function handleVersionChange(row) {
  activeVersion.value = row || null
}

/**
 * 处理查看版本
 * @param {Object} row - 策略行数据
 */
async function handleVersions(row) {
  versionOpen.value = true
  versionLoading.value = true
  activeVersion.value = null
  versionList.value = []
  try {
    const response = await listTradeStrategyVersions(row.id)
    versionList.value = response?.rows || response?.data || []
    activeVersion.value = versionList.value[0] || null
  } finally {
    versionLoading.value = false
  }
}

/**
 * 处理账户绑定
 * @param {Object} row - 策略行数据
 */
async function handleBindings(row) {
  bindingOpen.value = true
  bindingLoading.value = true
  bindingStrategy.value = row
  bindingRows.value = []
  try {
    const [accountResponse, bindingResponse] = await Promise.all([
      listExchangeAccount({
        pageNum: 1,
        pageSize: 200
      }),
      listTradeStrategyBindings(row.id)
    ])
    bindingRows.value = createTradeStrategyBindingRows(
      row,
      accountResponse?.rows || [],
      bindingResponse?.rows || bindingResponse?.data || []
    )
  } finally {
    bindingLoading.value = false
  }
}

/**
 * 提交账户绑定
 */
async function submitBindings() {
  if (!bindingStrategy.value?.id) {
    return
  }
  bindingSubmitting.value = true
  try {
    await updateTradeStrategyBindings(
      bindingStrategy.value.id,
      buildTradeStrategyBindingsPayload(bindingRows.value)
    )
    proxy?.$modal?.msgSuccess?.('绑定已更新')
    bindingOpen.value = false
  } finally {
    bindingSubmitting.value = false
  }
}

// 初始化加载列表
getList()
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header__actions {
  display: flex;
  gap: 8px;
}

.form-tip {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.strategy-config-panel {
  margin-bottom: 18px;
  padding: 16px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  background: #fcfdff;
}

.strategy-config-panel__title {
  margin-bottom: 12px;
  font-weight: 600;
}

.strategy-config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
}

.version-layout {
  display: grid;
  grid-template-columns: minmax(0, 280px) minmax(0, 1fr);
  gap: 16px;
  min-height: 320px;
}

.version-layout__table {
  min-width: 0;
}

.version-layout__detail {
  min-width: 0;
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  background: #f8fafc;
  overflow: hidden;
}

.version-layout__header {
  padding: 12px 14px;
  border-bottom: 1px solid var(--el-border-color-light);
  font-weight: 600;
}

.version-layout__content {
  margin: 0;
  padding: 14px;
  min-height: 260px;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: auto;
}

.version-layout__meta {
  padding: 0 14px 14px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.binding-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 240px;
}

.binding-layout__summary {
  padding: 14px 16px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  background: #f8fafc;
}

.binding-layout__title {
  font-weight: 600;
}

.binding-layout__subtitle {
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

@media (max-width: 768px) {
  .card-header {
    align-items: flex-start;
    gap: 12px;
    flex-direction: column;
  }

  .version-layout {
    grid-template-columns: 1fr;
  }

  .strategy-config-grid {
    grid-template-columns: 1fr;
  }
}
</style>
