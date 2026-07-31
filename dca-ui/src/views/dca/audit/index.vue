<template>
  <div class="app-container">
    <AiCallLog />
  </div>
</template>

<script>
export const auditTabItems = [
  { label: 'AI调用日志', name: 'aicall' }
]
</script>

<script setup>
import AiCallLog from './aicall.vue'
</script>
