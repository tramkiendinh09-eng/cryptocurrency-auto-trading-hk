<template>
  <div class="header-search">
    <el-tooltip :content="`搜索页面（${shortcutLabel}）`" effect="dark" placement="bottom">
      <div class="search-trigger" @click.stop="click">
        <svg-icon class-name="search-icon" icon-class="search" />
        <span class="search-kbd">{{ shortcutLabel }}</span>
      </div>
    </el-tooltip>
    <el-dialog
      v-model="show"
      width="600"
      @close="close"
      @opened="onDialogOpened"
      :show-close="false"
      append-to-body
    >
      <el-input
        v-model="search"
        ref="headerSearchSelectRef"
        size="large"
        @input="querySearch"
        prefix-icon="Search"
        placeholder="搜索页面：可输入标题、路径，或用空格分隔多个关键词"
        clearable
        @keyup.enter="selectActiveResult"
        @keydown.up.prevent="navigateResult('up')"
        @keydown.down.prevent="navigateResult('down')"
      >
      </el-input>

      <div class="result-count" v-if="search && options.length > 0">
        找到 <strong>{{ options.length }}</strong> 个结果
      </div>

      <div class="result-wrap">
        <el-scrollbar>

          <template v-if="options.length > 0">
            <div
              class="search-item"
              tabindex="1"
              v-for="(item, index) in options"
              :key="item.path"
              :class="{ 'is-active': index === activeIndex }"
              :style="activeStyle(index)"
              @mouseenter="activeIndex = index"
              @mouseleave="activeIndex = -1"
            >
              <div class="left">
                <svg-icon class="menu-icon" :icon-class="item.icon" />
              </div>
              <div class="search-info" @click="change(item)">
                <div class="menu-title" v-html="highlightText(item.title.join(' / '))"></div>
                <div class="menu-path" v-html="highlightText(item.path)"></div>
              </div>
              <svg-icon icon-class="enter" v-show="index === activeIndex" />
            </div>
          </template>

          <div class="empty-state" v-else-if="search && options.length === 0">
            <el-icon class="empty-icon"><Search /></el-icon>
            <p class="empty-text">未找到 "<strong>{{ search }}</strong>" 相关菜单</p>
            <p class="empty-tip">试试其他关键词或路径</p>
          </div>

        </el-scrollbar>
      </div>

      <div class="search-footer">
        <span class="shortcut-item">
          <kbd>↑</kbd><kbd>↓</kbd> 切换
        </span>
        <span class="shortcut-item">
          <kbd>↵</kbd> 选择
        </span>
        <span class="shortcut-item">
          <kbd>Esc</kbd> 关闭
        </span>
        <span class="shortcut-item shortcut-hint">
          随处按 <kbd>{{ shortcutLabel }}</kbd> 唤起
        </span>
      </div>
    </el-dialog>
  </div>
</template>

<script>
/**
 * 菜单搜索的排序规则。抽成纯函数是为了能单独测 —— 组件本身要 pinia、
 * 路由和 Element Plus 才能挂载，而真正容易写错的只有这段匹配。
 *
 * 三层由严到松合并，先出现的排前面：
 *   1) 子串直接命中标题或路径 —— 最确定，用户多半就是要这个
 *   2) 多关键词全部命中 —— 「通知 模板」这种断续输入
 *   3) 模糊匹配兜底容错 —— 由调用方传进来
 *
 * @param {Array}  pool  候选项，每项形如 { path, title: string[] }
 * @param {string} query 用户输入
 * @param {Array}  fuzzy 模糊匹配的结果，可为空
 * @returns {Array} 去重后的结果
 */
export function rankSearchResults(pool, query, fuzzy = []) {
  const raw = String(query || '').trim()
  if (raw === '') return pool

  const q = raw.toLowerCase()
  const tokens = q.split(/\s+/).filter(Boolean)
  const hay = (item) => ((item.title || []).join(' ') + ' ' + item.path).toLowerCase()

  const exact = pool.filter((item) => hay(item).includes(q))
  const everyToken = tokens.length > 1
    ? pool.filter((item) => tokens.every((t) => hay(item).includes(t)))
    : []

  const merged = []
  const seen = new Set()
  for (const item of [...exact, ...everyToken, ...fuzzy]) {
    if (seen.has(item.path)) continue
    seen.add(item.path)
    merged.push(item)
  }
  return merged
}

