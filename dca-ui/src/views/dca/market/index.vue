<template>
  <div class="app-container market-page">
    <el-alert
      :title="marketPageTitle"
      :description="compatibilityMessage"
      type="warning"
      show-icon
      :closable="false"
    />
    <div class="cutover-actions">
      <el-button
        v-for="item in legacyConsoleLinks"
        :key="item.path"
        :type="item.type"
        @click="goTo(item.path)"
      >
        {{ item.label }}
      </el-button>
    </div>
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="API配置" name="apis">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>市场API / WebSocket配置</span>
              <el-button type="primary" size="small" @click="handleAddApi">添加API</el-button>
            </div>
          </template>
          <div class="toolbar">
            <el-select v-model="apiFilter.category" clearable placeholder="分类" @change="handleApiQuery">
              <el-option label="PRICE" value="PRICE" />
              <el-option label="VOLUME" value="VOLUME" />
              <el-option label="KLINE" value="KLINE" />
              <el-option label="FEAR_GREED" value="FEAR_GREED" />
              <el-option label="ONCHAIN" value="ONCHAIN" />
              <el-option label="GAS" value="GAS" />
            </el-select>
            <el-select v-model="apiFilter.enabled" clearable placeholder="状态" @change="handleApiQuery">
              <el-option label="已启用" value="1" />
              <el-option label="已禁用" value="0" />
            </el-select>
          </div>
          <el-table :data="apiList" border>
            <el-table-column prop="configName" label="配置名称" min-width="180" />
            <el-table-column prop="dataCategory" label="分类" min-width="110" />
            <el-table-column prop="apiName" label="API名称" min-width="180" />
            <el-table-column prop="transportType" label="传输" width="110" />
            <el-table-column prop="vendorCode" label="厂商" width="110" />
            <el-table-column prop="endpointDisplay" label="端点" min-width="280" show-overflow-tooltip />
            <el-table-column prop="enabled" label="状态" width="100">
              <template #default="{ row }">
                <el-switch v-model="row.enabledValue" active-value="1" inactive-value="0" @change="handleToggleApi(row)" />
              </template>
            </el-table-column>
            <el-table-column prop="priority" label="优先级" width="90" />
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleEditApi(row)">编辑</el-button>
                <el-button link type="primary" @click="handleTestApi(row)">测试</el-button>
                <el-button link type="danger" @click="handleDeleteApi(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <pagination
            v-show="apiTotal > 0"
            :total="apiTotal"
            v-model:page="apiQuery.pageNum"
            v-model:limit="apiQuery.pageSize"
            @pagination="loadApiList"
          />
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="策略绑定" :name="marketBindingTabName">
        <SourceBindingPanel />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="apiDialogVisible" :title="apiDialogTitle" width="860px">
      <el-form ref="apiFormRef" :model="apiForm" :rules="apiRules" label-width="170px">
        <el-form-item label="配置名称" prop="configName"><el-input v-model="apiForm.configName" /></el-form-item>
        <el-form-item label="数据分类" prop="dataCategory">
          <el-select v-model="apiForm.dataCategory">
            <el-option label="PRICE" value="PRICE" />
            <el-option label="VOLUME" value="VOLUME" />
            <el-option label="KLINE" value="KLINE" />
            <el-option label="FEAR_GREED" value="FEAR_GREED" />
            <el-option label="ONCHAIN" value="ONCHAIN" />
            <el-option label="GAS" value="GAS" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据子类型"><el-input v-model="apiForm.dataSubType" placeholder="TICKER / TRADE / KLINE" /></el-form-item>
        <el-form-item label="API名称" prop="apiName"><el-input v-model="apiForm.apiName" /></el-form-item>
        <el-form-item label="传输">
          <el-radio-group v-model="apiForm.transportType">
            <el-radio label="REST">REST</el-radio>
            <el-radio label="WEBSOCKET">WebSocket</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="厂商">
          <el-select v-model="apiForm.vendorCode" clearable filterable allow-create>
            <el-option label="BINANCE" value="BINANCE" />
            <el-option label="OKX" value="OKX" />
          </el-select>
        </el-form-item>
        <el-form-item label="市场范围">
          <el-radio-group v-model="apiForm.marketScope">
            <el-radio label="SPOT">SPOT</el-radio>
            <el-radio label="FUTURES">FUTURES</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-alert v-if="isBinanceWebsocketApi()" type="warning" :closable="false" class="section-gap"
          title="Binance规则：小写交易对，/ws 或 /stream 路径，24小时TTL，最大1024个流，最大5个控制消息/秒。" />
        <el-alert v-if="isOkxWebsocketApi()" type="info" :closable="false" class="section-gap"
          title="OKX规则：公共频道使用 /ws/v5/public，通过 subscribe args JSON 配置 tickers、mark-price、funding-rate、open-interest、liquidation-orders。" />
        <template v-if="isWebsocketApi()">
          <el-form-item label="WS基础URL"><el-input v-model="apiForm.wsBaseUrl" /></el-form-item>
          <el-form-item label="WS路径"><el-input v-model="apiForm.wsPath" placeholder="Binance: /stream；OKX: /ws/v5/public" /></el-form-item>
          <el-form-item label="流模板">
            <el-input v-model="apiForm.wsStreamNameTemplate" placeholder="Binance: {symbol_lower}@ticker；OKX: {&quot;args&quot;:[...]}" />
            <div class="market-guide market-guide--inline">
              <div class="market-guide__title">流模板说明</div>
              <ul class="market-guide__list">
                <li v-for="item in marketWsTemplateGuideItems" :key="item">{{ item }}</li>
              </ul>
              <div class="market-guide__label">示例 JSON</div>
              <pre class="market-guide__code">{{ marketWsTemplateExampleJson }}</pre>
            </div>
          </el-form-item>
          <el-form-item label="组合流"><el-switch v-model="apiForm.wsCombinedEnabled" /></el-form-item>
          <el-form-item label="小写交易对"><el-switch v-model="apiForm.wsSymbolLowercase" /></el-form-item>
          <el-form-item label="Ping间隔"><el-input-number v-model="apiForm.wsPingIntervalSeconds" :min="1" :max="300" /></el-form-item>
          <el-form-item label="Pong超时"><el-input-number v-model="apiForm.wsPongTimeoutSeconds" :min="1" :max="600" /></el-form-item>
          <el-form-item label="连接TTL"><el-input-number v-model="apiForm.wsConnectionTtlHours" :min="1" :max="24" /></el-form-item>
          <el-form-item label="最大流数"><el-input-number v-model="apiForm.wsMaxStreamsPerConnection" :min="1" :max="1024" /></el-form-item>
          <el-form-item label="控制消息/秒"><el-input-number v-model="apiForm.wsControlMessagesPerSecond" :min="1" :max="5" /></el-form-item>
          <el-form-item label="文档URL"><el-input v-model="apiForm.docReferenceUrl" /></el-form-item>
        </template>
        <template v-else>
          <el-form-item label="API URL"><el-input v-model="apiForm.apiUrl" /></el-form-item>
          <el-form-item label="HTTP方法">
            <el-radio-group v-model="apiForm.httpMethod">
              <el-radio label="GET">GET</el-radio>
              <el-radio label="POST">POST</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="响应路径"><el-input v-model="apiForm.responsePath" placeholder="$.data[0]" /></el-form-item>
          <el-form-item label="字段映射"><el-input v-model="apiForm.fieldMapping" type="textarea" :rows="4" placeholder='{"price":"last"}' /></el-form-item>
        </template>
        <el-form-item label="优先级"><el-input-number v-model="apiForm.priority" :min="1" :max="100" /></el-form-item>
        <el-form-item label="超时秒数"><el-input-number v-model="apiForm.timeout" :min="1" :max="120" /></el-form-item>
        <el-form-item label="已启用"><el-switch v-model="apiForm.enabledValue" active-value="1" inactive-value="0" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="apiForm.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="apiDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitApi">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { listApi, addApi, updateApi, deleteApi, testApi } from '@/api/dca/market'
