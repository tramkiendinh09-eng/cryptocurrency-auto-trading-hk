<template>
  <el-empty :image-size="60">
    <template #description>
      <template v-if="!error">
        <p class="table-state__text">{{ emptyText }}</p>
      </template>
      <template v-else>
        <p class="table-state__failed">数据没能加载出来</p>
        <p class="table-state__detail">{{ detail }}</p>
        <el-button size="small" type="primary" plain @click="emit('retry')">重新加载</el-button>
      </template>
    </template>
  </el-empty>
</template>

<script setup>
/**
 * 表格的空状态 / 失败状态。
 *
 * 这两种情况必须分开显示。原来的写法是请求失败就把列表清空，于是
 * 「后端挂了」和「今天一笔成交都没有」在界面上长得完全一样 —— 盯实盘的人
 * 看到空表格，没有任何线索判断该去查服务，还是本来就没有数据。
 */
defineOptions({ name: 'TableState' })

const props = defineProps({
  /** 加载失败时传入错误信息；为空表示这次是正常的「无数据」 */
  error: { type: [String, Error, Object], default: '' },
  /** 无数据时的说明文案 */
  emptyText: { type: String, default: '暂无数据' }
})

const emit = defineEmits(['retry'])

const detail = computed(() => {
  const e = props.error
  if (!e) return ''
  const msg = typeof e === 'string' ? e : (e.message || e.msg || '')
  // 拿不到具体原因时，至少告诉用户往哪儿看
  return msg || '请求未能完成，请检查后端服务是否正常'
})
</script>

<style scoped>
.table-state__text {
  margin: 0;
  color: var(--el-text-color-secondary);
}

.table-state__failed {
  margin: 0 0 4px;
  color: var(--el-color-danger);
  font-weight: 500;
}

.table-state__detail {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  word-break: break-all;
}
</style>