/** 把用户输入切成高亮用的关键词 */
export function highlightTokens(query) {
  return String(query || '').trim().split(/\s+/).filter(Boolean)
}
</script>

<script setup>
import Fuse from 'fuse.js'
import { getNormalPath } from '@/utils/ruoyi'
import { isHttp } from '@/utils/validate'
import useSettingsStore from '@/store/modules/settings'
import usePermissionStore from '@/store/modules/permission'

const search = ref('')
const options = ref([])
const activeIndex = ref(-1)
const show = ref(false)
const fuse = ref(undefined)
const headerSearchSelectRef = ref(null)
const router = useRouter()
const theme = computed(() => useSettingsStore().theme)
const routes = computed(() => usePermissionStore().defaultRoutes)

function click() {
  show.value = !show.value
  if (show.value) {
    options.value = searchPool.value
  }
}

function onDialogOpened() {
  nextTick(() => {
    headerSearchSelectRef.value && headerSearchSelectRef.value.focus()
  })
}

function close() {
  headerSearchSelectRef.value && headerSearchSelectRef.value.blur()
  search.value = ''
  options.value = searchPool.value
  show.value = false
  activeIndex.value = -1
}

function change(val) {
  const p = val.path
  const query = val.query
  if (isHttp(p)) {
    // http(s):// 路径新窗口打开
    const pindex = p.indexOf("http")
    window.open(p.substr(pindex, p.length), "_blank")
  } else {
    if (query) {
      router.push({ path: p, query: JSON.parse(query) })
    } else {
      router.push(p)
    }
  }
  search.value = ''
  options.value = searchPool.value
  nextTick(() => {
    show.value = false
  })
}

function initFuse(list) {
  fuse.value = new Fuse(list, {
    shouldSort: true,
    threshold: 0.2,
    distance: 100,
    minMatchCharLength: 1,
    keys: [{
      name: 'title',
      weight: 0.7
    }, {
      name: 'path',
      weight: 0.3
    }]
  })
}

function generateRoutes(routes, basePath = '', prefixTitle = []) {
  let res = []
  for (const r of routes) {
    if (r.hidden) { continue }
    const p = r.path.length > 0 && r.path[0] === '/' ? r.path : '/' + r.path
    const data = {
      path: !isHttp(r.path) ? getNormalPath(basePath + p) : r.path,
      title: [...prefixTitle],
      icon: ''
    }
    if (r.meta && r.meta.title) {
      data.title = [...data.title, r.meta.title]
      data.icon = r.meta.icon
      if (r.redirect !== "noRedirect") {
        res.push(data)
      }
    }
    if (r.query) {
      data.query = r.query
    }
    if (r.children) {
      const tempRoutes = generateRoutes(r.children, data.path, data.title)
      if (tempRoutes.length >= 1) {
        res = [...res, ...tempRoutes]
      }
    }
  }
  return res
}

function querySearch(query) {
  activeIndex.value = -1
  /* 原来只按路径做子串匹配，标题得靠 fuse 去碰，而 threshold 又是 0.2，
     收得很紧 —— 输「持仓」这类词经常一条都出不来。 */
  const fuzzy = fuse.value ? fuse.value.search(String(query || '').trim()).map((r) => r.item) : []
  options.value = rankSearchResults(searchPool.value, query, fuzzy)
}

function activeStyle(index) {
  if (index !== activeIndex.value) return {}
  return {
    "background-color": theme.value,
    "color": "#fff"
  }
}

function navigateResult(direction) {
  if (direction === "up") {
    activeIndex.value = activeIndex.value <= 0 ? options.value.length - 1 : activeIndex.value - 1
  } else if (direction === "down") {
    activeIndex.value = activeIndex.value >= options.value.length - 1 ? 0 : activeIndex.value + 1
  }
}

function selectActiveResult() {
  if (options.value.length > 0 && activeIndex.value >= 0) {
    change(options.value[activeIndex.value])
  }
}

