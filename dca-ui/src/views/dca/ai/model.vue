<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryForm" :inline="true">
      <el-form-item label="模型名称" prop="modelName">
        <el-input
          v-model="queryParams.modelName"
          placeholder="请输入模型名称"
          clearable
          @keyup.enter.native="handleQuery"
        />
      </el-form-item>
      <el-form-item label="提供商" prop="provider">
        <el-select v-model="queryParams.provider" placeholder="请选择提供商" clearable>
          <el-option label="OpenAI" value="openai" />
          <el-option label="Azure" value="azure" />
          <el-option label="Claude" value="anthropic" />
          <el-option label="DeepSeek" value="deepseek" />
          <el-option label="本地模型" value="local" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态" prop="isEnabled">
        <el-select v-model="queryParams.isEnabled" placeholder="状态" clearable>
          <el-option label="启用" :value="1" />
          <el-option label="禁用" :value="0" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button
          type="primary"
          icon="Plus"
          @click="handleAdd"
          v-hasPermi="['dca:aiModel:add']"
        >新增模型</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button
          type="danger"
          icon="Delete"
          :disabled="multiple"
          @click="handleDelete"
          v-hasPermi="['dca:aiModel:remove']"
        >删除</el-button>
      </el-col>
    </el-row>

    <el-table v-loading="loading" :data="modelList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column label="模型名称" align="center" prop="modelName" :show-overflow-tooltip="true" />
      <el-table-column label="模型Key" align="center" prop="modelKey" :show-overflow-tooltip="true" />
      <el-table-column label="模型代码" align="center" prop="modelCode" :show-overflow-tooltip="true" />
      <el-table-column label="提供商" align="center" prop="provider">
        <template #default="scope">
          <el-tag v-if="scope.row.provider === 'openai'">OpenAI</el-tag>
          <el-tag type="primary" v-else-if="scope.row.provider === 'azure'">Azure</el-tag>
          <el-tag type="success" v-else-if="scope.row.provider === 'anthropic'">Claude</el-tag>
          <el-tag type="danger" v-else-if="scope.row.provider === 'deepseek'">DeepSeek</el-tag>
          <el-tag type="warning" v-else-if="scope.row.provider === 'local'">本地模型</el-tag>
          <el-tag v-else>{{ scope.row.provider }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="API端点" align="center" prop="apiEndpoint" :show-overflow-tooltip="true" />
      <el-table-column label="最大Tokens" align="center" prop="maxTokens" />
      <el-table-column label="温度" align="center" prop="temperature" />
      <el-table-column label="使用次数" align="center" prop="usageCount" />
      <el-table-column label="状态" align="center" prop="isEnabled">
        <template #default="scope">
          <el-switch
            v-model="scope.row.isEnabled"
            :active-value="1"
            :inactive-value="0"
            @change="handleToggle(scope.row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="默认" align="center" prop="isDefault">
        <template #default="scope">
          <el-tag v-if="scope.row.isDefault === 1" type="success">默认</el-tag>
          <el-tag v-else type="info">否</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" align="center" class-name="small-padding fixed-width">
        <template #default="scope">
          <el-button
            link
            type="primary"
            icon="Edit"
            @click="handleUpdate(scope.row)"
            v-hasPermi="['dca:aiModel:edit']"
          >修改</el-button>
          <el-button
            link
            type="danger"
            icon="Delete"
            @click="handleDelete(scope.row)"
            v-hasPermi="['dca:aiModel:remove']"
          >删除</el-button>
          <el-button
            link
            type="success"
            icon="Check"
            @click="handleSetDefault(scope.row)"
            v-if="scope.row.isDefault !== 1"
          >设为默认</el-button>
          <el-button
            link
            type="warning"
            icon="Message"
            @click="handleTest(scope.row)"
          >测试</el-button>
        </template>
      </el-table-column>
    </el-table>

    <pagination
      v-show="total>0"
      :total="total"
      v-model:page="queryParams.pageNum"
      v-model:limit="queryParams.pageSize"
      @pagination="getList"
    />

    <!-- 添加或修改模型对话框 -->
    <el-dialog :title="title" v-model="open" width="800px" append-to-body>
      <el-form ref="modelRef" :model="form" :rules="rules" label-width="140px">
        <el-form-item label="模型Key" prop="modelKey">
          <el-input v-model="form.modelKey" placeholder="请输入模型Key" :disabled="form.id !== undefined" />
        </el-form-item>
        <el-form-item label="模型名称" prop="modelName">
          <el-input v-model="form.modelName" placeholder="请输入模型名称" />
        </el-form-item>
        <el-form-item label="模型代码" prop="modelCode">
          <el-input v-model="form.modelCode" placeholder="请输入模型代码，如：gpt-4、deepseek-chat、claude-3-5-sonnet" />
          <div class="mt-2 text-xs text-gray-500">
            <template v-if="form.provider === 'deepseek'">
              DeepSeek模型代码：deepseek-chat 或 deepseek-reasoner
            </template>
            <template v-else-if="form.provider === 'openai'">
              OpenAI模型代码：gpt-4、gpt-3.5-turbo 等
            </template>
            <template v-else-if="form.provider === 'anthropic'">
              Claude模型代码：claude-3-5-sonnet、claude-3-opus 等
            </template>
            <template v-else>
              根据提供商填写对应的模型代码
            </template>
          </div>
        </el-form-item>
        <el-form-item label="提供商" prop="provider">
          <el-select v-model="form.provider" placeholder="请选择提供商">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Azure" value="azure" />
            <el-option label="Claude" value="anthropic" />
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="本地模型" value="local" />
          </el-select>
        </el-form-item>
        <el-form-item label="API端点" prop="apiEndpoint">
          <el-input v-model="form.apiEndpoint" placeholder="请输入API端点" />
        </el-form-item>
        <el-form-item label="API密钥" prop="apiKeyEncrypted">
          <el-input v-model="form.apiKeyEncrypted" type="password" placeholder="请输入API密钥" />
          <div class="mt-2 text-xs text-gray-500">
            注意：API密钥将被加密存储
          </div>
        </el-form-item>
        <el-form-item label="API版本" prop="apiVersion">
          <el-input v-model="form.apiVersion" placeholder="请输入API版本（可选）" />
        </el-form-item>
        <el-form-item label="模型版本" prop="modelVersion">
          <el-input v-model="form.modelVersion" placeholder="请输入模型版本（可选）" />
        </el-form-item>
        <el-form-item label="最大Tokens" prop="maxTokens">
          <el-input-number v-model="form.maxTokens" :min="100" :max="100000" placeholder="请输入最大Tokens" />
        </el-form-item>
        <el-form-item label="最高温度" prop="maxTemperature">
          <el-input-number v-model="form.maxTemperature" :min="0" :max="2" :step="0.1" placeholder="请输入最高温度" />
        </el-form-item>
        <el-form-item label="温度" prop="temperature">
          <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" placeholder="请输入温度" />
        </el-form-item>
        <el-form-item label="Top-P参数" prop="topP">
          <el-input-number v-model="form.topP" :min="0" :max="1" :step="0.1" placeholder="请输入Top-P参数" />
        </el-form-item>
        <el-form-item label="每日调用限制" prop="dailyLimit">
          <el-input-number v-model="form.dailyLimit" :min="0" placeholder="请输入每日调用限制" />
        </el-form-item>
        <el-form-item label="每月Token限制" prop="monthlyTokenLimit">
          <el-input-number v-model="form.monthlyTokenLimit" :min="0" placeholder="请输入每月Token限制" />
        </el-form-item>
        <el-form-item label="超时(秒)" prop="timeoutSeconds">
          <el-input-number v-model="form.timeoutSeconds" :min="1" :max="60" placeholder="请输入超时时间" />
        </el-form-item>
        <el-form-item label="重试次数" prop="retryTimes">
          <el-input-number v-model="form.retryTimes" :min="0" :max="5" placeholder="请输入重试次数" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-input-number v-model="form.priority" :min="0" :max="100" placeholder="请输入优先级" />
        </el-form-item>
        <el-form-item label="使用次数" prop="usageCount">
          <el-input-number v-model="form.usageCount" :min="0" disabled />
        </el-form-item>
        <el-form-item label="是否启用" prop="isEnabled">
          <el-switch v-model="form.isEnabled" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="设为默认" prop="isDefault">
          <el-switch v-model="form.isDefault" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { listModel, getModel, addModel, updateModel, delModel, setDefaultModel, testModel } from "@/api/dca/ai";

const { proxy } = getCurrentInstance();

const modelList = ref([]);
const open = ref(false);
const loading = ref(true);
const ids = ref([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);
const title = ref("");

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    modelName: undefined,
    provider: undefined,
    isEnabled: undefined
  },
  rules: {
    modelKey: [
      { required: true, message: "模型Key不能为空", trigger: "blur" }
    ],
    modelName: [
      { required: true, message: "模型名称不能为空", trigger: "blur" }
    ],
    modelCode: [
      { required: true, message: "模型代码不能为空", trigger: "blur" }
    ],
    provider: [
      { required: true, message: "提供商不能为空", trigger: "blur" }
    ],
    apiEndpoint: [
      { required: true, message: "API端点不能为空", trigger: "blur" }
    ],
    apiKeyEncrypted: [
      { required: true, message: "API密钥不能为空", trigger: "blur" }
    ],
    maxTokens: [
      { required: true, message: "最大Tokens不能为空", trigger: "blur" }
    ],
    temperature: [
      { required: true, message: "温度不能为空", trigger: "blur" }
    ],
    timeoutSeconds: [
      { required: true, message: "超时时间不能为空", trigger: "blur" }
    ],
    retryTimes: [
      { required: true, message: "重试次数不能为空", trigger: "blur" }
    ],
    priority: [
      { required: true, message: "优先级不能为空", trigger: "blur" }
    ]
  }
});

