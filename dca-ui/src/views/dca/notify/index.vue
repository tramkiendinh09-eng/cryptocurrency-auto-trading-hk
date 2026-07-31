<template>
  <div class="app-container">
    <el-alert
      :title="notifyChannelCompatibilityMessage"
      type="info"
      :closable="false"
      class="page-alert"
    />

    <el-form ref="queryFormRef" :model="queryParams" :inline="true">
      <el-form-item label="类型" prop="channelType">
        <el-select v-model="queryParams.channelType" clearable placeholder="所有类型" style="width: 180px">
          <el-option v-for="item in channelTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态" prop="isEnabled">
        <el-select v-model="queryParams.isEnabled" clearable placeholder="所有状态" style="width: 160px">
          <el-option label="已启用" :value="1" />
          <el-option label="已禁用" :value="0" />
        </el-select>
      </el-form-item>
      <el-form-item label="名称" prop="channelName">
        <el-input v-model="queryParams.channelName" clearable placeholder="渠道名称" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button type="primary" icon="Plus" v-hasPermi="['dca:notify:add']" @click="handleAdd">添加渠道</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="danger" icon="Delete" :disabled="multiple" v-hasPermi="['dca:notify:remove']" @click="handleDelete">删除</el-button>
      </el-col>
    </el-row>

    <el-table v-loading="loading" :data="channelList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column prop="channelName" label="渠道" min-width="180" show-overflow-tooltip />
      <el-table-column label="类型" width="120">
        <template #default="{ row }">
          <el-tag :type="channelToneMap[row.channelType] || 'info'">
            {{ channelLabelMap[row.channelType] || row.channelType }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="配置" min-width="240" show-overflow-tooltip>
        <template #default="{ row }">
          {{ formatChannelSummary(row) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-switch v-model="row.isEnabled" :active-value="1" :inactive-value="0" @change="handleToggle(row)" />
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
      <el-table-column prop="createTime" label="创建时间" width="180">
        <template #default="{ row }">
          {{ parseTime(row.createTime) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" v-hasPermi="['dca:notify:edit']" @click="handleUpdate(row)">编辑</el-button>
          <el-button link type="danger" v-hasPermi="['dca:notify:remove']" @click="handleDelete(row)">删除</el-button>
          <el-button
            v-if="row.channelType === 'email'"
            link
            type="warning"
            v-hasPermi="['dca:notify:edit']"
            @click="handleTestConnection(row)"
          >
            SMTP测试
          </el-button>
          <el-button
            v-else
            link
            type="success"
            v-hasPermi="['dca:notify:edit']"
            @click="handleTest(row)"
          >
            发送测试
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <pagination
      v-show="total > 0"
      :total="total"
      v-model:page="queryParams.pageNum"
      v-model:limit="queryParams.pageSize"
      @pagination="loadChannels"
    />

    <el-dialog v-model="dialogOpen" :title="dialogTitle" width="720px" append-to-body>
      <el-form ref="channelFormRef" :model="channelForm" :rules="rules" label-width="150px">
        <el-form-item label="渠道名称" prop="channelName">
          <el-input v-model="channelForm.channelName" placeholder="运维告警 / 运行时审计 / 风险提示" />
        </el-form-item>
        <el-form-item label="渠道类型" prop="channelType">
          <el-select v-model="channelForm.channelType" placeholder="选择渠道类型" style="width: 100%" @change="handleChannelTypeChange">
            <el-option v-for="item in channelTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>

        <template v-if="channelForm.channelType === 'email'">
          <el-form-item label="SMTP主机" prop="smtpHost">
            <el-input v-model="channelForm.smtpHost" placeholder="smtp.qq.com" />
          </el-form-item>
          <el-form-item label="SMTP端口" prop="smtpPort">
            <el-input-number v-model="channelForm.smtpPort" :min="1" :max="65535" style="width: 100%" />
          </el-form-item>
          <el-form-item label="SMTP用户" prop="mailUsername">
            <el-input v-model="channelForm.mailUsername" placeholder="ops@example.com" />
          </el-form-item>
          <el-form-item label="SMTP密码" prop="mailPassword">
            <el-input v-model="channelForm.mailPassword" type="password" show-password placeholder="SMTP认证密码或应用密码" />
          </el-form-item>
          <el-form-item label="发件人名称" prop="mailFrom">
            <el-input v-model="channelForm.mailFrom" placeholder="Runtime Ops" />
          </el-form-item>
          <el-form-item label="收件人邮箱" prop="emailAddress">
            <el-input v-model="channelForm.emailAddress" placeholder="ops@example.com" />
          </el-form-item>
        </template>

        <template v-else-if="channelForm.channelType === 'telegram'">
          <el-form-item label="机器人令牌" prop="botToken">
            <el-input v-model="channelForm.botToken" placeholder="Telegram机器人令牌" />
          </el-form-item>
          <el-form-item label="聊天ID" prop="chatId">
            <el-input v-model="channelForm.chatId" placeholder="Telegram聊天ID" />
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="Webhook URL" prop="webhookUrl">
            <el-input v-model="channelForm.webhookUrl" placeholder="https://..." />
          </el-form-item>
        </template>

        <el-form-item label="已启用" prop="isEnabled">
          <el-switch v-model="channelForm.isEnabled" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="channelForm.remark" type="textarea" :rows="3" placeholder="用于运行时告警、风险拦截、执行失败等..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogOpen = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
/**
 * 通知渠道页面工具函数模块
 * 提供渠道配置、验证等辅助函数
 */

const CHANNEL_TYPE_OPTIONS = [
  { label: 'Email', value: 'email' },
  { label: 'Telegram', value: 'telegram' },
  { label: 'DingTalk', value: 'dingtalk' },
  { label: 'Feishu', value: 'feishu' },
  { label: 'Webhook', value: 'webhook' }
]

export const notifyChannelCompatibilityMessage =
  'notify_channel 持久化活动渠道定义。notify_record 仍然是投递审计追踪，通知策略已经在这些表之上绑定了严重性路由。'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function text(value) {
  return String(value ?? '').trim()
}

export function createSupportedChannelTypes() {
  return CHANNEL_TYPE_OPTIONS.map((item) => ({ ...item }))
}

export function createRecordQuery(query = {}) {
  return {
    pageNum: Number(query.pageNum ?? 1),
    pageSize: Number(query.pageSize ?? 10),
    channelType: text(query.channelType) || undefined,
    status: query.status ?? undefined,
    title: text(query.title) || undefined,
    traceId: text(query.traceId) || undefined,
    recipient: text(query.recipient) || undefined
  }
}

export function createChannelForm(channel = {}) {
  const channelType = text(channel.channelType) || 'email'
  return {
    id: channel.id,
    channelType,
    channelName: text(channel.channelName),
    webhookUrl: text(channel.webhookUrl),
    token: text(channel.token),
    recipient: text(channel.recipient),
    smtpHost: text(channel.smtpHost),
    smtpPort: Number(channel.smtpPort ?? 587),
    mailUsername: text(channel.mailUsername),
    mailPassword: text(channel.mailPassword),
    mailFrom: text(channel.mailFrom),
    isEnabled: Number(channel.isEnabled ?? 1),
    remark: text(channel.remark),
    emailAddress: channelType === 'email' ? text(channel.recipient) : '',
    botToken: channelType === 'telegram' ? text(channel.token) : '',
    chatId: channelType === 'telegram' ? text(channel.recipient) : ''
  }
}

export function buildChannelPayload(form = {}) {
  const channelType = text(form.channelType).toLowerCase()
  const payload = {
    id: form.id,
    channelType,
    channelName: text(form.channelName),
    webhookUrl: '',
    token: '',
    recipient: '',
    smtpHost: '',
    smtpPort: form.smtpPort == null ? undefined : Number(form.smtpPort),
    mailUsername: text(form.mailUsername),
    mailPassword: text(form.mailPassword),
    mailFrom: text(form.mailFrom),
    isEnabled: Number(Boolean(form.isEnabled)),
    remark: text(form.remark)
  }
  if (form.isEnabled === 1 || form.isEnabled === 0) {
    payload.isEnabled = Number(form.isEnabled)
  }
  if (channelType === 'email') {
    payload.recipient = text(form.emailAddress)
    payload.smtpHost = text(form.smtpHost)
  } else if (channelType === 'telegram') {
    payload.token = text(form.botToken)
    payload.recipient = text(form.chatId)
    payload.smtpHost = ''
    payload.smtpPort = undefined
    payload.mailUsername = ''
    payload.mailPassword = ''
    payload.mailFrom = ''
  } else {
    payload.webhookUrl = text(form.webhookUrl)
    payload.smtpHost = ''
    payload.smtpPort = undefined
    payload.mailUsername = ''
    payload.mailPassword = ''
    payload.mailFrom = ''
  }
  return payload
}

export function validateChannelPayload(form = {}) {
  const payload = buildChannelPayload(form)
  if (!payload.channelName) {
    throw new Error('Channel name is required')
  }
  if (!payload.channelType) {
    throw new Error('Channel type is required')
  }
  if (payload.channelType === 'email') {
    if (!payload.smtpHost) {
      throw new Error('SMTP host is required')
    }
    if (!payload.recipient || !EMAIL_RE.test(payload.recipient)) {
      throw new Error('Recipient email is invalid')
    }
  } else if (payload.channelType === 'telegram') {
    if (!payload.token) {
      throw new Error('Telegram bot token is required')
    }
    if (!payload.recipient) {
      throw new Error('Telegram chat id is required')
    }
  } else {
    if (!payload.webhookUrl) {
      throw new Error('Webhook URL is required')
    }
    if (!payload.webhookUrl.startsWith('https://')) {
      throw new Error('Webhook URL must use https')
    }
  }
  return payload
}

export function formatChannelSummary(row = {}) {
  const channelType = text(row.channelType).toLowerCase()
  if (channelType === 'email') {
    return text(row.recipient)
  }
  if (channelType === 'telegram') {
    return `chat:${text(row.recipient)}`
  }
  return text(row.webhookUrl)
}
</script>

<script setup>
import { computed, getCurrentInstance, reactive, ref, toRefs } from 'vue'

import {
  addChannel,
  delChannel,
  getChannel,
  listChannel,
  testChannel,
  testMailConnection,
  toggleChannel,
  updateChannel
} from '@/api/dca/notify'

const { proxy } = getCurrentInstance()

const loading = ref(false)
const saving = ref(false)
const dialogOpen = ref(false)
const dialogTitle = ref('Add Channel')
const total = ref(0)
const channelList = ref([])
const ids = ref([])
const multiple = ref(true)
const channelFormRef = ref()
const queryFormRef = ref()

const data = reactive({
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    channelType: undefined,
    isEnabled: undefined,
    channelName: undefined
  },
  channelForm: createChannelForm(),
  rules: {
    channelName: [{ required: true, message: 'Channel name is required', trigger: 'blur' }],
    channelType: [{ required: true, message: 'Channel type is required', trigger: 'change' }]
  }
})

const { queryParams, channelForm, rules } = toRefs(data)

const channelTypeOptions = createSupportedChannelTypes()
const channelLabelMap = Object.fromEntries(channelTypeOptions.map((item) => [item.value, item.label]))
const channelToneMap = {
  email: 'success',
  telegram: 'primary',
  dingtalk: 'warning',
  feishu: 'danger',
  webhook: 'info'
}

const normalizedForm = computed(() => createChannelForm(channelForm.value))

function resetChannelForm(channel) {
  Object.assign(channelForm.value, createChannelForm(channel))
  channelFormRef.value?.clearValidate()
}

async function loadChannels() {
  loading.value = true
  try {
    const response = await listChannel(queryParams.value)
    channelList.value = response?.rows || []
    total.value = response?.total || 0
  } finally {
    loading.value = false
  }
}

function handleQuery() {
  queryParams.value.pageNum = 1
  loadChannels()
}

function resetQuery() {
  queryFormRef.value?.resetFields()
  queryParams.value.pageNum = 1
  loadChannels()
}

function handleSelectionChange(selection) {
  ids.value = selection.map((item) => item.id)
  multiple.value = !selection.length
}

function handleAdd() {
  dialogTitle.value = '添加渠道'
  resetChannelForm()
  dialogOpen.value = true
}

async function handleUpdate(row) {
  const response = await getChannel(row.id)
  dialogTitle.value = '编辑渠道'
  resetChannelForm(response?.data || {})
  dialogOpen.value = true
}

function handleChannelTypeChange() {
  const nextForm = createChannelForm({ ...normalizedForm.value, channelType: channelForm.value.channelType })
  Object.assign(channelForm.value, nextForm)
}

async function submitForm() {
  await channelFormRef.value?.validate()
  const payload = validateChannelPayload(channelForm.value)
  saving.value = true
  try {
    if (payload.id) {
      await updateChannel(payload)
    } else {
      await addChannel(payload)
    }
    proxy?.$modal?.msgSuccess?.('Channel saved')
    dialogOpen.value = false
    await loadChannels()
  } catch (error) {
    proxy?.$modal?.msgError?.(error?.message || 'Save failed')
    throw error
  } finally {
    saving.value = false
  }
}

async function handleToggle(row) {
  const nextValue = Number(row.isEnabled)
  try {
    await toggleChannel(row.id, nextValue)
    proxy?.$modal?.msgSuccess?.('Channel status updated')
  } catch (error) {
    row.isEnabled = nextValue === 1 ? 0 : 1
    proxy?.$modal?.msgError?.(error?.message || 'Status update failed')
  }
}

async function handleDelete(row) {
  const deleteIds = row?.id ? row.id : ids.value
  await proxy?.$modal?.confirm?.(`Delete channel ${deleteIds}?`)
  await delChannel(deleteIds)
  proxy?.$modal?.msgSuccess?.('Channel deleted')
  await loadChannels()
}

async function handleTest(row) {
  await testChannel(row.id)
  proxy?.$modal?.msgSuccess?.('Test notification dispatched')
}

async function handleTestConnection(row) {
  await testMailConnection(row.id)
  proxy?.$modal?.msgSuccess?.('SMTP connection succeeded')
}

loadChannels()
</script>

<style scoped>
.page-alert {
  margin-bottom: 16px;
}
</style>
