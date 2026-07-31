<template>
  <div class="app-container">
    <el-alert
      title="旧DCA风险页面已冻结"
      description="此页面仅作为兼容性通知保留。请使用交易控制台中的运行模式、风险熔断、决策审计和通知策略进行实时风险控制。"
      type="warning"
      show-icon
      :closable="false"
    />
    <div class="actions">
      <el-button
        v-for="item in riskConsoleLinks"
        :key="item.path"
        :type="item.type"
        @click="goTo(item.path)"
      >
        {{ item.label }}
      </el-button>
    </div>
  </div>
</template>

<script>
export function createLegacyRiskConsoleLinks() {
  return [
    { label: '运行模式', path: '/dca/trade/runtime', type: 'primary' },
    { label: '风险熔断', path: '/dca/trade/risk-hits', type: 'default' },
    { label: '决策审计', path: '/dca/trade/decision', type: 'default' },
    { label: '通知策略', path: '/dca/trade/notify-policy', type: 'default' }
  ]
}
</script>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
const riskConsoleLinks = createLegacyRiskConsoleLinks()

function goTo(path) {
  router.push(path)
}
</script>

<style scoped>
.actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
