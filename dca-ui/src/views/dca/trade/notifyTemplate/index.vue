<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>通知模板</span>
          <div class="card-header__actions">
            <el-button type="primary" v-hasPermi="['dca:notifyTemplate:add']" @click="handleAdd">新增模板</el-button>
            <el-button plain @click="getList">刷新</el-button>
          </div>
        </div>
      </template>

      <div class="toolbar">
        <el-input v-model="queryParams.name" clearable placeholder="模板名称" style="width: 220px" @keyup.enter="handleQuery" />
        <el-input v-model="queryParams.code" clearable placeholder="模板编码" style="width: 220px" @keyup.enter="handleQuery" />
        <el-select v-model="queryParams.isActive" clearable placeholder="状态" style="width: 160px" @change="handleQuery">
          <el-option label="启用" :value="1" />
          <el-option label="禁用" :value="0" />
        </el-select>
      </div>

      <el-table
        v-loading="loading"
        :data="templateList"
        row-key="id"
        highlight-current-row
        empty-text="无通知模板"
        @current-change="handleCurrentChange"
      >
        <el-table-column prop="name" label="模板名称" min-width="180" />
        <el-table-column prop="code" label="模板编码" min-width="220" show-overflow-tooltip />
        <el-table-column label="标题" min-width="220" show-overflow-tooltip>
          <template #default="scope">
            {{ scope.row.titleTemplate || '--' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="Number(scope.row.isActive ?? 1) === 1 ? 'success' : 'info'">
              {{ Number(scope.row.isActive ?? 1) === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button link type="primary" v-hasPermi="['dca:notifyTemplate:edit']" @click="handleUpdate(scope.row)">修改</el-button>
            <el-button link type="danger" v-hasPermi="['dca:notifyTemplate:remove']" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <pagination
        v-show="total > 0"
        :total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="getList"
      />

      <div class="detail-grid">
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">模板详情</div>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="模板编码">{{ previewTemplate?.code || '--' }}</el-descriptions-item>
            <el-descriptions-item label="模板名称">{{ previewTemplate?.name || '--' }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ Number(previewTemplate?.isActive ?? 1) === 1 ? '启用' : '禁用' }}</el-descriptions-item>
          </el-descriptions>
          <div class="preview-tags">
            <el-tag v-for="item in variableList(previewTemplate?.variablesList || previewTemplate?.variables)" :key="item" size="small" effect="plain">
              {{ item }}
            </el-tag>
          </div>
        </el-card>
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">标题预览</div>
          </template>
          <pre class="preview-content">{{ previewTemplate?.titleTemplate || '--' }}</pre>
        </el-card>
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">内容预览</div>
          </template>
          <pre class="preview-content">{{ previewTemplate?.contentTemplate || '--' }}</pre>
        </el-card>
      </div>
    </el-card>

    <el-dialog v-model="open" :title="title" width="820px" append-to-body>
      <el-form ref="templateRef" :model="form" :rules="rules" label-width="120px">
        <TradeFormSection title="模板基础" description="先确定模板名称、模板编码，以及它是否启用、是否设为默认模板。">
          <el-form-item label="模板名称" prop="name">
            <el-input v-model="form.name" placeholder="运行风险通知" />
          </el-form-item>
          <el-form-item label="模板编码" prop="code">
            <el-input v-model="form.code" placeholder="notify.runtime.risk.v1" />
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.isActive" :active-value="1" :inactive-value="0" />
          </el-form-item>
          <el-form-item label="默认">
            <el-switch v-model="form.isDefault" :active-value="1" :inactive-value="0" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="模板说明" />
          </el-form-item>
        </TradeFormSection>

        <TradeFormSection title="模板内容" description="标题和内容模板决定最终通知内容，变量列表用于说明模板中可引用的占位符。">
          <el-form-item label="标题模板" prop="titleTemplate">
            <el-input v-model="form.titleTemplate" placeholder="[{{symbol}}] 风险预警" />
          </el-form-item>
          <el-form-item label="内容模板" prop="contentTemplate">
            <el-input v-model="form.contentTemplate" type="textarea" :rows="6" placeholder="事件：{event_type}" />
          </el-form-item>
          <el-form-item label="变量列表">
            <TradeEditableTags
              v-model="form.variablesList"
              :options="notifyTemplateVariableOptions"
              placeholder="输入或选择模板变量"
            />
          </el-form-item>
        </TradeFormSection>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="open = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
/**
 * 通知模板页面工具函数模块
 * 提供通知模板表单创建、变量解析等辅助函数
 */

function trimValue(value) {
  return String(value || '').trim()
}

function parseVariables(value) {
  if (!value || !trimValue(value)) {
    return []
  }
  if (Array.isArray(value)) {
    return value.map((item) => trimValue(item)).filter(Boolean)
  }
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed.map((item) => trimValue(item)).filter(Boolean) : []
  } catch {
    return []
  }
}

export function createNotifyTemplateForm(template = {}) {
  return {
    id: template.id,
    name: trimValue(template.name),
    code: trimValue(template.code),
    titleTemplate: trimValue(template.titleTemplate),
    contentTemplate: trimValue(template.contentTemplate),
    variablesList: parseVariables(template.variables),
    isActive: Number(template.isActive ?? 1),
    isDefault: Number(template.isDefault ?? 0),
    remark: trimValue(template.remark)
  }
}

export function buildNotifyTemplatePayload(form = {}) {
  const variables = Array.isArray(form.variablesList) ? parseVariables(form.variablesList) : parseVariables(form.variables)
  return {
    id: form.id,
    name: trimValue(form.name),
    code: trimValue(form.code),
    titleTemplate: trimValue(form.titleTemplate),
    contentTemplate: trimValue(form.contentTemplate),
    variables: JSON.stringify(variables),
    isActive: Number(form.isActive ?? 1),
    isDefault: Number(form.isDefault ?? 0),
    remark: trimValue(form.remark) || null
  }
}

export function validateNotifyTemplatePayload(form = {}) {
  const payload = buildNotifyTemplatePayload(form)
  if (!payload.name) {
    throw new Error('模板名称不能为空')
  }
  if (!payload.code) {
    throw new Error('模板编码不能为空')
  }
  if (!payload.titleTemplate) {
    throw new Error('标题模板不能为空')
  }
  if (!payload.contentTemplate) {
    throw new Error('内容模板不能为空')
  }
  return payload
}
</script>

<script setup>
import { computed, getCurrentInstance, reactive, ref } from 'vue'

import {
  addTradeNotifyTemplate,
  delTradeNotifyTemplate,
  listTradeNotifyTemplate,
  updateTradeNotifyTemplate
} from '@/api/dca/tradeNotifyTemplate'
import TradeEditableTags from '@/components/trade/TradeEditableTags.vue'
import TradeFormSection from '@/components/trade/TradeFormSection.vue'

const { proxy } = getCurrentInstance()

const notifyTemplateVariableOptions = ['symbol', 'event_type', 'severity', 'summary', 'trace_id', 'reason', 'created_at']

const loading = ref(false)
const submitting = ref(false)
const open = ref(false)
const title = ref('新增通知模板')
const templateRef = ref()
const templateList = ref([])
const total = ref(0)
const currentTemplateId = ref(null)
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  name: '',
  code: '',
  isActive: undefined
})
const form = reactive(createNotifyTemplateForm())
const rules = {
  name: [{ required: true, message: '模板名称不能为空', trigger: 'blur' }],
  code: [{ required: true, message: '模板编码不能为空', trigger: 'blur' }],
  titleTemplate: [{ required: true, message: '标题模板不能为空', trigger: 'blur' }],
  contentTemplate: [{ required: true, message: '内容模板不能为空', trigger: 'blur' }]
}

