<template>
  <section class="trade-form-section">
    <header class="trade-form-section__header">
      <div class="trade-form-section__title">{{ title }}</div>
      <div v-if="description" class="trade-form-section__description">{{ description }}</div>
    </header>
    <div class="trade-form-section__body">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.trade-form-section {
  margin-bottom: 20px;
  padding: 16px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  background: #fcfcfd;
}

.trade-form-section__header {
  margin-bottom: 12px;
}

.trade-form-section__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.trade-form-section__description {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.trade-form-section__body {
  display: block;
}
</style>
