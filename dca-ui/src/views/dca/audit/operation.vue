<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryForm" :inline="true">
      <el-form-item label="用户ID" prop="userId">
        <el-input v-model="queryParams.userId" placeholder="请输入用户ID" clearable />
      </el-form-item>
      <el-form-item label="操作人" prop="username">
        <el-input v-model="queryParams.username" placeholder="请输入操作人" clearable />
      </el-form-item>
      <el-form-item label="模块" prop="module">
        <el-select v-model="queryParams.module" placeholder="请选择模块" clearable>
          <el-option label="策略管理" value="strategy" />
          <el-option label="配置管理" value="config" />
          <el-option label="卡密管理" value="card" />
          <el-option label="AI模型" value="ai" />
        </el-select>
      </el-form-item>
      <el-form-item label="操作类型" prop="operation">
        <el-select v-model="queryParams.operation" placeholder="请选择操作类型" clearable>
          <el-option label="新增" value="create" />
          <el-option label="修改" value="update" />
          <el-option label="删除" value="delete" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        <el-button icon="Download" @click="handleExport">导出</el-button>
      </el-form-item>
    </el-form>

    <div class="table-container">
      <el-table v-loading="loading" :data="logList">
        <el-table-column label="用户ID" align="center" prop="userId" width="100" />
        <el-table-column label="操作人" align="center" prop="username" width="100" />
        <el-table-column label="模块" align="center" prop="module" width="100" />
        <el-table-column label="操作类型" align="center" prop="operation" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.operation === 'create'" type="success">新增</el-tag>
            <el-tag v-else-if="scope.row.operation === 'update'" type="warning">修改</el-tag>
            <el-tag v-else-if="scope.row.operation === 'delete'" type="danger">删除</el-tag>
            <el-tag v-else>{{ scope.row.operation }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作描述" align="center" prop="description" :show-overflow-tooltip="true" />
        <el-table-column label="请求方法" align="center" prop="requestMethod" width="80" />
        <el-table-column label="请求URL" align="center" prop="requestUrl" :show-overflow-tooltip="true" />
        <el-table-column label="IP地址" align="center" prop="requestIp" width="130" />
        <el-table-column label="状态" align="center" prop="status" width="80">
          <template #default="scope">
            <el-tag v-if="scope.row.status === 1" type="success">成功</el-tag>
            <el-tag v-else type="danger">失败</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="执行时间" align="center" prop="executionTime" width="100">
          <template #default="scope">
            {{ scope.row.executionTime }}ms
          </template>
        </el-table-column>
        <el-table-column label="操作时间" align="center" prop="operationTime" width="180" />
        <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="100">
          <template #default="scope">
            <el-button link type="primary" icon="View" @click="handleDetail(scope.row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <pagination
      v-show="total>0"
      :total="total"
      v-model:page="queryParams.pageNum"
      v-model:limit="queryParams.pageSize"
      @pagination="getList"
    />

    <!-- 详情对话框 -->
    <el-dialog title="操作详情" v-model="detailOpen" width="800px" append-to-body>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="用户ID">{{ logDetail.userId }}</el-descriptions-item>
        <el-descriptions-item label="操作人">{{ logDetail.username }}</el-descriptions-item>
        <el-descriptions-item label="模块">{{ logDetail.module }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">{{ logDetail.operation }}</el-descriptions-item>
        <el-descriptions-item label="描述">{{ logDetail.description }}</el-descriptions-item>
        <el-descriptions-item label="请求方法">{{ logDetail.requestMethod }}</el-descriptions-item>
        <el-descriptions-item label="请求URL">{{ logDetail.requestUrl }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ logDetail.requestIp }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag v-if="logDetail.status === 1" type="success">成功</el-tag>
          <el-tag v-else type="danger">失败</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="执行时间">{{ logDetail.executionTime }}ms</el-descriptions-item>
        <el-descriptions-item label="请求参数" span="2">
          <pre>{{ formatJson(logDetail.requestParams) }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="响应数据" span="2">
          <pre>{{ formatJson(logDetail.responseData) }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="错误信息" v-if="logDetail.errorMsg" span="2">
          <span style="color: red">{{ logDetail.errorMsg }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="操作时间" span="2">{{ logDetail.operationTime }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<style scoped>
.table-container {
  width: 100%;
  overflow-x: auto;
  margin-bottom: 16px;
}

.table-container :deep(.el-table) {
  min-width: 1400px;
  width: 100%;
}
</style>

<script setup>
import { listOperationLog, exportLog } from "@/api/dca/audit";

const { proxy } = getCurrentInstance();

const logList = ref([]);
const logDetail = ref({});
const detailOpen = ref(false);
const loading = ref(true);
const total = ref(0);

const queryParams = ref({
  pageNum: 1,
  pageSize: 10,
  userId: undefined,
  username: undefined,
  module: undefined,
  operation: undefined
});

function getList() {
  loading.value = true;
  listOperationLog(queryParams.value).then(response => {
    logList.value = response.rows;
    total.value = response.total;
    loading.value = false;
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

function handleDetail(row) {
  logDetail.value = row;
  detailOpen.value = true;
}

function handleExport() {
  proxy.download('dca/audit/operations/export', {
    ...queryParams.value
  }, `操作日志_${new Date().getTime()}.xlsx`);
}

function formatJson(json) {
  try {
    return JSON.stringify(JSON.parse(json), null, 2);
  } catch {
    return json;
  }
}

getList();
</script>
