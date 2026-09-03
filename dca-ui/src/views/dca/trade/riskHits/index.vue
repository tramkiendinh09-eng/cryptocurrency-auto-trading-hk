<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>运行时风控命中</span>
          <el-tag type="danger">风控审计</el-tag>
        </div>
      </template>
      <el-table :data="riskHits" v-loading="loading">
        <template #empty>
          <table-state :error="loadError" @retry="loadRiskHits" />
        </template>
        <el-table-column prop="createdAt" label="时间" min-width="168" />
        <el-table-column prop="traceId" label="追踪ID" min-width="180" />
        <el-table-column prop="ruleCode" label="规则编码" min-width="180" />
        <el-table-column prop="reason" label="原因" min-width="220" show-overflow-tooltip />
      </el-table>
      <pagination
        v-show="total > 0"
        :total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="loadRiskHits"
      />
    </el-card>
  </div>
</template>

<script>
/**
 * 运行时风控命中页面工具函数模块
 * 提供风控命中数据提取等辅助函数
 */

/**
 * 从API响应中提取风控命中记录行数据
 * @param {Object} response - API响应对象
 * @returns {Array} 风控命中记录数组
 */
export function extractRiskHitRows(response) {
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
 * 运行时风控命中页面组合式API
 * 提供风控命中列表加载、分页等功能
 */

import { onMounted, reactive, ref } from 'vue'

import { listRuntimeRiskHits } from '@/api/dca/tradeExecution'

/** 加载状态 */
const loading = ref(false)
/** 上一次加载的失败信息；为空表示这次是正常的「无数据」 */
const loadError = ref('')
/** 风控命中列表数据 */
const riskHits = ref([])
/** 总记录数 */
const total = ref(0)
/** 查询参数 */
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10
})

/**
 * 加载风控命中列表
 * 从API获取运行时风控命中数据
 */
async function loadRiskHits() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await listRuntimeRiskHits(queryParams)
    riskHits.value = extractRiskHitRows(response)
    total.value = response?.total || riskHits.value.length
  } catch (error) {
    riskHits.value = []
    total.value = 0
    // 记下来交给 <table-state> 展示，别让失败伪装成空数据
    loadError.value = error?.message || error?.msg || '请求失败'
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载风控命中列表
onMounted(() => {
  loadRiskHits()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
