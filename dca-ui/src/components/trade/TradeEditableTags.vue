<template>
  <el-select
    :model-value="normalizedValue"
    multiple
    filterable
    allow-create
    default-first-option
    clearable
    collapse-tags
    collapse-tags-tooltip
    :placeholder="placeholder"
    style="width: 100%"
    @update:model-value="handleUpdate"
  >
    <el-option
      v-for="item in mergedOptions"
      :key="item"
      :label="item"
      :value="item"
    />
  </el-select>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  options: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: '请输入或选择'
  }
})

const emit = defineEmits(['update:modelValue'])

function normalizeList(values = []) {
  return Array.from(
    new Set(
      (Array.isArray(values) ? values : [])
        .map((item) => String(item || '').trim())
        .filter(Boolean)
    )
  )
}

const normalizedValue = computed(() => normalizeList(props.modelValue))
const mergedOptions = computed(() => normalizeList([...(props.options || []), ...normalizedValue.value]))

function handleUpdate(values) {
  emit('update:modelValue', normalizeList(values))
}
</script>
