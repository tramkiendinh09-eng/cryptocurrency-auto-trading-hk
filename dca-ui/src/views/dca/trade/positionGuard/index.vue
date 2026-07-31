<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>仓位保护</span>
          <div class="card-header__actions">
            <el-button type="primary" v-hasPermi="['dca:tradePositionGuard:add']" @click="handleAdd">新增保护</el-button>
            <el-button plain @click="getList">刷新</el-button>
          </div>
        </div>
      </template>

      <div class="toolbar">
        <el-select v-model="queryParams.scopeType" clearable placeholder="范围类型" style="width: 180px" @change="handleQuery">
          <el-option v-for="item in positionGuardScopeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="queryParams.strategyId" clearable filterable placeholder="策略" style="width: 220px" @change="handleQuery">
          <el-option v-for="item in strategyOptions" :key="item.id" :label="item.strategyName || item.strategyKey" :value="item.id" />
        </el-select>
        <el-select v-model="queryParams.enabled" clearable placeholder="状态" style="width: 160px" @change="handleQuery">
          <el-option label="启用" :value="true" />
          <el-option label="禁用" :value="false" />
        </el-select>
      </div>

      <el-table v-loading="loading" :data="guardList" empty-text="暂无仓位保护配置">
        <el-table-column prop="guardName" label="保护名称" min-width="180" />
        <el-table-column label="范围类型" width="120">
          <template #default="scope">
            {{ formatScopeLabel(scope.row.scopeType) }}
          </template>
        </el-table-column>
        <el-table-column label="策略" min-width="180">
          <template #default="scope">
            {{ resolveStrategyName(scope.row.strategyId) }}
          </template>
        </el-table-column>
        <el-table-column prop="symbol" label="交易对" width="140" />
        <el-table-column prop="exchangeCode" label="交易所" width="120" />
        <el-table-column label="止损比例" width="120">
          <template #default="scope">
            {{ formatGuardThresholdPercent(scope.row.stopLossPct) }}
          </template>
        </el-table-column>
        <el-table-column label="止盈比例" width="120">
          <template #default="scope">
            {{ formatGuardThresholdPercent(scope.row.takeProfitPct) }}
          </template>
        </el-table-column>
        <el-table-column prop="maxHoldingMinutes" label="最长持仓分钟" width="140" />
        <el-table-column prop="priority" label="优先级" width="100" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.enabled ? 'success' : 'info'">{{ scope.row.enabled ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="180" show-overflow-tooltip>
          <template #default="scope">
            {{ scope.row.remark || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button link type="primary" v-hasPermi="['dca:tradePositionGuard:edit']" @click="handleUpdate(scope.row)">修改</el-button>
            <el-button link type="danger" v-hasPermi="['dca:tradePositionGuard:remove']" @click="handleDelete(scope.row)">删除</el-button>
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

    <el-dialog v-model="open" :title="title" width="720px" append-to-body>
      <el-form ref="guardRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="保护名称" prop="guardName">
          <el-input v-model="form.guardName" placeholder="BTC 仓位保护" />
        </el-form-item>
        <el-form-item label="范围类型" prop="scopeType">
          <el-radio-group v-model="form.scopeType">
            <el-radio-button v-for="item in positionGuardScopeOptions" :key="item.value" :label="item.value">
              {{ item.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="requiresStrategyScope(form.scopeType)" label="策略" prop="strategyId">
          <el-select v-model="form.strategyId" filterable clearable placeholder="选择策略" style="width: 100%">
            <el-option v-for="item in strategyOptions" :key="item.id" :label="item.strategyName || item.strategyKey" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="requiresSymbolScope(form.scopeType)" label="策略">
          <el-select v-model="form.strategyId" filterable clearable placeholder="可选，进一步缩小到策略" style="width: 100%">
            <el-option v-for="item in strategyOptions" :key="item.id" :label="item.strategyName || item.strategyKey" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="requiresSymbolScope(form.scopeType)" label="交易对" prop="symbol">
          <el-select v-model="form.symbol" clearable placeholder="选择交易对" style="width: 100%">
            <el-option v-for="item in positionGuardSymbolOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="requiresSymbolScope(form.scopeType)" label="交易所" prop="exchangeCode">
          <el-select v-model="form.exchangeCode" clearable placeholder="选择交易所" style="width: 100%">
            <el-option v-for="item in positionGuardExchangeOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="止损比例">
          <el-input-number v-model="form.stopLossPct" :min="0" :max="99.99" :step="0.1" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="止盈比例">
          <el-input-number v-model="form.takeProfitPct" :min="0" :max="99.99" :step="0.1" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="最长持仓分钟">
          <el-input-number v-model="form.maxHoldingMinutes" :min="1" :max="10080" :step="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="0" :max="999" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="可选备注" />
        </el-form-item>
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
 * 仓位保护页面工具函数模块
 * 提供仓位保护表单创建、数据转换、验证等辅助函数
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
 * 解析数字值
 * @param {*} value - 输入值
 * @param {number|null} fallback - 默认值
 * @returns {number|null} 解析后的数字或默认值
 */
function parseNumber(value, fallback = null) {
  if (value == null || value === '') {
    return fallback
  }
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function ratioToPercent(value) {
  const ratio = parseNumber(value, null)
  return ratio == null ? null : Number((ratio * 100).toFixed(8))
}

function percentToRatio(value) {
  const percent = parseNumber(value, null)
  return percent == null ? null : Number((percent / 100).toFixed(8))
}

export function formatGuardThresholdPercent(value) {
  const percent = ratioToPercent(value)
  return percent == null ? '-' : `${percent}%`
}

/**
 * 解析整数值
 * @param {*} value - 输入值
 * @param {number|null} fallback - 默认值
 * @returns {number|null} 解析后的整数或默认值
 */
function parseInteger(value, fallback = null) {
  if (value == null || value === '') {
    return fallback
  }
  const parsed = Number.parseInt(String(value).trim(), 10)
  return Number.isNaN(parsed) ? fallback : parsed
}

export const positionGuardSymbolOptions = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
// 交易所选项从后端获取，此处保留默认值作为后备
export const positionGuardExchangeOptions = ['BINANCE', 'OKX']
export const positionGuardScopeOptions = [
  { label: '全局', value: 'GLOBAL' },
  { label: '策略', value: 'STRATEGY' },
  { label: '交易对', value: 'SYMBOL' }
]

/**
 * 创建仓位保护表单对象
 * @param {Object} guard - 仓位保护数据
 * @returns {Object} 表单对象
 */
export function createTradePositionGuardForm(guard = {}) {
  return {
    id: guard.id,
    guardName: trimValue(guard.guardName),
    scopeType: trimValue(guard.scopeType).toUpperCase() || 'GLOBAL',
    strategyId: guard.strategyId ?? null,
    symbol: trimValue(guard.symbol).toUpperCase() || '',
    exchangeCode: trimValue(guard.exchangeCode).toUpperCase() || '',
    stopLossPct: ratioToPercent(guard.stopLossPct),
    takeProfitPct: ratioToPercent(guard.takeProfitPct),
    maxHoldingMinutes: parseInteger(guard.maxHoldingMinutes, null),
    enabled: guard.enabled !== false,
    priority: parseInteger(guard.priority, 0) ?? 0,
    remark: trimValue(guard.remark)
  }
}

/**
 * 构建仓位保护提交数据
 * @param {Object} form - 表单数据
 * @returns {Object} 提交数据对象
 */
export function buildTradePositionGuardPayload(form = {}) {
  return {
    id: form.id,
    guardName: trimValue(form.guardName),
    scopeType: trimValue(form.scopeType).toUpperCase(),
    strategyId: form.strategyId ?? null,
    symbol: trimValue(form.symbol).toUpperCase() || null,
    exchangeCode: trimValue(form.exchangeCode).toUpperCase() || null,
    stopLossPct: percentToRatio(form.stopLossPct),
    takeProfitPct: percentToRatio(form.takeProfitPct),
    maxHoldingMinutes: parseInteger(form.maxHoldingMinutes, null),
    enabled: Boolean(form.enabled),
    priority: parseInteger(form.priority, 0) ?? 0,
    remark: trimValue(form.remark) || null
  }
}

/**
 * 验证仓位保护提交数据
 * @param {Object} form - 表单数据
 * @returns {Object} 验证通过后的提交数据
 * @throws {Error} 验证失败时抛出错误
 */
export function validateTradePositionGuardPayload(form = {}) {
  const payload = buildTradePositionGuardPayload(form)
  if (!payload.guardName) {
    throw new Error('保护名称不能为空')
  }
  if (!payload.scopeType) {
    throw new Error('范围类型不能为空')
  }
  if (!positionGuardScopeOptions.some((item) => item.value === payload.scopeType)) {
    throw new Error(`不支持的范围类型: ${payload.scopeType}`)
  }
  if (payload.scopeType === 'STRATEGY' && !payload.strategyId) {
    throw new Error('策略范围必须绑定策略')
  }
  if (payload.scopeType === 'SYMBOL' && !payload.symbol) {
    throw new Error('交易对范围必须选择交易对')
  }
  if (payload.scopeType === 'SYMBOL' && !payload.exchangeCode) {
    throw new Error('交易对范围必须选择交易所')
  }
  if (payload.symbol && !positionGuardSymbolOptions.includes(payload.symbol)) {
    throw new Error(`不支持的交易对: ${payload.symbol}`)
  }
  if (payload.exchangeCode && !positionGuardExchangeOptions.includes(payload.exchangeCode)) {
    throw new Error(`不支持的交易所: ${payload.exchangeCode}`)
  }
  if (payload.stopLossPct == null && payload.takeProfitPct == null && payload.maxHoldingMinutes == null) {
    throw new Error('至少配置一个保护阈值')
  }
  return payload
}
</script>

<script setup>
/**
 * 仓位保护页面组合式API
 * 提供仓位保护列表加载、新增、编辑、删除等功能
 */

import { getCurrentInstance, reactive, ref } from 'vue'

import {
  addTradePositionGuard,
  delTradePositionGuard,
  listTradePositionGuard,
  updateTradePositionGuard
} from '@/api/dca/tradePositionGuard'
import { listTradeStrategy } from '@/api/dca/tradeStrategy'

const { proxy } = getCurrentInstance()

/** 加载状态 */
const loading = ref(false)
/** 提交状态 */
const submitting = ref(false)
/** 弹窗显示状态 */
const open = ref(false)
/** 弹窗标题 */
const title = ref('新增仓位保护')
/** 表单引用 */
const guardRef = ref()
/** 仓位保护列表数据 */
const guardList = ref([])
/** 总记录数 */
const total = ref(0)
/** 策略选项列表 */
const strategyOptions = ref([])
/** 查询参数 */
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  scopeType: '',
  strategyId: null,
  enabled: ''
})
/** 表单数据 */
const form = reactive(createTradePositionGuardForm({
  scopeType: 'GLOBAL',
  enabled: true,
  priority: 0
}))
/** 表单验证规则 */
const rules = {
  guardName: [{ required: true, message: '保护名称不能为空', trigger: 'blur' }],
  scopeType: [{ required: true, message: '范围类型不能为空', trigger: 'change' }],
  strategyId: [{
    validator: (_, value, callback) => {
      if (requiresStrategyScope(form.scopeType) && !value) {
        callback(new Error('请选择策略'))
        return
      }
      callback()
    },
    trigger: 'change'
  }],
  symbol: [{
    validator: (_, value, callback) => {
      if (requiresSymbolScope(form.scopeType) && !value) {
        callback(new Error('请选择交易对'))
        return
      }
      callback()
    },
    trigger: 'change'
  }],
  exchangeCode: [{
    validator: (_, value, callback) => {
      if (requiresSymbolScope(form.scopeType) && !value) {
        callback(new Error('请选择交易所'))
        return
      }
      callback()
    },
    trigger: 'change'
  }]
}

/**
 * 判断是否需要策略范围
 * @param {string} scopeType - 范围类型
 * @returns {boolean} 是否需要策略范围
 */
function requiresStrategyScope(scopeType) {
  return scopeType === 'STRATEGY'
}

/**
 * 判断是否需要交易对范围
 * @param {string} scopeType - 范围类型
 * @returns {boolean} 是否需要交易对范围
 */
function requiresSymbolScope(scopeType) {
  return scopeType === 'SYMBOL'
}

/**
 * 格式化范围类型标签
 * @param {string} scopeType - 范围类型
 * @returns {string} 格式化后的标签文本
 */
function formatScopeLabel(scopeType) {
  return positionGuardScopeOptions.find((item) => item.value === scopeType)?.label || scopeType || '-'
}

/**
 * 解析策略名称
 * @param {number} strategyId - 策略ID
 * @returns {string} 策略名称
 */
function resolveStrategyName(strategyId) {
  if (!strategyId) {
    return '全局'
  }
  const strategy = strategyOptions.value.find((item) => Number(item.id) === Number(strategyId))
  return strategy?.strategyName || strategy?.strategyKey || `#${strategyId}`
}

/**
 * 重置表单
 * @param {Object} guard - 仓位保护数据
 */
function resetForm(guard = {}) {
  Object.assign(form, createTradePositionGuardForm({
    scopeType: 'GLOBAL',
    enabled: true,
    priority: 0,
    ...guard
  }))
  guardRef.value?.clearValidate()
}

/**
 * 加载策略选项
 */
async function loadOptions() {
  const response = await listTradeStrategy({ pageNum: 1, pageSize: 200 })
  strategyOptions.value = response?.rows || []
}

/**
 * 处理查询操作
 */
function handleQuery() {
  queryParams.pageNum = 1
  getList()
}

/**
 * 加载仓位保护列表
 */
async function getList() {
  loading.value = true
  try {
    const response = await listTradePositionGuard({
      ...queryParams
    })
    guardList.value = response?.rows || []
    total.value = response?.total || guardList.value.length
  } finally {
    loading.value = false
  }
}

/**
 * 处理新增仓位保护操作
 */
async function handleAdd() {
  await loadOptions()
  resetForm()
  title.value = '新增仓位保护'
  open.value = true
}

/**
 * 处理编辑仓位保护操作
 * @param {Object} row - 要编辑的仓位保护数据
 */
async function handleUpdate(row) {
  await loadOptions()
  resetForm(row)
  title.value = '修改仓位保护'
  open.value = true
}

/**
 * 提交表单
 */
async function submitForm() {
  await guardRef.value?.validate()
  submitting.value = true
  try {
    const payload = validateTradePositionGuardPayload(form)
    if (payload.id) {
      await updateTradePositionGuard(payload)
      proxy?.$modal?.msgSuccess?.('仓位保护已更新')
    } else {
      await addTradePositionGuard(payload)
      proxy?.$modal?.msgSuccess?.('仓位保护已新增')
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
 * 处理删除仓位保护操作
 * @param {Object} row - 要删除的仓位保护数据
 */
async function handleDelete(row) {
  try {
    await proxy?.$modal?.confirm?.(`确认删除仓位保护”${row.guardName}”吗？`)
    await delTradePositionGuard(row.id)
    proxy?.$modal?.msgSuccess?.('仓位保护已删除')
    await getList()
  } catch {
    // ignore when cancelled
  }
}

// 初始化加载选项和列表
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

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