import SourceBindingPanel from './SourceBindingPanel.vue'

function trimString(value) {
  return String(value || '').trim()
}

function toNumber(value, fallback) {
  const num = Number(value)
  return Number.isFinite(num) ? num : fallback
}

export function normalizeApiUpper(value, fallback = '') {
  const normalized = trimString(value).toUpperCase()
  return normalized || fallback
}

export const defaultMarketActiveTab = 'apis'
export const marketBindingTabName = 'bindings'
export const marketDataSourceConsolePath = '/dca/market?tab=bindings'

export const marketPageTitle = '行情数据源'

export const marketWsTemplateGuideItems = [
  'Binance 使用流名称模板，组合流必须走 /stream，例如 ticker、markPrice、forceOrder。',
  'OKX 使用 subscribe args JSON，公共频道走 /ws/v5/public，例如 tickers、mark-price、funding-rate、open-interest、liquidation-orders。',
  '数据库中的 WebSocket 字段是运行时权威配置；代码只在配置缺失时使用安全默认值。'
]

export const marketWsTemplateBinanceExampleJson = `{
  "ws_stream_name_template": [
    "{symbol_lower}@ticker",
    "{symbol_lower}@markPrice",
    "{symbol_lower}@forceOrder"
  ],
  "ws_combined_enabled": true
}`

