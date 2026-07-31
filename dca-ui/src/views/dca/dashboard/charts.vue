<template>
  <div class="app-container legacy-dashboard-cutover">
    <el-alert
      title="旧仪表盘图表已退役"
      description="事件驱动运行时负责策略执行、决策、订单和仓位管理。请使用交易控制台进行操作。"
      type="warning"
      show-icon
      :closable="false"
    />

    <el-card class="cutover-card">
      <template #header>
        <span>运行时交易控制台</span>
      </template>

      <p class="summary">
        旧DCA图表组件依赖已退役的策略端点。此页面现在仅作为导航桥梁。
      </p>

      <div class="actions">
        <el-button
          v-for="item in legacyDashboardLinks"
          :key="item.path"
          :type="item.type"
          @click="goTo(item.path)"
        >
          {{ item.label }}
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script>
export function createLegacyDashboardLinks() {
  return [
    { label: '运行模式', path: '/dca/trade/runtime', type: 'primary' },
    { label: '决策审计', path: '/dca/trade/decision', type: 'default' },
    { label: '历史回放', path: '/dca/trade/replay', type: 'default' },
    { label: '订单', path: '/dca/trade/orders', type: 'default' },
    { label: '仓位', path: '/dca/trade/positions', type: 'default' }
  ]
}
</script>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
const legacyDashboardLinks = createLegacyDashboardLinks()

function goTo(path) {
  router.push(path)
}
</script>

<style scoped>
.legacy-dashboard-cutover {
  display: grid;
  gap: 16px;
}

.cutover-card {
  border-radius: 12px;
}

.summary {
  margin: 0 0 16px;
  color: #606266;
  line-height: 1.6;
}

.actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
