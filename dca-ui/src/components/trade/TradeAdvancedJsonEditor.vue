<template>
  <el-collapse class="trade-advanced-json">
    <el-collapse-item name="advanced">
      <template #title>
        <div class="trade-advanced-json__title">
          <span>{{ title }}</span>
          <span v-if="description" class="trade-advanced-json__summary">{{ description }}</span>
        </div>
      </template>
      <div v-if="description" class="trade-advanced-json__description">
        {{ description }}
      </div>
      <el-input
        :model-value="modelValue"
        type="textarea"
        :rows="rows"
        :placeholder="placeholder"
        @update:model-value="emit('update:modelValue', $event)"
      />
    </el-collapse-item>
  </el-collapse>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: '高级配置'
  },
  description: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '{}'
  },
  rows: {
    type: Number,
    default: 6
  }
})

const emit = defineEmits(['update:modelValue'])
</script>

<style scoped>
.trade-advanced-json {
  width: 100%;
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  background: #fcfdff;
}

.trade-advanced-json :deep(.el-collapse-item__header) {
  align-items: flex-start;
  min-height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.trade-advanced-json :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.trade-advanced-json :deep(.el-collapse-item__content) {
  padding: 16px;
}

.trade-advanced-json__title {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 0;
  line-height: 1.4;
}

.trade-advanced-json__summary,
.trade-advanced-json__description {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.trade-advanced-json__description {
  margin-bottom: 10px;
  line-height: 1.6;
}
</style>