export const marketWsTemplateOkxExampleJson = `{
  "args": [
    { "channel": "tickers", "instId": "{instId}" },
    { "channel": "mark-price", "instId": "{instId}" },
    { "channel": "funding-rate", "instId": "{instId}" },
    { "channel": "open-interest", "instId": "{instId}" },
    { "channel": "liquidation-orders", "instType": "SWAP" }
  ]
}`

export const marketWsTemplateExampleJson = marketWsTemplateOkxExampleJson

export const legacyMarketCompatibilityMessage =
  '本页面是行情数据源统一控制面：数据源配置维护 REST / WebSocket 源，策略绑定维护运行时使用范围；旧版市场仪表板、采集触发器和日志工作流已冻结。'

export function createLegacyMarketConsoleLinks() {
  return [
    { label: '运行时模式', path: '/dca/trade/runtime', type: 'default' },
    { label: '决策审计', path: '/dca/trade/decision', type: 'default' }
  ]
}

export function createApiForm(config = {}) {
  const enabled = config.enabled === '1' ? '1' : (config.enabled === '0' ? '0' : '0')
  return {
    id: config.id ?? null,
    configName: String(config.configName || ''),
    dataCategory: normalizeApiUpper(config.dataCategory),
    dataSubType: normalizeApiUpper(config.dataSubType),
    apiName: String(config.apiName || ''),
    apiUrl: String(config.apiUrl || ''),
    transportType: normalizeApiUpper(config.transportType, 'REST'),
    vendorCode: normalizeApiUpper(config.vendorCode),
    marketScope: normalizeApiUpper(config.marketScope, 'FUTURES'),
    wsBaseUrl: String(config.wsBaseUrl || ''),
    wsPath: String(config.wsPath || ''),
    wsStreamNameTemplate: String(config.wsStreamNameTemplate || ''),
    wsCombinedEnabled: config.wsCombinedEnabled === true,
    wsSymbolLowercase: config.wsSymbolLowercase === true,
    wsPingIntervalSeconds: config.wsPingIntervalSeconds ?? 20,
    wsPongTimeoutSeconds: config.wsPongTimeoutSeconds ?? 60,
    wsConnectionTtlHours: config.wsConnectionTtlHours ?? 24,
    wsMaxStreamsPerConnection: config.wsMaxStreamsPerConnection ?? 1024,
    wsControlMessagesPerSecond: config.wsControlMessagesPerSecond ?? 5,
    docReferenceUrl: String(config.docReferenceUrl || ''),
    httpMethod: normalizeApiUpper(config.httpMethod, 'GET'),
    responsePath: String(config.responsePath || ''),
    fieldMapping: String(config.fieldMapping || ''),
    priority: toNumber(config.priority, 100),
    timeout: toNumber(config.timeout, 10),
    enabled,
    enabledValue: enabled,
    remark: String(config.remark || '')
  }
}