function highlightText(text) {
  if (!text) return ''
  // 多关键词时逐个高亮，否则用户看不出哪个词命中了哪一段
  const parts = highlightTokens(search.value).map(escapeRegExp)
  if (!parts.length) return text
  const reg = new RegExp(`(${parts.join('|')})`, 'gi')
  return text.replace(reg, '<span class="highlight">$1</span>')
}

function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/* 原来是 onMounted 时抓一次快照。动态路由是登录后才注册的，组件挂载和路由
   就位的先后顺序没有保证，抓早了搜索池就永远是空的。改成跟着路由算，
   顺带让「菜单改了要重新登录才能搜到」这种问题不再出现。 */
const searchPool = computed(() => generateRoutes(routes.value))

watch(searchPool, (list) => {
  initFuse(list)
  options.value = list
}, { immediate: true })

/* Mac 上是 ⌘K，其余平台 Ctrl+K —— 和绝大多数工具的习惯保持一致。 */
const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)
const shortcutLabel = computed(() => (isMac ? '⌘K' : 'Ctrl+K'))

function onGlobalKeydown(e) {
  if (e.key !== 'k' && e.key !== 'K') return
  if (!(e.metaKey || e.ctrlKey)) return
  // 浏览器自己不占用 Ctrl+K / ⌘K 的场景下才拦，另外别打断正在输入的人
  e.preventDefault()
  show.value = true
  options.value = searchPool.value
}

onMounted(() => window.addEventListener('keydown', onGlobalKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onGlobalKeydown))
</script>

<style lang='scss' scoped>
:deep(.el-dialog__header) {
  padding: 6px !important;
}

:deep(.highlight) {
  color: red;
  font-weight: 600;
}

:deep(.is-active .highlight) {
  color: rgba(255, 255, 255, 0.9);
  font-weight: 600;
}

.header-search {
  .search-trigger {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    padding: 0 4px;
  }

  .search-icon {
    font-size: 18px;
    vertical-align: middle;
  }

  // 快捷键提示：窄屏放不下就收起来，只留图标
  .search-kbd {
    font-size: 11px;
    line-height: 1;
    padding: 2px 5px;
    border: 1px solid var(--el-border-color, #dcdfe6);
    border-radius: 4px;
    color: var(--el-text-color-secondary, #909399);
    white-space: nowrap;
  }

  @media (max-width: 992px) {
    .search-kbd { display: none; }
  }
}

.search-footer .shortcut-hint {
  margin-left: auto;
  color: #bbb;
}

.result-count {
  padding: 6px 16px 0;
  font-size: 12px;
  color: #aaa;

  strong {
    color: red;
    font-weight: 600;
  }
}

.result-wrap {
  height: 280px;
  margin: 4px 0;

  .search-item {
    display: flex;
    height: 48px;
    align-items: center;
    padding-right: 10px;
    border-radius: 4px;
    transition: background 0.15s;

    .left {
      width: 60px;
      text-align: center;
      flex-shrink: 0;

      .menu-icon {
        width: 18px;
        height: 18px;
      }
    }

    .search-info {
      padding-left: 5px;
      margin-top: 10px;
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      flex: 1;
      overflow: hidden;

      .menu-title,
      .menu-path {
        height: 20px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .menu-path {
        color: #ccc;
        font-size: 10px;
      }
    }
  }

  .search-item:hover {
    cursor: pointer;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;

    .empty-icon {
      font-size: 42px;
      color: #e0e0e0;
      margin-bottom: 14px;
    }

    .empty-text {
      font-size: 14px;
      color: #999;
      margin: 0 0 6px;

      strong {
        color: #666;
      }
    }

    .empty-tip {
      font-size: 12px;
      color: #bbb;
      margin: 0;
    }
  }
}

.search-footer {
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 10px 20px;
  border-top: 1px solid #f0f0f0;
  color: #999;
  font-size: 12px;

  .shortcut-item {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  kbd {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 5px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: #f7f7f7;
    color: #555;
    font-size: 11px;
    font-family: inherit;
    line-height: 1;
    box-shadow: 0 1px 0 #ccc;
  }
}
</style>
