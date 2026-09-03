<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>运行时持仓</span>
          <el-tag type="danger">实盘防护</el-tag>
        </div>
      </template>
      <el-table :data="positions" v-loading="loading">
        <template #empty>
          <table-state :error="loadError" @retry="loadPositions" />
        </template>
        <el-table-column prop="exchangeCode" label="交易所" width="120" />
        <el-table-column prop="symbol" label="交易对" width="120" />
        <el-table-column label="方向" width="100">
          <template #default="scope">
            {{ formatPositionSide(scope.row.side) }}
          </template>
        </el-table-column>
        <el-table-column prop="positionQuantity" label="数量" min-width="140" />
        <el-table-column prop="entryPrice" label="入场价格" min-width="140" />
        <el-table-column prop="unrealizedPnl" label="未实现盈亏" min-width="160" />
      </el-table>
      <pagination
        v-show="total > 0"
        :total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="loadPositions"
      />
    </el-card>
  </div>
</template>

<script>
/**
 * 运行时持仓页面工具函数模块
 * 提供持仓数据提取、方向格式化等辅助函数
 */

import { formatTradeLabel } from '@/utils/tradeLabels'

/**
 * 从API响应中提取持仓记录行数据
 * @param {Object} response - API响应对象
 * @returns {Array} 持仓记录数组
 */
export function extractPositionRows(response) {
  if (Array.isArray(response?.data)) {
    return response.data
  }
  if (Array.isArray(response?.rows)) {
    return response.rows
  }
  return []
}

/**
 * 标准化持仓方向
 * 将buy/sell转换为long/short
 * @param {string} value - 原始方向值
 * @returns {string} 标准化后的方向值
 */
export function normalizePositionSide(value) {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'buy') {
    return 'long'
  }
  if (normalized === 'sell') {
    return 'short'
  }
  if (['long', 'short', 'flat'].includes(normalized)) {
    return normalized
  }
  return normalized
}

/**
 * 格式化持仓方向显示文本
 * @param {string} value - 方向值
 * @returns {string} 格式化后的显示文本
 */
export function formatPositionSide(value) {
  return formatTradeLabel('orderSide', normalizePositionSide(value)) || '-'
}

/**
 * 格式化订单方向显示文本
 * @param {string} value - 方向值
 * @returns {string} 格式化后的显示文本
 */
export function formatOrderSide(value) {
  return formatPositionSide(value)
}
</script>

<script setup>
/**
 * 运行时持仓页面组合式API
 * 提供持仓列表加载、分页等功能
 */

import { onMounted, reactive, ref } from 'vue'

import { listRuntimePositions } from '@/api/dca/tradeExecution'

/** 加载状态 */
const loading = ref(false)
/** 上一次加载的失败信息；为空表示这次是正常的「无数据」 */
const loadError = ref('')
/** 持仓列表数据 */
const positions = ref([])
/** 总记录数 */
const total = ref(0)
/** 查询参数 */
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10
})

/**
 * 加载持仓列表
 * 从API获取运行时持仓数据
 */
async function loadPositions() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await listRuntimePositions(queryParams)
    positions.value = extractPositionRows(response)
    total.value = response?.total || positions.value.length
  } catch (error) {
    positions.value = []
    total.value = 0
    // 记下来交给 <table-state> 展示，别让失败伪装成空数据
    loadError.value = error?.message || error?.msg || '请求失败'
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载持仓列表
onMounted(() => {
  loadPositions()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

