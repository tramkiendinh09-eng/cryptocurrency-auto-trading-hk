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
          <el-option label="Anthropic" value="anthropic" />
          <el-option label="Azure" value="azure" />
          <el-option label="DeepSeek" value="deepseek" />
          <el-option label="Ollama" value="ollama" />
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
    </el-row>

    <el-table v-loading="loading" :data="modelList">
      <el-table-column label="模型名称" align="center" prop="modelName" />
      <el-table-column label="模型编码" align="center" prop="modelKey" />
      <el-table-column label="模型代码" align="center" prop="modelCode" />
      <el-table-column label="提供商" align="center" prop="provider">
        <template #default="scope">
          <el-tag v-if="scope.row.provider === 'openai'">OpenAI</el-tag>
          <el-tag v-else-if="scope.row.provider === 'anthropic'" type="success">Claude</el-tag>
          <el-tag v-else-if="scope.row.provider === 'azure'" type="warning">Azure</el-tag>
          <el-tag v-else-if="scope.row.provider === 'deepseek'" type="info">DeepSeek</el-tag>
          <el-tag v-else-if="scope.row.provider === 'ollama'">Ollama</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="API端点" align="center" prop="apiEndpoint" :show-overflow-tooltip="true" />
      <el-table-column label="模型版本" align="center" prop="modelVersion" />
      <el-table-column label="最大Token" align="center" prop="maxTokens" />
      <el-table-column label="超时(秒)" align="center" prop="timeoutSeconds" />
      <el-table-column label="状态" align="center" prop="isEnabled">
        <template #default="scope">
          <el-switch
            v-model="scope.row.isEnabled"
            :active-value="1"
            :inactive-value="0"
            @change="handleStatusChange(scope.row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="默认" align="center" prop="isDefault">
        <template #default="scope">
          <el-tag v-if="scope.row.isDefault === 1" type="success">默认</el-tag>
          <el-tag v-else type="info">普通</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="250">
        <template #default="scope">
          <el-button
            link
            type="primary"
            icon="Connection"
            @click="handleTest(scope.row)"
          >测试</el-button>
          <el-button
            link
            type="success"
            icon="Star"
            @click="handleSetDefault(scope.row)"
            v-if="scope.row.isDefault !== 1"
          >设为默认</el-button>
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
    <el-dialog :title="title" v-model="open" width="700px" append-to-body>
      <el-form ref="modelRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="模型名称" prop="modelName">
          <el-input v-model="form.modelName" placeholder="请输入模型名称" />
        </el-form-item>
        <el-form-item label="模型编码" prop="modelKey">
          <el-input v-model="form.modelKey" placeholder="请输入模型编码（英文唯一标识）" :disabled="form.id !== undefined" />
        </el-form-item>
        <el-form-item label="模型代码" prop="modelCode">
          <el-input v-model="form.modelCode" placeholder="例如: gpt-4.1 / deepseek-chat / deepseek-reasoner" />
        </el-form-item>
        <el-form-item label="提供商" prop="provider">
          <el-select v-model="form.provider" placeholder="请选择提供商">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Anthropic" value="anthropic" />
            <el-option label="Azure" value="azure" />
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="Ollama" value="ollama" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="API端点" prop="apiEndpoint">
          <el-input v-model="form.apiEndpoint" placeholder="请输入API端点URL" />
        </el-form-item>
        <el-form-item label="API密钥" prop="apiKeyEncrypted">
          <el-input v-model="form.apiKeyEncrypted" type="password" placeholder="请输入API密钥" show-password />
        </el-form-item>
        <el-form-item label="模型版本" prop="modelVersion">
          <el-input v-model="form.modelVersion" placeholder="例如: gpt-4, claude-3-sonnet" />
        </el-form-item>
        <el-form-item label="最大Token" prop="maxTokens">
          <el-input-number v-model="form.maxTokens" :min="100" :max="100000" />
        </el-form-item>
        <el-form-item label="温度" prop="temperature">
          <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" :precision="1" />
        </el-form-item>
        <el-form-item label="超时时间(秒)" prop="timeoutSeconds">
          <el-input-number v-model="form.timeoutSeconds" :min="5" :max="120" />
        </el-form-item>
        <el-form-item label="重试次数" prop="retryTimes">
          <el-input-number v-model="form.retryTimes" :min="0" :max="5" />
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

    <!-- 统计信息 -->
    <el-card class="stats-card" style="margin-top: 20px">
      <template #header>
        <span>使用统计</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-statistic title="总调用次数" :value="stats.totalCalls" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="总Token消耗" :value="stats.totalTokens" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="总费用($)" :value="stats.totalCost" :precision="4" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="平均响应时间(ms)" :value="stats.avgLatency" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { listAiModel, getAiModel, addAiModel, updateAiModel, delAiModel, testAiModel, setDefaultModel, getAiStats } from "@/api/dca/ai";