export function buildApiPayload(form = {}) {
  return {
    id: form.id ?? null,
    configName: trimString(form.configName),
    dataCategory: normalizeApiUpper(form.dataCategory),
    dataSubType: normalizeApiUpper(form.dataSubType),
    apiName: trimString(form.apiName),
    apiUrl: trimString(form.apiUrl),
    transportType: normalizeApiUpper(form.transportType, 'REST'),
    vendorCode: normalizeApiUpper(form.vendorCode),
    marketScope: normalizeApiUpper(form.marketScope, 'FUTURES'),
    wsBaseUrl: trimString(form.wsBaseUrl),
    wsPath: trimString(form.wsPath),
    wsStreamNameTemplate: trimString(form.wsStreamNameTemplate),
    wsCombinedEnabled: Boolean(form.wsCombinedEnabled),
    wsSymbolLowercase: Boolean(form.wsSymbolLowercase),
    wsPingIntervalSeconds: toNumber(form.wsPingIntervalSeconds, 0),
    wsPongTimeoutSeconds: toNumber(form.wsPongTimeoutSeconds, 0),
    wsConnectionTtlHours: toNumber(form.wsConnectionTtlHours, 0),
    wsMaxStreamsPerConnection: toNumber(form.wsMaxStreamsPerConnection, 0),
    wsControlMessagesPerSecond: toNumber(form.wsControlMessagesPerSecond, 0),
    docReferenceUrl: trimString(form.docReferenceUrl),
    httpMethod: normalizeApiUpper(form.httpMethod, 'GET'),
    responsePath: trimString(form.responsePath),
    fieldMapping: trimString(form.fieldMapping),
    priority: toNumber(form.priority, 100),
    timeout: toNumber(form.timeout, 10),
    enabled: form.enabledValue === '1' ? '1' : '0',
    remark: trimString(form.remark)
  }
}

export function validateApiPayload(form = {}) {
  const payload = buildApiPayload(form)
  if (!payload.configName) return 'Config name is required'
  if (!payload.dataCategory) return 'Data category is required'
  if (!payload.apiName) return 'API name is required'
  if (payload.transportType === 'WEBSOCKET') {
    if (!payload.wsBaseUrl) return 'WebSocket base URL is required'
    if (!payload.wsPath) return 'WebSocket path is required'
    if (!payload.wsStreamNameTemplate) return 'WebSocket stream template is required'
    if (payload.vendorCode === 'BINANCE') {
      if (!['/ws', '/stream'].includes(payload.wsPath)) return 'Binance WebSocket path must be /ws or /stream'
      if (payload.wsCombinedEnabled && payload.wsPath !== '/stream') return 'Binance combined streams must use /stream'
      if (!payload.wsSymbolLowercase) return 'Binance stream names require lowercase symbols'
    }
    if (payload.vendorCode === 'OKX' && payload.wsPath !== '/ws/v5/public') {
      return 'OKX public WebSocket path must be /ws/v5/public'
    }
    return ''
  }
  if (!payload.apiUrl) return 'API URL is required'
  if (!payload.responsePath) return 'Response path is required'
  if (!payload.fieldMapping) return 'Field mapping is required'
  return ''
}

