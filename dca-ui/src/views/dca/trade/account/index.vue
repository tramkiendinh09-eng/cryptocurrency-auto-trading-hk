<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>交易所账户</span>
          <div class="card-header__actions">
            <el-button type="primary" v-hasPermi="['dca:tradeAccount:add']" @click="handleAdd">添加账户</el-button>
            <el-button plain @click="getList">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table
        v-loading="loading"
        :data="accountList"
        row-key="id"
        highlight-current-row
        empty-text="暂无交易所账户"
        @current-change="handleCurrentChange"
      >
        <el-table-column label="交易所" prop="exchangeCode" min-width="140" />
      <el-table-column label="账户" prop="accountName" min-width="180" />
      <el-table-column label="账户键" prop="accountKey" min-width="160" />
      <el-table-column label="角色" min-width="120">
        <template #default="scope">
          {{ formatTradeLabel('accountRole', scope.row.accountRole) || scope.row.accountRole }}
        </template>
      </el-table-column>
        <el-table-column label="访问密钥" min-width="180">
          <template #default="scope">
            {{ maskSecret(scope.row.apiKeyCiphertext) }}
          </template>
        </el-table-column>
        <el-table-column label="密钥口令" min-width="180">
          <template #default="scope">
            {{ maskSecret(scope.row.apiSecretCiphertext) }}
          </template>
        </el-table-column>
        <el-table-column label="运行时标志" min-width="220">
          <template #default="scope">
            <el-space wrap>
              <el-tag v-if="scope.row.testnet" type="warning">测试网</el-tag>
              <el-tag v-if="scope.row.demoTrading" type="info">演示</el-tag>
              <el-tag v-if="scope.row.apiBaseUrl" type="success">自定义地址</el-tag>
              <span v-if="!scope.row.testnet && !scope.row.demoTrading && !scope.row.apiBaseUrl">--</span>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="市场模式" min-width="240">
          <template #default="scope">
            <el-space wrap>
              <el-tag size="small">{{ formatTradeLabel('marginMode', scope.row.marginMode || 'cross') }}</el-tag>
              <el-tag size="small" type="info">{{ formatTradeLabel('leverageMode', scope.row.leverageMode || 'manual') }}</el-tag>
              <el-tag size="small" type="warning">{{ formatTradeLabel('positionMode', scope.row.positionMode || 'one_way') }}</el-tag>
              <el-tag size="small" type="success">{{ scope.row.settleCurrency || 'USDT' }}</el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="健康状态" min-width="220">
          <template #default="scope">
            <el-space direction="vertical" alignment="flex-start" :size="4">
              <el-tag :type="resolveHealthTagType(scope.row.healthStatus)">
                {{ formatTradeLabel('healthStatus', scope.row.healthStatus || 'unknown') }}
              </el-tag>
              <span class="meta-text">{{ scope.row.lastValidatedAt || '--' }}</span>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.enabled ? 'success' : 'info'">
              {{ scope.row.enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button
              link
              type="primary"
              v-hasPermi="['dca:tradeAccount:edit']"
              @click="handleUpdate(scope.row)"
            >
              编辑
            </el-button>
            <el-button
              link
              type="danger"
              v-hasPermi="['dca:tradeAccount:remove']"
              @click="handleDelete(scope.row)"
            >
              删除
            </el-button>
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
            <div class="detail-card__header">账户静态配置</div>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="交易所">{{ previewAccount?.exchangeCode || '--' }}</el-descriptions-item>
            <el-descriptions-item label="账户名称">{{ previewAccount?.accountName || '--' }}</el-descriptions-item>
            <el-descriptions-item label="账户键">{{ previewAccount?.accountKey || '--' }}</el-descriptions-item>
            <el-descriptions-item label="账户角色">{{ formatTradeLabel('accountRole', previewAccount?.accountRole) || previewAccount?.accountRole || '--' }}</el-descriptions-item>
            <el-descriptions-item label="访问密钥">{{ maskSecret(previewAccount?.apiKeyCiphertext) }}</el-descriptions-item>
            <el-descriptions-item label="密钥口令">{{ maskSecret(previewAccount?.apiSecretCiphertext) }}</el-descriptions-item>
          </el-descriptions>
          <div class="preview-tags">
            <el-tag v-if="previewAccount?.testnet" size="small" type="warning" effect="plain">测试网</el-tag>
            <el-tag v-if="previewAccount?.demoTrading" size="small" type="info" effect="plain">演示交易</el-tag>
            <el-tag v-if="previewAccount?.apiBaseUrl" size="small" type="success" effect="plain">自定义地址</el-tag>
            <el-tag size="small" effect="plain">{{ previewAccount?.settleCurrency || 'USDT' }}</el-tag>
          </div>
        </el-card>
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="detail-card__header">运行健康状态</div>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="状态">
              <el-tag :type="resolveHealthTagType(previewAccount?.healthStatus)">
                {{ formatTradeLabel('healthStatus', previewAccount?.healthStatus || 'unknown') }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="最近校验时间">{{ previewAccount?.lastValidatedAt || '--' }}</el-descriptions-item>
            <el-descriptions-item label="保证金模式">{{ formatTradeLabel('marginMode', previewAccount?.marginMode) || '--' }}</el-descriptions-item>
            <el-descriptions-item label="杠杆模式">{{ formatTradeLabel('leverageMode', previewAccount?.leverageMode) || '--' }}</el-descriptions-item>
            <el-descriptions-item label="持仓模式">{{ formatTradeLabel('positionMode', previewAccount?.positionMode) || '--' }}</el-descriptions-item>
          </el-descriptions>
          <pre class="preview-content">{{ previewAccount?.lastErrorMessage || '--' }}</pre>
        </el-card>
      </div>
    </el-card>

    <el-dialog v-model="open" :title="title" width="520px" append-to-body>
      <el-form ref="accountRef" :model="form" :rules="rules" label-width="120px">
        <TradeFormSection title="账户基础" description="先填写交易所、账户名称、账户角色，以及这套凭证主要用于什么场景。">
          <el-form-item label="交易所" prop="exchangeCode">
            <el-select
              v-model="form.exchangeCode"
              filterable
              allow-create
              default-first-option
              placeholder="BINANCE / OKX"
              style="width: 100%"
            >
              <el-option v-for="item in exchangeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="账户名称" prop="accountName">
            <el-input v-model="form.accountName" placeholder="主力合约账户" />
          </el-form-item>
          <el-form-item label="账户键">
            <el-input v-model="form.accountKey" placeholder="binance-main" />
          </el-form-item>
          <el-form-item label="账户角色">
            <el-select v-model="form.accountRole" placeholder="选择角色" style="width: 100%">
              <el-option label="执行" value="EXECUTION" />
              <el-option label="只读" value="READONLY" />
              <el-option label="影子" value="SHADOW" />
            </el-select>
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.enabled" />
          </el-form-item>
        </TradeFormSection>

        <TradeFormSection title="交易接入" description="这里配置交易所 API 凭证、市场模式以及测试网等接入参数。">
          <el-form-item label="访问密钥" prop="apiKeyCiphertext">
            <el-input v-model="form.apiKeyCiphertext" show-password />
          </el-form-item>
          <el-form-item label="密钥口令" prop="apiSecretCiphertext">
            <el-input v-model="form.apiSecretCiphertext" type="password" show-password />
          </el-form-item>
          <el-form-item label="Passphrase">
            <el-input v-model="form.passphraseCiphertext" type="password" show-password placeholder="OKX 必填" />
          </el-form-item>
          <el-form-item label="自定义地址">
            <el-input v-model="form.apiBaseUrl" placeholder="可选的自定义交易所地址" />
          </el-form-item>
          <el-form-item label="保证金模式">
            <el-select v-model="form.marginMode" placeholder="选择保证金模式" style="width: 100%">
              <el-option label="全仓" value="cross" />
              <el-option label="逐仓" value="isolated" />
            </el-select>
          </el-form-item>
          <el-form-item label="杠杆模式">
            <el-select v-model="form.leverageMode" placeholder="选择杠杆模式" style="width: 100%">
              <el-option label="手动" value="manual" />
              <el-option label="自动" value="auto" />
            </el-select>
          </el-form-item>
          <el-form-item label="持仓模式">
            <el-select v-model="form.positionMode" placeholder="选择持仓模式" style="width: 100%">
              <el-option label="单向持仓" value="one_way" />
              <el-option label="双向持仓" value="hedge" />
            </el-select>
          </el-form-item>
          <el-form-item label="结算货币">
            <el-input v-model="form.settleCurrency" placeholder="USDT" />
          </el-form-item>
          <el-form-item label="测试网">
            <el-switch v-model="form.testnet" />
          </el-form-item>
          <el-form-item label="演示交易">
            <el-switch v-model="form.demoTrading" />
          </el-form-item>
        </TradeFormSection>

        <TradeFormSection title="运行健康" description="这部分用于记录账户当前健康状态、最近校验时间以及最新错误。">
          <el-form-item label="健康状态">
            <el-select v-model="form.healthStatus" placeholder="选择健康状态" style="width: 100%">
              <el-option label="未知" value="unknown" />
              <el-option label="健康" value="healthy" />
              <el-option label="降级" value="degraded" />
              <el-option label="异常" value="unhealthy" />
            </el-select>
          </el-form-item>
          <el-form-item label="最后验证时间">
            <el-date-picker
              v-model="form.lastValidatedAt"
              type="datetime"
              value-format="YYYY-MM-DD HH:mm:ss"
              placeholder="选择验证时间"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="最后错误信息">
            <el-input v-model="form.lastErrorMessage" type="textarea" :rows="3" placeholder="最新的验证或运行时错误" />
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
 * 交易所账户页面工具函数模块
 * 提供账户表单创建、数据转换、验证等辅助函数
 */

/**
 * 标准化交易所代码
 * @param {string} value - 交易所代码
 * @returns {string} 标准化后的代码
 */
export function normalizeExchangeCode(value) {
  return String(value || '').trim().toUpperCase()
}

/**
 * 遮蔽密钥显示
 * 只显示密钥的前后部分，中间用***替代
 * @param {string} value - 原始密钥值
 * @returns {string} 遮蔽后的密钥显示
 */
export function maskSecret(value) {
  if (!value) {
    return '--'
  }
  const visible = String(value)
  if (visible.length <= 8) {
    return `${visible.slice(0, 2)}***${visible.slice(-2)}`
  }
  return `${visible.slice(0, 4)}***${visible.slice(-4)}`
}

/**
 * 获取健康状态对应的标签类型
 * @param {string} status - 健康状态值
 * @returns {string} Element Plus标签类型
 */
export function resolveHealthTagType(status) {
  const normalized = String(status || '').trim().toLowerCase()
  if (normalized === 'healthy') {
    return 'success'
  }
  if (normalized === 'degraded') {
    return 'warning'
  }
  if (normalized === 'unhealthy') {
    return 'danger'
  }
  return 'info'
}

/**
 * 创建交易所账户表单对象
 * @param {Object} account - 账户数据
 * @returns {Object} 表单对象
 */
export function createExchangeAccountForm(account = {}) {
  return {
    id: account.id,
    exchangeCode: normalizeExchangeCode(account.exchangeCode),
    accountName: String(account.accountName || ''),
    accountKey: String(account.accountKey || ''),
    accountRole: normalizeExchangeCode(account.accountRole || 'EXECUTION'),
    apiKeyCiphertext: String(account.apiKeyCiphertext || ''),
    apiSecretCiphertext: String(account.apiSecretCiphertext || ''),
    passphraseCiphertext: String(account.passphraseCiphertext || ''),
    apiBaseUrl: String(account.apiBaseUrl || ''),
    marginMode: String(account.marginMode || 'cross').trim().toLowerCase(),
    leverageMode: String(account.leverageMode || 'manual').trim().toLowerCase(),
    positionMode: String(account.positionMode || 'one_way').trim().toLowerCase(),
    settleCurrency: normalizeExchangeCode(account.settleCurrency || 'USDT'),
    healthStatus: String(account.healthStatus || 'unknown').trim().toLowerCase(),
    lastValidatedAt: String(account.lastValidatedAt || ''),
    lastErrorMessage: String(account.lastErrorMessage || ''),
    testnet: account.testnet === true,
    demoTrading: account.demoTrading === true,
    enabled: account.enabled !== false
  }
}

/**
 * 构建交易所账户提交数据
 * @param {Object} form - 表单数据
 * @returns {Object} 提交数据对象
 */
export function buildExchangeAccountPayload(form = {}) {
  return {
    id: form.id,
    exchangeCode: normalizeExchangeCode(form.exchangeCode),
    accountName: String(form.accountName || '').trim(),
    accountKey: String(form.accountKey || '').trim(),
    accountRole: normalizeExchangeCode(form.accountRole || 'EXECUTION'),
    apiKeyCiphertext: String(form.apiKeyCiphertext || '').trim(),
    apiSecretCiphertext: String(form.apiSecretCiphertext || '').trim(),
    passphraseCiphertext: String(form.passphraseCiphertext || '').trim(),
    apiBaseUrl: String(form.apiBaseUrl || '').trim(),
    marginMode: String(form.marginMode || 'cross').trim().toLowerCase(),
    leverageMode: String(form.leverageMode || 'manual').trim().toLowerCase(),
    positionMode: String(form.positionMode || 'one_way').trim().toLowerCase(),
    settleCurrency: normalizeExchangeCode(form.settleCurrency || 'USDT'),
    healthStatus: String(form.healthStatus || 'unknown').trim().toLowerCase(),
    lastValidatedAt: String(form.lastValidatedAt || '').trim(),
    lastErrorMessage: String(form.lastErrorMessage || '').trim(),
    testnet: Boolean(form.testnet),
    demoTrading: Boolean(form.demoTrading),
    enabled: Boolean(form.enabled)
  }
}

/**
 * 验证交易所账户提交数据
 * @param {Object} form - 表单数据
 * @returns {string} 验证错误信息，空字符串表示验证通过
 */
export function validateExchangeAccountPayload(form = {}) {
  const payload = buildExchangeAccountPayload(form)
  if (!payload.exchangeCode) {
    return '交易所不能为空'
  }
  if (!payload.accountName) {
    return '账户名称不能为空'
  }
  if (!payload.apiKeyCiphertext) {
    return '访问密钥不能为空'
  }
  if (!payload.apiSecretCiphertext) {
    return '密钥口令不能为空'
  }
  if (payload.exchangeCode === 'OKX' && !payload.passphraseCiphertext) {
    return 'OKX 账户必须填写 Passphrase'
  }
  return ''
}
</script>

<script setup>
/**
 * 交易所账户页面组合式API
 * 提供账户列表加载、新增、编辑、删除等功能
 */

import { computed, getCurrentInstance, reactive, ref } from 'vue'

import TradeFormSection from '@/components/trade/TradeFormSection.vue'
import {
  addExchangeAccount as addExchangeAccountApi,
  delExchangeAccount as delExchangeAccountApi,
  listExchangeAccount as listExchangeAccountApi,
  updateExchangeAccount as updateExchangeAccountApi
} from '@/api/dca/exchangeAccount'
import { formatTradeLabel } from '@/utils/tradeLabels'

const { proxy } = getCurrentInstance()

/** 加载状态 */
const loading = ref(false)
/** 提交状态 */
const submitting = ref(false)
/** 弹窗显示状态 */
const open = ref(false)
/** 弹窗标题 */
const title = ref('添加账户')
/** 表单引用 */
const accountRef = ref()
/** 账户列表数据 */
const accountList = ref([])
/** 总记录数 */
const total = ref(0)
/** 当前选中的账户ID */
const currentAccountId = ref(null)
/** 查询参数 */
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10
})
/** 交易所选项列表 */
const exchangeOptions = ['BINANCE', 'OKX']
/** 表单数据 */
const form = reactive(createExchangeAccountForm())
/** 表单验证规则 */
const rules = {
  exchangeCode: [{ required: true, message: '交易所不能为空', trigger: 'change' }],
  accountName: [{ required: true, message: '账户名称不能为空', trigger: 'blur' }],
  apiKeyCiphertext: [{ required: true, message: '访问密钥不能为空', trigger: 'blur' }],
  apiSecretCiphertext: [{ required: true, message: '密钥口令不能为空', trigger: 'blur' }]
}
/** 当前选中的账户计算属性 */
const selectedAccount = computed(() => accountList.value.find((item) => item.id === currentAccountId.value) || null)
/** 预览账户计算属性 */
const previewAccount = computed(() => (open.value ? form : (selectedAccount.value || accountList.value[0] || null)))

/**
 * 重置表单
 * 将表单数据重置为指定账户数据或空表单
 * @param {Object} account - 账户数据
 */
function resetForm(account = {}) {
  Object.assign(form, createExchangeAccountForm(account))
  accountRef.value?.clearValidate()
}

/**
 * 处理表格行选中变化
 * 更新当前选中的账户ID
 * @param {Object} row - 选中的行数据
 */
function handleCurrentChange(row) {
  currentAccountId.value = row?.id ?? null
}

/**
 * 加载账户列表
 * 从API获取交易所账户数据并更新列表
 */
async function getList() {
  loading.value = true
  try {
    const response = await listExchangeAccountApi({
      ...queryParams
    })
    accountList.value = response?.rows || []
    total.value = response?.total || accountList.value.length
    const stillExists = accountList.value.some((item) => item.id === currentAccountId.value)
    currentAccountId.value = stillExists ? currentAccountId.value : (accountList.value[0]?.id ?? null)
  } finally {
    loading.value = false
  }
}

/**
 * 处理添加账户操作
 * 重置表单并打开新增弹窗
 */
function handleAdd() {
  resetForm()
  title.value = '添加账户'
  open.value = true
}

/**
 * 处理编辑账户操作
 * 使用指定账户数据填充表单并打开编辑弹窗
 * @param {Object} row - 要编辑的账户数据
 */
function handleUpdate(row) {
  resetForm(row)
  title.value = '编辑账户'
  open.value = true
}

/**
 * 提交表单
 * 验证表单数据并执行新增或更新操作
 */
async function submitForm() {
  await accountRef.value?.validate()
  submitting.value = true
  try {
    const payload = buildExchangeAccountPayload(form)
    const validationMessage = validateExchangeAccountPayload(payload)
    if (validationMessage) {
      proxy?.$modal?.msgError?.(validationMessage)
      return
    }
    if (payload.id) {
      await updateExchangeAccountApi(payload)
      proxy?.$modal?.msgSuccess?.('账户已更新')
    } else {
      await addExchangeAccountApi(payload)
      proxy?.$modal?.msgSuccess?.('账户已新增')
    }
    open.value = false
    await getList()
  } finally {
    submitting.value = false
  }
}

/**
 * 处理删除账户操作
 * 确认后删除指定账户
 * @param {Object} row - 要删除的账户数据
 */
async function handleDelete(row) {
  await proxy?.$modal?.confirm?.(`确认删除交易所账户”${row.accountName}”吗？`)
  await delExchangeAccountApi(row.id)
  proxy?.$modal?.msgSuccess?.('账户已删除')
  await getList()
}

getList()
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header__actions {
  display: flex;
  gap: 8px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
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
  margin: 12px 0 0;
  padding: 12px;
  min-height: 96px;
  border-radius: 10px;
  background: #f8fafc;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 768px) {
  .card-header {
    align-items: flex-start;
    gap: 12px;
    flex-direction: column;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