const { queryParams, form, rules } = toRefs(data);

function getList() {
  loading.value = true;
  listModel(queryParams.value).then(response => {
    modelList.value = response.rows;
    total.value = response.total;
    loading.value = false;
  });
}

function cancel() {
  open.value = false;
  reset();
}

function reset() {
  form.value = {
    id: undefined,
    modelKey: undefined,
    modelCode: undefined,
    modelName: undefined,
    provider: "openai",
    apiEndpoint: "https://api.openai.com/v1/chat/completions",
    apiKeyEncrypted: undefined,
    apiVersion: undefined,
    modelVersion: undefined,
    maxTokens: 2000,
    maxTemperature: undefined,
    temperature: 0.7,
    topP: undefined,
    dailyLimit: undefined,
    monthlyTokenLimit: undefined,
    timeoutSeconds: 30,
    retryTimes: 2,
    priority: 0,
    usageCount: 0,
    isEnabled: 1,
    isDefault: 0,
    description: undefined
  };
  proxy.resetForm("modelRef");
}

function handleQuery() {
  queryParams.value.pageNum = 1;
  getList();
}

function resetQuery() {
  proxy.resetForm("queryForm");
  handleQuery();
}

function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.id);
  single.value = selection.length != 1;
  multiple.value = !selection.length;
}

