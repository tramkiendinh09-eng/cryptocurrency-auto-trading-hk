import { createApp, defineAsyncComponent } from 'vue'

import Cookies from 'js-cookie'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import locale from 'element-plus/es/locale/lang/zh-cn'

import '@/assets/styles/index.scss' // global css

import App from './App'
import store from './store'
import router from './router'
import directive from './directive' // directive

// 注册指令
import plugins from './plugins' // plugins
import { download } from '@/utils/request'

// svg图标
import 'virtual:svg-icons-register'
import SvgIcon from '@/components/SvgIcon'
import elementIcons from '@/components/SvgIcon/svgicon'

import './permission' // permission control

import { useDict } from '@/utils/dict'
import { getConfigKey } from "@/api/system/config"
import { parseTime, resetForm, addDateRange, handleTree, selectDictLabel, selectDictLabels } from '@/utils/ruoyi'

// 分页组件
import Pagination from '@/components/Pagination'
// 自定义表格工具组件
import RightToolbar from '@/components/RightToolbar'
// 字典标签组件
import DictTag from '@/components/DictTag'
// 表格空状态 / 加载失败状态
import TableState from '@/components/TableState'

/* 富文本 / 上传 / 预览四个组件仍然全局注册，模板里的写法一个字都不用改，
   但改成按需加载。它们同步引入时会把各自的依赖压进首屏入口包，而实际用到
   的页面极少 —— <editor> 背后是整个 Quill 编辑器，全站只有「通知公告」一个
   页面在用；三个上传/预览组件在交易控制台里一次都没出现。首屏为它们付出的
   下载时间，对着实盘盯盘的人来说是白等。 */
const Editor = defineAsyncComponent(() => import('@/components/Editor'))
const FileUpload = defineAsyncComponent(() => import('@/components/FileUpload'))
const ImageUpload = defineAsyncComponent(() => import('@/components/ImageUpload'))
const ImagePreview = defineAsyncComponent(() => import('@/components/ImagePreview'))

const app = createApp(App)

// 全局方法挂载
app.config.globalProperties.useDict = useDict
app.config.globalProperties.download = download
app.config.globalProperties.parseTime = parseTime
app.config.globalProperties.resetForm = resetForm
app.config.globalProperties.handleTree = handleTree
app.config.globalProperties.addDateRange = addDateRange
app.config.globalProperties.getConfigKey = getConfigKey
app.config.globalProperties.selectDictLabel = selectDictLabel
app.config.globalProperties.selectDictLabels = selectDictLabels

// 全局组件挂载
app.component('DictTag', DictTag)
app.component('Pagination', Pagination)
app.component('FileUpload', FileUpload)
app.component('ImageUpload', ImageUpload)
app.component('ImagePreview', ImagePreview)
app.component('RightToolbar', RightToolbar)
app.component('TableState', TableState)
app.component('Editor', Editor)

app.use(router)
app.use(store)
app.use(plugins)
app.use(elementIcons)
app.component('svg-icon', SvgIcon)

directive(app)

// 使用element-plus 并且设置全局的大小
app.use(ElementPlus, {
  locale: locale,
  // 支持 large、default、small
  size: Cookies.get('size') || 'default'
})

app.mount('#app')