export default {
  name: 'MarketDataIndex',
  components: { SourceBindingPanel },
  data() {
    return {
      activeTab: this.resolveInitialActiveTab(),
      marketPageTitle,
      marketBindingTabName,
      marketWsTemplateGuideItems,
      marketWsTemplateExampleJson,
      compatibilityMessage: legacyMarketCompatibilityMessage,
      legacyConsoleLinks: createLegacyMarketConsoleLinks(),
      apiList: [],
      apiTotal: 0,
      apiFilter: { category: '', enabled: '' },
      apiQuery: { pageNum: 1, pageSize: 10 },
      apiDialogVisible: false,
      apiDialogTitle: '',
      apiForm: createApiForm(),
      apiRules: {
        configName: [{ required: true, message: 'Config name is required', trigger: 'blur' }],
        dataCategory: [{ required: true, message: 'Data category is required', trigger: 'change' }],
        apiName: [{ required: true, message: 'API name is required', trigger: 'blur' }]
      }
    }
  },
  created() {
    this.loadApiList()
  },
  methods: {
    resolveInitialActiveTab() {
      return this.$route?.query?.tab === marketBindingTabName ? marketBindingTabName : defaultMarketActiveTab
    },
    handleApiQuery() {
      this.apiQuery.pageNum = 1
      this.loadApiList()
    },
    loadApiList() {
      const params = { ...this.apiQuery }
      if (this.apiFilter.category) params.dataCategory = this.apiFilter.category
      if (this.apiFilter.enabled !== '') params.enabled = this.apiFilter.enabled
      listApi(params).then(response => {
        this.apiTotal = response.total || 0
        this.apiList = (response.rows || []).map(item => {
          const form = createApiForm(item)
          return {
            ...item,
            transportType: form.transportType,
            vendorCode: form.vendorCode,
            endpointDisplay: form.transportType === 'WEBSOCKET' ? `${form.wsBaseUrl}${form.wsPath}` : form.apiUrl,
            enabledValue: item.enabled || '0'
          }
        })
      })
    },
    handleAddApi() {
      this.apiDialogTitle = '添加API配置'
      this.apiForm = createApiForm({ responsePath: '$', fieldMapping: '{}' })
      this.apiDialogVisible = true
    },
    handleEditApi(row) {
      this.apiDialogTitle = '编辑API配置'
      this.apiForm = createApiForm(row)
      this.apiDialogVisible = true
      this.$nextTick(() => this.$refs.apiFormRef?.clearValidate())
    },
    handleToggleApi(row) {
      const payload = buildApiPayload({ ...createApiForm(row), enabledValue: row.enabledValue })
      updateApi(payload).then(() => {
        this.$message.success('API status updated')
        this.loadApiList()
      })
    },
    handleTestApi(row) {
      testApi(row.id).then(response => {
        this.$message.success(`Test passed: ${JSON.stringify(response.data)}`)
      }).catch(error => {
        this.$message.error(`Test failed: ${error.message || 'Unknown error'}`)
      })
    },
    handleDeleteApi(row) {
      this.$confirm(`Delete API profile "${row.configName}"?`, 'Confirm', { type: 'warning' }).then(() => {
        deleteApi(row.id).then(() => {
          this.$message.success('API profile deleted')
          this.loadApiList()
        })
      })
    },
    submitApi() {
      const validationMessage = validateApiPayload(this.apiForm)
      if (validationMessage) {
        this.$message.error(validationMessage)
        return
      }
      const payload = buildApiPayload(this.apiForm)
      const request = payload.id ? updateApi(payload) : addApi(payload)
      request.then(() => {
        this.$message.success(payload.id ? 'API profile updated' : 'API profile added')
        this.apiDialogVisible = false
        this.loadApiList()
      }).catch(error => {
        this.$message.error(`API save failed: ${error.message || 'Unknown error'}`)
      })
    },
    isWebsocketApi() {
      return normalizeApiUpper(this.apiForm.transportType, 'REST') === 'WEBSOCKET'
    },
    isBinanceWebsocketApi() {
      return this.isWebsocketApi() && normalizeApiUpper(this.apiForm.vendorCode) === 'BINANCE'
    },
    isOkxWebsocketApi() {
      return this.isWebsocketApi() && normalizeApiUpper(this.apiForm.vendorCode) === 'OKX'
    },
    goTo(path) {
      this.$router.push(path)
    }
  }
}
</script>

<style scoped>
.market-page { display: flex; flex-direction: column; gap: 16px; }
.cutover-actions { display: flex; gap: 12px; flex-wrap: wrap; }
.toolbar { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; align-items: center; }
.section-gap { margin-bottom: 16px; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.muted { color: #909399; font-size: 12px; }
.market-guide {
  margin-top: 10px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  background: linear-gradient(180deg, #fffdf7 0%, #f8fbff 100%);
}
.market-guide__title {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.market-guide__label {
  margin-top: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.market-guide__list {
  margin: 0;
  padding-left: 18px;
  color: var(--el-text-color-regular);
  line-height: 1.7;
}
.market-guide__code {
  margin: 0;
  padding: 12px;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
}
@media (max-width: 768px) { .card-header { flex-direction: column; align-items: flex-start; } }
</style>