const selectedTemplate = computed(() => templateList.value.find((item) => item.id === currentTemplateId.value) || null)
const previewTemplate = computed(() => (open.value ? form : (selectedTemplate.value || templateList.value[0] || null)))

function variableList(value) {
  return parseVariables(value)
}

function resetForm(template = {}) {
  Object.assign(form, createNotifyTemplateForm(template))
  templateRef.value?.clearValidate()
}

function handleCurrentChange(row) {
  currentTemplateId.value = row?.id ?? null
}

function handleQuery() {
  queryParams.pageNum = 1
  getList()
}

async function getList() {
  loading.value = true
  try {
    const response = await listTradeNotifyTemplate({
      ...queryParams
    })
    templateList.value = response?.rows || []
    total.value = response?.total || templateList.value.length
    const stillExists = templateList.value.some((item) => item.id === currentTemplateId.value)
    currentTemplateId.value = stillExists ? currentTemplateId.value : (templateList.value[0]?.id ?? null)
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  resetForm()
  title.value = '新增通知模板'
  open.value = true
}

function handleUpdate(row) {
  resetForm(row)
  title.value = '修改通知模板'
  open.value = true
}

async function submitForm() {
  await templateRef.value?.validate()
  submitting.value = true
  try {
    const payload = validateNotifyTemplatePayload(form)
    if (payload.id) {
      await updateTradeNotifyTemplate(payload)
      proxy?.$modal?.msgSuccess?.('通知模板已更新')
    } else {
      await addTradeNotifyTemplate(payload)
      proxy?.$modal?.msgSuccess?.('通知模板已新增')
    }
    open.value = false
    await getList()
  } catch (error) {
    if (error?.message) {
      proxy?.$modal?.msgError?.(error.message)
    }
    throw error
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await proxy?.$modal?.confirm?.(`确认删除通知模板“${row.name}”吗？`)
    await delTradeNotifyTemplate(row.id)
    proxy?.$modal?.msgSuccess?.('通知模板已删除')
    await getList()
  } catch {
    // ignore when cancelled
  }
}

getList()
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-header__actions,
.toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar {
  margin-bottom: 16px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.detail-card {
  min-width: 0;
}

.detail-card__header {
  font-weight: 600;
}

.preview-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.preview-content {
  margin: 0;
  padding: 12px;
  min-height: 140px;
  border-radius: 10px;
  background: #f8fafc;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: auto;
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