const { proxy } = getCurrentInstance();

const modelList = ref([]);
const open = ref(false);
const loading = ref(true);
const total = ref(0);
const title = ref("");
const stats = ref({
  totalCalls: 0,
  totalTokens: 0,
  totalCost: 0,
  avgLatency: 0
});

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    modelName: undefined,
    provider: undefined
  },
  rules: {
    modelName: [{ required: true, message: "模型名称不能为空", trigger: "blur" }],
    modelKey: [{ required: true, message: "模型编码不能为空", trigger: "blur" }],
    modelCode: [{ required: true, message: "模型代码不能为空", trigger: "blur" }],
    provider: [{ required: true, message: "请选择提供商", trigger: "change" }],
    apiEndpoint: [{ required: true, message: "API端点不能为空", trigger: "blur" }],
    apiKeyEncrypted: [{ required: true, message: "API密钥不能为空", trigger: "blur" }]
  }
});

const { queryParams, form, rules } = toRefs(data);

function getList() {
  loading.value = true;
  listAiModel(queryParams.value).then(response => {
    modelList.value = response.rows;
    total.value = response.total;
    loading.value = false;
  });
  getStats();
}

function getStats() {
  getAiStats().then(response => {
    stats.value = response.data;
  });
}

function handleQuery() {
  queryParams.value.pageNum = 1;
  getList();
}

function resetQuery() {
  proxy.resetForm("queryForm");
  handleQuery();
}

function handleAdd() {
  reset();
  open.value = true;
  title.value = "添加AI模型";
}

function handleUpdate(row) {
  reset();
  getAiModel(row.id).then(response => {
    form.value = {
      ...response.data,
      modelCode: response.data?.modelCode || response.data?.modelVersion
    };
    open.value = true;
    title.value = "修改AI模型";
  });
}

function handleTest(row) {
  proxy.$modal.msgInfo("正在测试连接...");
  testAiModel(row.id).then(() => {
    proxy.$modal.msgSuccess("连接测试成功");
  }).catch(() => {
    proxy.$modal.msgError("连接测试失败");
  });
}

function handleSetDefault(row) {
  proxy.$modal.confirm('确认将"' + row.modelName + '"设为默认模型？').then(() => {
    return setDefaultModel(row.id);
  }).then(() => {
    proxy.$modal.msgSuccess("设置成功");
    getList();
  });
}

function handleStatusChange(row) {
  const text = row.isEnabled === 1 ? "启用" : "禁用";
  proxy.$modal.confirm('确认要"' + text + '""' + row.modelName + '"模型吗？').then(() => {
    return updateAiModel(row);
  }).then(() => {
    proxy.$modal.msgSuccess(text + "成功");
  }).catch(() => {
    row.isEnabled = row.isEnabled === 1 ? 0 : 1;
  });
}

function submitForm() {
  proxy.$refs.modelRef.validate(valid => {
    if (valid) {
      if (form.value.id != undefined) {
        updateAiModel(form.value).then(() => {
          proxy.$modal.msgSuccess("修改成功");
          open.value = false;
          getList();
        });
      } else {
        addAiModel(form.value).then(() => {
          proxy.$modal.msgSuccess("新增成功");
          open.value = false;
          getList();
        });
      }
    }
  });
}

function handleDelete(row) {
  proxy.$modal.confirm('确认删除"' + row.modelName + '"模型？').then(() => {
    return delAiModel(row.id);
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("删除成功");
  });
}

function cancel() {
  open.value = false;
  reset();
}

function reset() {
  form.value = {
    id: undefined,
    modelName: undefined,
    modelKey: undefined,
    modelCode: 'gpt-4',
    provider: 'openai',
    apiEndpoint: 'https://api.openai.com/v1/chat/completions',
    apiKeyEncrypted: undefined,
    modelVersion: 'gpt-4',
    maxTokens: 2000,
    temperature: 0.7,
    timeoutSeconds: 30,
    retryTimes: 2,
    description: undefined
  };
  proxy.resetForm("modelRef");
}

getList();
</script>

