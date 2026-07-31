<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>运行时订单</span>
          <el-tag type="warning">执行控制台</el-tag>
        </div>
      </template>
      <el-form :model="queryParams" :inline="true" class="query-form">
        <el-form-item label="执行状态">
          <el-select v-model="queryParams.status" clearable placeholder="全部" style="width: 160px">
            <el-option
              v-for="item in executionStatusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="订单状态">
          <el-select v-model="queryParams.orderStatus" clearable placeholder="全部" style="width: 180px">
            <el-option
              v-for="item in orderStatusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="orders" v-loading="loading">
        <el-table-column prop="traceId" label="追踪ID" min-width="180" />
        <el-table-column prop="exchangeCode" label="交易所" width="120" />
        <el-table-column prop="symbol" label="交易对" width="120" />
        <el-table-column label="方向" width="100">
          <template #default="scope">
            {{ formatOrderSide(scope.row.side) }}
          </template>
        </el-table-column>
        <el-table-column label="模式" width="100">
          <template #default="scope">
            {{ formatRuntimeMode(scope.row.mode) }}
          </template>
        </el-table-column>
        <el-table-column prop="orderRef" label="订单引用" min-width="160" />
        <el-table-column label="执行状态" width="120">
          <template #default="scope">
            <el-tag :type="executionStatusTag(scope.row.status)">
              {{ formatExecutionStatus(scope.row.status || 'pending') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="订单状态" width="120">
          <template #default="scope">
            <el-tag :type="orderStatusTag(scope.row.orderStatus)">
              {{ formatOrderStatus(scope.row.orderStatus || 'PENDING') }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <pagination
        v-show="total > 0"
        :total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="loadOrders"
      />
    </el-card>
  </div>
</template>

<script>
/**
 * 运行时订单页面工具函数模块
 * 提供订单查询构建、状态格式化等辅助函数
 */

export { executionStatusTag, orderStatusTag } from '@/utils/tradeExecutionStatus'

import { formatTradeLabel } from '@/utils/tradeLabels'

/**
 * 构建订单查询参数
 * @param {Object} filters - 过滤条件
 * @returns {Object} 查询参数对象
 */
export function buildOrderQuery(filters = {}) {
  const query = {}
  if (filters.pageNum) {
    query.pageNum = filters.pageNum
  }
  if (filters.pageSize) {
    query.pageSize = filters.pageSize
  }
  if (filters.status) {
    query.status = filters.status
  }
  if (filters.orderStatus) {
    query.orderStatus = filters.orderStatus
  }
  return query
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
 * 格式化订单方向显示文本
 * @param {string} value - 方向值
 * @returns {string} 格式化后的显示文本
 */
export function formatOrderSide(value) {
  return formatTradeLabel('orderSide', value) || '-'
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
</script>

<script setup>
/**
 * 运行时订单页面组合式API
 * 提供订单列表加载、查询、分页等功能
 */

import { onMounted, reactive, ref } from 'vue'

import { listRuntimeOrders } from '@/api/dca/tradeExecution'
import { executionStatusTag, orderStatusTag } from '@/utils/tradeExecutionStatus'

/** 加载状态 */
const loading = ref(false)
/** 订单列表数据 */
const orders = ref([])
/** 总记录数 */
const total = ref(0)
/** 查询参数 */
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  status: '',
  orderStatus: ''
})

/** 执行状态选项列表 */
const executionStatusOptions = [
  { label: '已成交', value: 'filled' },
  { label: '待执行', value: 'pending' },
  { label: '部分成交', value: 'partial' },
  { label: '已取消', value: 'canceled' },
  { label: '已过期', value: 'expired' },
  { label: '执行失败', value: 'failed' },
  { label: '已拦截', value: 'blocked' },
  { label: '已跳过', value: 'skipped' }
]

/** 订单状态选项列表 */
const orderStatusOptions = [
  { label: '已成交', value: 'FILLED' },
  { label: '待处理', value: 'PENDING' },
  { label: '部分成交', value: 'PARTIALLY_FILLED' },
  { label: '已取消', value: 'CANCELED' },
  { label: '已过期', value: 'EXPIRED' },
  { label: '已拒绝', value: 'REJECTED' },
  { label: '已拦截', value: 'BLOCKED' },
  { label: '已跳过', value: 'SKIPPED' }
]

/**
 * 加载订单列表
 * 从API获取运行时订单数据
 */
async function loadOrders() {
  loading.value = true
  try {
    const response = await listRuntimeOrders(buildOrderQuery(queryParams))
    orders.value = response?.rows || response?.data || []
    total.value = response?.total || orders.value.length
  } catch (error) {
    orders.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

/**
 * 处理查询操作
 * 重置页码并重新加载数据
 */
function handleQuery() {
  queryParams.pageNum = 1
  loadOrders()
}

/**
 * 重置查询条件
 * 清空筛选条件并重新加载数据
 */
function resetQuery() {
  queryParams.pageNum = 1
  queryParams.status = ''
  queryParams.orderStatus = ''
  loadOrders()
}

// 组件挂载时加载订单列表
onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.query-form {
  margin-bottom: 16px;
}
</style>

