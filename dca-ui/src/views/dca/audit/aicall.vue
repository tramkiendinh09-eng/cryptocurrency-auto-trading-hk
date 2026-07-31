<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryForm" :inline="true">
      <el-form-item label="场景" prop="scene">
        <el-select v-model="queryParams.scene" placeholder="请选择场景" clearable>
          <el-option label="市场分析" value="market_analysis" />
          <el-option label="风险预警" value="risk_alert" />
          <el-option label="交易总结" value="trade_summary" />
        </el-select>
      </el-form-item>
      <el-form-item label="模型" prop="model">
        <el-select v-model="queryParams.model" placeholder="请选择模型" clearable>
          <el-option
            v-for="item in modelOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-select v-model="queryParams.status" placeholder="请选择状态" clearable>
          <el-option label="成功" value="1" />
          <el-option label="失败" value="0" />
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
        <el-table-column label="用户ID" align="center" prop="userId" />
        <el-table-column label="场景" align="center" prop="scene">
          <template #default="scope">
            <el-tag v-if="scope.row.scene === 'market_analysis'">市场分析</el-tag>
            <el-tag v-else-if="scope.row.scene === 'risk_alert'" type="warning">风险预警</el-tag>
            <el-tag v-else-if="scope.row.scene === 'trade_summary'" type="success">交易总结</el-tag>
            <el-tag v-else>{{ scope.row.scene }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="模型" align="center" prop="model" />
        <el-table-column label="模板ID" align="center" prop="templateId" />
        <el-table-column label="提示词Token" align="center" prop="promptTokens" />
        <el-table-column label="完成Token" align="center" prop="completionTokens" />
        <el-table-column label="总Token" align="center" prop="totalTokens" />
        <el-table-column label="响应时间(ms)" align="center" prop="responseTime" />
        <el-table-column label="状态" align="center" prop="status">
          <template #default="scope">
            <el-tag v-if="scope.row.status === 1" type="success">成功</el-tag>
            <el-tag v-else type="danger">失败</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="调用时间" align="center" prop="callTime" />
        <el-table-column label="操作" align="center">
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
    <el-dialog title="调用详情" v-model="detailOpen" width="900px" append-to-body>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="用户ID">{{ logDetail.userId }}</el-descriptions-item>
        <el-descriptions-item label="场景">{{ logDetail.scene }}</el-descriptions-item>
        <el-descriptions-item label="模型">{{ logDetail.model }}</el-descriptions-item>
        <el-descriptions-item label="模板ID">{{ logDetail.templateId }}</el-descriptions-item>
        <el-descriptions-item label="提示词Token">{{ logDetail.promptTokens }}</el-descriptions-item>
        <el-descriptions-item label="完成Token">{{ logDetail.completionTokens }}</el-descriptions-item>
        <el-descriptions-item label="总Token">{{ logDetail.totalTokens }}</el-descriptions-item>
        <el-descriptions-item label="响应时间">{{ logDetail.responseTime }}ms</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag v-if="logDetail.status === 1" type="success">成功</el-tag>
          <el-tag v-else type="danger">失败</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="调用时间">{{ logDetail.callTime }}</el-descriptions-item>
      </el-descriptions>

      <el-divider>请求提示词</el-divider>
      <el-input
        v-model="logDetail.prompt"
        type="textarea"
        :rows="6"
        readonly
      />

      <el-divider>响应内容</el-divider>
      <el-input
        v-model="logDetail.response"
        type="textarea"
        :rows="10"
        readonly
      />

      <el-divider v-if="logDetail.errorMsg">错误信息</el-divider>
      <el-alert v-if="logDetail.errorMsg" :title="logDetail.errorMsg" type="error" :closable="false" />
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
  width: 100%;
}
</style>

<script>
export {
  buildAiCallModelOptions,
  formatAiCallModel,
  normalizeAiCallRows
} from './aicall.helpers'
</script>

<script setup>
import { computed, getCurrentInstance, ref } from 'vue'

import { listAiCallLog, exportLog } from "@/api/dca/audit";
import {
  buildAiCallModelOptions,
  normalizeAiCallRows
} from './aicall.helpers'

const { proxy } = getCurrentInstance();

const logList = ref([]);
const logDetail = ref({});
const detailOpen = ref(false);
const loading = ref(true);
const total = ref(0);

const queryParams = ref({
  pageNum: 1,
  pageSize: 10,
  scene: undefined,
  model: undefined,
  status: undefined
});
const modelOptions = computed(() => buildAiCallModelOptions(logList.value))

function getList() {
  loading.value = true;
  listAiCallLog(queryParams.value).then(response => {
    logList.value = normalizeAiCallRows(response.rows || []);
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
  proxy.download('dca/audit/aiCalls/export', {
    ...queryParams.value
  }, `AI调用日志_${new Date().getTime()}.xlsx`);
}

getList();
</script>