function handleAdd() {
  reset();
  open.value = true;
  title.value = "添加AI模型";
}

function handleUpdate(row) {
  reset();
  const id = row.id || ids.value[0];
  getModel(id).then(response => {
    form.value = response.data;
    open.value = true;
    title.value = "修改AI模型";
  });
}

function handleToggle(row) {
  const text = row.isEnabled === 1 ? "启用" : "禁用";
  proxy.$modal.confirm('确认要"' + text + '""' + row.modelName + '"模型吗？').then(() => {
    return updateModel(row);
  }).then(() => {
    proxy.$modal.msgSuccess(text + "成功");
  }).catch(() => {
    row.isEnabled = row.isEnabled === 1 ? 0 : 1;
  });
}

function handleSetDefault(row) {
  proxy.$modal.confirm('确认要将"' + row.modelName + '"设为默认模型吗？').then(() => {
    return setDefaultModel(row.id);
  }).then(() => {
    proxy.$modal.msgSuccess("设置成功");
    getList();
  }).catch(() => {});
}

function handleTest(row) {
  proxy.$modal.confirm('确认要测试"' + row.modelName + '"模型吗？').then(() => {
    return testModel(row.id);
  }).then(() => {
    proxy.$modal.msgSuccess("测试成功，模型连接正常");
  }).catch(() => {
    proxy.$modal.msgError("测试失败，请检查配置");
  });
}

function submitForm() {
  proxy.$refs.modelRef.validate(valid => {
    if (valid) {
      if (form.value.id != undefined) {
        updateModel(form.value).then(response => {
          proxy.$modal.msgSuccess("修改成功");
          open.value = false;
          getList();
        });
      } else {
        addModel(form.value).then(response => {
          proxy.$modal.msgSuccess("新增成功");
          open.value = false;
          getList();
        });
      }
    }
  });
}

function handleDelete(row) {
  const deleteIds = row.id || ids.value;
  proxy.$modal.confirm('是否确认删除模型编号为"' + deleteIds + '"的数据项？').then(function() {
    return delModel(deleteIds);
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("删除成功");
  }).catch(() => {});
}

getList();
</script>

<style scoped>
.text-xs {
  font-size: 12px;
}

.text-gray-500 {
  color: #909399;
}

.mt-2 {
  margin-top: 8px;
}
</style>
