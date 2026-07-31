<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryForm" :inline="true">
      <el-form-item label="卡密" prop="cardKey">
        <el-input
          v-model="queryParams.cardKey"
          placeholder="请输入卡密"
          clearable
          @keyup.enter.native="handleQuery"
        />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-select v-model="queryParams.status" placeholder="请选择状态" clearable>
          <el-option label="未使用" value="unused" />
          <el-option label="已激活" value="activated" />
          <el-option label="已过期" value="expired" />
          <el-option label="已禁用" value="disabled" />
        </el-select>
      </el-form-item>
      <el-form-item label="类型" prop="cardType">
        <el-select v-model="queryParams.cardType" placeholder="请选择类型" clearable>
          <el-option label="时间版" value="time" />
          <el-option label="永久版" value="permanent" />
          <el-option label="次数版" value="count" />
          <el-option label="试用版" value="trial" />
        </el-select>
      </el-form-item>
      <el-form-item label="批次号" prop="batchNo">
        <el-input
          v-model="queryParams.batchNo"
          placeholder="请输入批次号"
          clearable
        />
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
          @click="handleGenerate"
          v-hasPermi="['dca:card:generate']"
        >生成卡密</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button
          type="success"
          icon="Download"
          @click="handleExport"
          v-hasPermi="['dca:card:export']"
        >导出</el-button>
      </el-col>
    </el-row>

    <el-table v-loading="loading" :data="cardList">
      <el-table-column label="卡密" align="center" prop="cardKey" :show-overflow-tooltip="true" />
      <el-table-column label="类型" align="center" prop="cardType">
        <template #default="scope">
          <el-tag v-if="scope.row.cardType === 'time'">时间版</el-tag>
          <el-tag v-else-if="scope.row.cardType === 'permanent'" type="success">永久版</el-tag>
          <el-tag v-else-if="scope.row.cardType === 'count'" type="warning">次数版</el-tag>
          <el-tag v-else-if="scope.row.cardType === 'trial'" type="info">试用版</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="等级" align="center" prop="cardLevel">
        <template #default="scope">
          <el-tag v-if="scope.row.cardLevel === 'basic'">基础版</el-tag>
          <el-tag v-else-if="scope.row.cardLevel === 'pro'" type="success">专业版</el-tag>
          <el-tag v-else-if="scope.row.cardLevel === 'premium'" type="warning">旗舰版</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="天数/次数" align="center">
        <template #default="scope">
          <span v-if="scope.row.cardType === 'time' || scope.row.cardType === 'trial'">{{ scope.row.days }}天</span>
          <span v-else-if="scope.row.cardType === 'count'">{{ scope.row.counts }}次</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" align="center" prop="status">
        <template #default="scope">
          <el-tag v-if="scope.row.status === 'unused'">未使用</el-tag>
          <el-tag v-else-if="scope.row.status === 'activated'" type="success">已激活</el-tag>
          <el-tag v-else-if="scope.row.status === 'expired'" type="info">已过期</el-tag>
          <el-tag v-else-if="scope.row.status === 'disabled'" type="danger">已禁用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="绑定用户" align="center" prop="bindUserId" />
      <el-table-column label="激活时间" align="center" prop="activeTime" width="180">
        <template #default="scope">
          <span>{{ parseTime(scope.row.activeTime) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="过期时间" align="center" prop="expireTime" width="180">
        <template #default="scope">
          <span>{{ parseTime(scope.row.expireTime) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="200">
        <template #default="scope">
          <el-button
            link
            type="primary"
            icon="View"
            @click="handleView(scope.row)"
          >详情</el-button>
          <el-button
            link
            type="danger"
            icon="Delete"
            @click="handleDelete(scope.row)"
            v-hasPermi="['dca:card:remove']"
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

    <!-- 生成卡密对话框 -->
    <el-dialog title="批量生成卡密" v-model="generateOpen" width="600px" append-to-body>
      <el-form ref="generateRef" :model="generateForm" :rules="generateRules" label-width="120px">
        <el-form-item label="卡密类型" prop="cardType">
          <el-select v-model="generateForm.cardType" placeholder="请选择类型">
            <el-option label="时间版" value="time" />
            <el-option label="永久版" value="permanent" />
            <el-option label="次数版" value="count" />
            <el-option label="试用版" value="trial" />
          </el-select>
        </el-form-item>
        <el-form-item label="卡密等级" prop="cardLevel">
          <el-select v-model="generateForm.cardLevel" placeholder="请选择等级">
            <el-option label="基础版" value="basic" />
            <el-option label="专业版" value="pro" />
            <el-option label="旗舰版" value="premium" />
          </el-select>
        </el-form-item>
        <el-form-item label="生成数量" prop="count">
          <el-input-number v-model="generateForm.count" :min="1" :max="1000" />
        </el-form-item>
        <el-form-item label="有效天数" prop="days" v-if="generateForm.cardType === 'time' || generateForm.cardType === 'trial'">
          <el-input-number v-model="generateForm.days" :min="1" :max="3650" />
        </el-form-item>
        <el-form-item label="次数限制" prop="counts" v-if="generateForm.cardType === 'count'">
          <el-input-number v-model="generateForm.counts" :min="1" :max="10000" />
        </el-form-item>
        <el-form-item label="功能开关" prop="featureFlags">
          <el-checkbox-group v-model="featureFlags">
            <el-checkbox label="ai_enabled">AI功能</el-checkbox>
            <el-checkbox label="multi_symbol">多币种</el-checkbox>
            <el-checkbox label="telegram_enabled">Telegram通知</el-checkbox>
            <el-checkbox label="auto_trade">自动交易</el-checkbox>
            <el-checkbox label="advanced_chart">高级图表</el-checkbox>
            <el-checkbox label="api_access">API访问</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="批次号" prop="batchNo">
          <el-input v-model="generateForm.batchNo" placeholder="留空自动生成" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="generateForm.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitGenerate">生成</el-button>
          <el-button @click="generateOpen = false">取消</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 卡密详情对话框 -->
    <el-dialog title="卡密详情" v-model="detailOpen" width="700px" append-to-body>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="卡密">{{ cardDetail.cardKey }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag v-if="cardDetail.status === 'unused'">未使用</el-tag>
          <el-tag v-else-if="cardDetail.status === 'activated'" type="success">已激活</el-tag>
          <el-tag v-else-if="cardDetail.status === 'expired'" type="info">已过期</el-tag>
          <el-tag v-else-if="cardDetail.status === 'disabled'" type="danger">已禁用</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="类型">{{ cardDetail.cardType }}</el-descriptions-item>
        <el-descriptions-item label="等级">{{ cardDetail.cardLevel }}</el-descriptions-item>
        <el-descriptions-item label="有效天数">{{ cardDetail.days }}天</el-descriptions-item>
        <el-descriptions-item label="次数限制">{{ cardDetail.counts }}次</el-descriptions-item>
        <el-descriptions-item label="绑定用户">{{ cardDetail.bindUserId }}</el-descriptions-item>
        <el-descriptions-item label="机器码">{{ cardDetail.bindMachine }}</el-descriptions-item>
        <el-descriptions-item label="激活时间">{{ parseTime(cardDetail.activeTime) }}</el-descriptions-item>
        <el-descriptions-item label="过期时间">{{ parseTime(cardDetail.expireTime) }}</el-descriptions-item>
        <el-descriptions-item label="批次号">{{ cardDetail.batchNo }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ parseTime(cardDetail.createTime) }}</el-descriptions-item>
      </el-descriptions>
      <el-divider>功能开关</el-divider>
      <el-tag v-for="(value, key) in JSON.parse(cardDetail.featureFlags || '{}')" :key="key" style="margin: 5px">
        {{ key }}: {{ value ? '开启' : '关闭' }}
      </el-tag>
    </el-dialog>
  </div>
</template>

<script setup>
import { listCard, getCard, generateCards, delCard, disableCard, exportCards } from "@/api/dca/card";

const { proxy } = getCurrentInstance();

const cardList = ref([]);
const cardDetail = ref({});
const generateOpen = ref(false);
const detailOpen = ref(false);
const loading = ref(true);
const total = ref(0);
const featureFlags = ref([]);

const data = reactive({
  generateForm: {
    cardType: 'time',
    cardLevel: 'basic',
    count: 10,
    days: 30,
    counts: 100,
    batchNo: undefined,
    remark: undefined
  },
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    cardKey: undefined,
    status: undefined,
    cardType: undefined,
    batchNo: undefined
  },
  generateRules: {
    cardType: [{ required: true, message: "请选择卡密类型", trigger: "change" }],
    cardLevel: [{ required: true, message: "请选择卡密等级", trigger: "change" }],
    count: [{ required: true, message: "请输入生成数量", trigger: "blur" }]
  }
});

const { queryParams, generateForm, generateRules } = toRefs(data);

function getList() {
  loading.value = true;
  listCard(queryParams.value).then(response => {
    cardList.value = response.rows;
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

function handleGenerate() {
  generateOpen.value = true;
}

function submitGenerate() {
  proxy.$refs.generateRef.validate(valid => {
    if (valid) {
      const data = { ...generateForm.value };
      data.featureFlags = {};
      featureFlags.value.forEach(flag => {
        data.featureFlags[flag] = true;
      });
      data.featureFlags = JSON.stringify(data.featureFlags);

      generateCards(data).then(() => {
        proxy.$modal.msgSuccess("生成成功");
        generateOpen.value = false;
        getList();
      });
    }
  });
}

function handleView(row) {
  getCard(row.id).then(response => {
    cardDetail.value = response.data;
    detailOpen.value = true;
  });
}

function handleDelete(row) {
  proxy.$modal.confirm('确认删除该卡密？').then(() => {
    return delCard(row.id);
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("删除成功");
  });
}

function handleExport() {
  proxy.download('dca/card/export', {
    ...queryParams.value
  }, `卡密列表_${new Date().getTime()}.xlsx`);
}

getList();
</script>
