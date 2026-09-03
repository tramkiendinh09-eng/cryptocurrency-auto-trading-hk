<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>运行时成交</span>
          <el-tag type="success">执行记录</el-tag>
        </div>
      </template>
      <el-table :data="fills" v-loading="loading">
        <template #empty>
          <table-state :error="loadError" @retry="loadFills" />
        </template>
        <el-table-column prop="createdAt" label="时间" min-width="168" />
        <el-table-column prop="traceId" label="追踪ID" min-width="180" />
        <el-table-column prop="orderRef" label="订单引用" min-width="160" />
        <el-table-column prop="fillPrice" label="成交价格" min-width="140" />
        <el-table-column prop="fillQuantity" label="成交数量" min-width="140" />
      </el-table>
      <pagination
        v-show="total > 0"
        :total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="loadFills"
      />
    </el-card>
  </div>
</template>

<script>
/**
 * 运行时成交页面工具函数模块
 * 提供成交数据提取等辅助函数
 */

/**
 * 从API响应中提取成交记录行数据
 * @param {Object} response - API响应对象
 * @returns {Array} 成交记录数组
 */
export function extractFillRows(response) {
  if (Array.isArray(response?.data)) {
    return response.data
  }
  if (Array.isArray(response?.rows)) {
    return response.rows
  }
  return []
}
</script>

<script setup>
/**
 * 运行时成交页面组合式API
 * 提供成交列表加载、分页等功能
 */

import { onMounted, reactive, ref } from 'vue'

import { listRuntimeFills } from '@/api/dca/tradeExecution'

/** 加载状态 */
const loading = ref(false)
/** 上一次加载的失败信息；为空表示这次是正常的「无数据」 */
const loadError = ref('')
/** 成交列表数据 */
const fills = ref([])
/** 总记录数 */
const total = ref(0)
/** 查询参数 */
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10
})

/**
 * 加载成交列表
 * 从API获取运行时成交数据
 */
async function loadFills() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await listRuntimeFills(queryParams)
    fills.value = extractFillRows(response)
    total.value = response?.total || fills.value.length
  } catch (error) {
    fills.value = []
    total.value = 0
    // 记下来交给 <table-state> 展示，别让失败伪装成空数据
    loadError.value = error?.message || error?.msg || '请求失败'
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载成交列表
onMounted(() => {
  loadFills()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
