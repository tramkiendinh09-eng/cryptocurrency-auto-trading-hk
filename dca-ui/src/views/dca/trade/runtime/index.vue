<!--
  交易运行时监控与配置管理页面

  这是交易系统的核心前端界面，提供运行时配置管理和实时监控功能。

  页面功能:
  1. 运行时配置展示: 显示当前运行模式、风控参数、触发策略等配置
  2. 运行时指标监控: 展示事件数、信号数、决策数、风控命中、持仓盈亏等统计
  3. 实时数据表格:
     - 最近事件(event_raw): 市场行情、新闻、链上、社交等原始事件
     - 最近信号(signal_event): 经过触发策略评估后的信号
     - 活跃信号窗口(signal_window_state): 当前活跃的信号时间窗口
     - 代理结论(agent_conclusion): 各Agent的分析结论
     - 监督者决策(decision_run): 主管Agent的最终决策
     - 风险熔断命中(risk_guard_hit): 风控规则拦截记录
     - 最近成交(trade_action): 实际成交记录
     - 最近订单(exchange_order): 交易所订单状态
     - 当前持仓(position_snapshot): 持仓快照
  4. 配置编辑对话框: 支持编辑运行时配置、触发策略、冷却策略、LLM预算等

  数据流向:
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                           前端数据流                                          │
  ├─────────────────────────────────────────────────────────────────────────────┤
  │                                                                             │
  │  页面加载                                                                    │
  │      │                                                                      │
  │      ▼                                                                      │
  │  loadOverview() ──► GET /dca/trade/runtime/overview                        │
  │      │                                                                      │
  │      ├─► runtimeConfig: 运行时配置                                          │
  │      ├─► executionStats: 执行统计                                           │
  │      ├─► recentEvents: 最近事件列表                                         │
  │      ├─► recentSignals: 最近信号列表                                        │
  │      ├─► activeSignalWindows: 活跃信号窗口                                   │
  │      ├─► recentAgentConclusions: Agent结论                                  │
  │      ├─► recentDecisions: 主管决策                                          │
  │      ├─► recentRiskHits: 风控命中                                           │
  │      ├─► recentTradeActions: 成交记录                                       │
  │      ├─► recentOrders: 订单记录                                             │
  │      └─► recentPositions: 持仓快照                                          │
  │                                                                             │
  │  编辑配置                                                                    │
  │      │                                                                      │
  │      ▼                                                                      │
  │  handleEditRuntimeConfig() ──► 打开编辑对话框                                │
  │      │                                                                      │
  │      ▼                                                                      │
  │  submitRuntimeConfig() ──► PUT /dca/trade/runtime/config                   │
  │      │                                                                      │
  │      └─► 刷新概览数据                                                        │
  │                                                                             │
  └─────────────────────────────────────────────────────────────────────────────┘

  核心组件:
  - runtimeConfig: 运行时配置响应式对象
  - summaryCards: 指标卡片计算属性
  - executionSummaryCards: 执行状态统计卡片
  - activeSignalWindowRows: 活跃信号窗口表格数据
  - recentTradeActionRows: 成交记录表格数据

  配置表单字段:
  - 基础配置: defaultMode, liveEnabled, maxPositionRatio, maxDailyLoss
  - 风控配置: maxConsecutiveFailures, requireAccountBinding, liveOrderRequiresHealthyAccount
  - 触发策略: triggerMode, marketTrigger, newsTrigger, onchainTrigger, socialTrigger
  - 冷却策略: cooldownGlobalSeconds, cooldownSameSourceSeconds
  - LLM预算: llmBudgetPerSymbolDailyLimit, llmBudgetRollingWindowLimit
  - 信号记忆: signalMemoryPolicy (market/news/onchain/social)
  - 触发矩阵: triggerMatrix (信号组合触发规则)
  - 高级参数: runtimeFlagsJson, notifyDefaultsJson

  @author dca-ui
-->
<template>
  <div class="app-container">
    <el-row :gutter="16" class="runtime-grid">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="runtime-summary">
          <template #header>
            <div class="card-header">
              <span>交易运行时</span>
              <div class="card-header__actions">
                <el-tag :type="formatModeTag(overview.runtimeConfig.defaultMode)">
                  {{ formatModeDisplayZh(overview.runtimeConfig.defaultMode) }}
                </el-tag>
                <el-button
                  type="primary"
                  plain
                  size="small"
                  v-hasPermi="['dca:tradeRuntime:edit']"
                  @click="handleEditRuntimeConfig"
                >
                  编辑运行时配置
                </el-button>
              </div>
            </div>
          </template>
          <el-skeleton :rows="3" animated :loading="loading">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="默认模式">
                {{ formatModeDisplayZh(overview.runtimeConfig.defaultMode) }}
              </el-descriptions-item>
              <el-descriptions-item label="生效模式">
                <el-tag :type="formatModeTag(runtimeModeSummary.effectiveMode)">
                  {{ formatModeDisplayZh(runtimeModeSummary.effectiveMode) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="模式状态">
                {{ runtimeModeSummary.summary }}
              </el-descriptions-item>
              <el-descriptions-item label="实盘交易">
                <el-tag :type="overview.runtimeConfig.liveEnabled ? 'danger' : 'info'">
                  {{ overview.runtimeConfig.liveEnabled ? '已启用' : '已禁用' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="最大仓位比例">
                {{ overview.runtimeConfig.maxPositionRatio }}
              </el-descriptions-item>
              <el-descriptions-item label="最大日亏损">
                {{ overview.runtimeConfig.maxDailyLoss }}
              </el-descriptions-item>
              <el-descriptions-item label="最大连续失败次数">
                {{ overview.runtimeConfig.maxConsecutiveFailures }}
              </el-descriptions-item>
              <el-descriptions-item label="允许交易对">
                {{ (runtimeConfigDisplay.allowedSymbols || []).join(', ') }}
              </el-descriptions-item>
              <el-descriptions-item label="允许交易所">
                {{ (runtimeConfigDisplay.allowedExchanges || []).join(', ') }}
              </el-descriptions-item>
              <el-descriptions-item label="账户绑定保护">
                <el-tag :type="overview.runtimeConfig.requireAccountBinding ? 'success' : 'warning'">
                  {{ overview.runtimeConfig.requireAccountBinding ? '必需' : '可选' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="健康账户保护">
                <el-tag :type="overview.runtimeConfig.liveOrderRequiresHealthyAccount ? 'success' : 'warning'">
                  {{ overview.runtimeConfig.liveOrderRequiresHealthyAccount ? '必需' : '可选' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="事件保留周期">
                {{ overview.runtimeConfig.eventRetentionDays || 30 }} 天
              </el-descriptions-item>
              <el-descriptions-item label="回放保留周期">
                {{ overview.runtimeConfig.replayRetentionDays || 30 }} 天
              </el-descriptions-item>
              <el-descriptions-item label="路由调度器">
                {{ overview.runtimeConfig.routeSchedulerMode || 'SERIAL' }}
              </el-descriptions-item>
              <el-descriptions-item label="路由并发数">
                {{ overview.runtimeConfig.routeMaxConcurrency || 1 }}
              </el-descriptions-item>
              <el-descriptions-item label="多轮协商">
                <el-tag :type="overview.runtimeConfig.deliberationEnabled ? 'warning' : 'info'">
                  {{ overview.runtimeConfig.deliberationEnabled ? '已启用' : '已禁用' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="最大轮次">
                {{ overview.runtimeConfig.deliberationMaxRounds ?? 0 }}
              </el-descriptions-item>
              <el-descriptions-item label="失败放行">
                <el-tag :type="overview.runtimeConfig.deliberationFailOpen !== false ? 'success' : 'danger'">
                  {{ overview.runtimeConfig.deliberationFailOpen !== false ? '已启用' : '已禁用' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="触发模式">
                {{ runtimeConfigDisplay.triggerMode }}
              </el-descriptions-item>
              <el-descriptions-item label="市场触发">
                涨跌 {{ runtimeConfigDisplay.marketTriggerPriceChangePct }}% /
                加速度 {{ runtimeConfigDisplay.marketTriggerPriceAccelerationPct }}%
              </el-descriptions-item>
              <el-descriptions-item label="新闻触发">
                分数 {{ runtimeConfigDisplay.newsTriggerScoreThreshold }} /
                等级 {{ runtimeConfigDisplay.newsTriggerSeverityThreshold }}
              </el-descriptions-item>
              <el-descriptions-item label="冷却时间">
                全局 {{ runtimeConfigDisplay.cooldownGlobalSeconds }} 秒 /
                同源 {{ runtimeConfigDisplay.cooldownSameSourceSeconds }} 秒
              </el-descriptions-item>
              <el-descriptions-item label="LLM 预算">
                每交易对 {{ runtimeConfigDisplay.llmBudgetPerSymbolDailyLimit }} 次 /
                {{ runtimeConfigDisplay.llmBudgetRollingWindowLimit }}
                每 {{ runtimeConfigDisplay.llmBudgetRollingWindowMinutes }} 分钟
              </el-descriptions-item>
              <el-descriptions-item label="去重策略">
                {{ runtimeConfigDisplay.dedupeWindowSeconds }} 秒 /
                {{ runtimeConfigDisplay.dedupeSameDirectionOnly ? '仅同方向去重' : '允许跨方向共存' }}
              </el-descriptions-item>
              <el-descriptions-item label="触发矩阵">
                已配置 {{ runtimeConfigDisplay.triggerMatrixRows.length }} 条规则
              </el-descriptions-item>
              <el-descriptions-item label="操作员视图">
                事件、信号、决策、风控、执行与持仓快照会在同一屏持续可追踪。
              </el-descriptions-item>
            </el-descriptions>
          </el-skeleton>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="runtime-summary">
          <template #header>
            <div class="card-header">
              <span>运行时指标</span>
              <el-tag type="warning">{{ formatExecutionTotalLabel(overview.executionStats) }}</el-tag>
            </div>
          </template>
          <el-skeleton :rows="4" animated :loading="loading">
            <div class="metric-grid">
              <div
                v-for="card in summaryCards"
                :key="card.key"
                class="metric-card"
                :class="`metric-card--${card.tone}`"
              >
                <div class="metric-label">{{ card.label }}</div>
                <div class="metric-value">{{ card.value }}</div>
              </div>
            </div>
            <div class="execution-summary">
              <div class="execution-summary__header">执行状态</div>
              <div class="execution-summary__grid">
                <div
                  v-for="card in executionSummaryCards"
                  :key="card.key"
                  class="execution-summary__item"
                >
                  <span class="execution-summary__label">{{ card.label }}</span>
                  <el-tag :type="card.tone" size="small">{{ card.value }}</el-tag>
                </div>
              </div>
            </div>
            <div class="execution-summary">
              <div class="execution-summary__header">分发概览</div>
              <div class="execution-summary__grid">
                <div
                  v-for="card in dispatchOverviewCards"
                  :key="card.key"
                  class="execution-summary__item"
                >
                  <span class="execution-summary__label">{{ card.label }}</span>
                  <el-tag size="small" type="info">{{ card.value }}</el-tag>
                </div>
              </div>
            </div>
          </el-skeleton>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="runtime-grid">
      <el-col :xs="24" :xl="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>最近事件</span>
              <el-tag type="info">event_raw</el-tag>
            </div>
          </template>
          <el-table :data="overview.recentEvents" v-loading="loading" empty-text="暂无事件">
            <el-table-column prop="createdAt" label="时间" min-width="168" />
            <el-table-column prop="eventType" label="类型" width="140" />
            <el-table-column prop="symbol" label="交易对" width="120" />
            <el-table-column prop="exchangeCode" label="交易所" width="120" />
            <el-table-column prop="traceId" label="追踪 ID" min-width="180" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :xl="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>最近信号</span>
              <el-tag type="success">signal_event</el-tag>
            </div>
          </template>
          <el-table :data="overview.recentSignals" v-loading="loading" empty-text="暂无信号">
            <el-table-column prop="createdAt" label="时间" min-width="168" />
            <el-table-column prop="symbol" label="交易对" width="120" />
            <el-table-column prop="signalType" label="信号" min-width="160" />
            <el-table-column prop="traceId" label="追踪 ID" min-width="180" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="runtime-grid">
      <el-col :xs="24">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>活跃信号窗口</span>
              <el-tag type="warning">signal_window_state</el-tag>
            </div>
          </template>
          <el-table :data="activeSignalWindowRows" v-loading="loading" empty-text="暂无活跃窗口">
            <el-table-column prop="windowKey" label="窗口键" min-width="220" />
            <el-table-column prop="symbol" label="交易对" width="120" />
            <el-table-column prop="sourceTypeLabel" label="来源" width="120" />
            <el-table-column prop="signalTypeLabel" label="信号类型" min-width="140" />
            <el-table-column prop="directionLabel" label="方向" width="120" />
            <el-table-column prop="strengthScoreLabel" label="强度" width="120" />
            <el-table-column label="状态" width="120">
              <template #default="scope">
                <el-tag :type="scope.row.statusText === 'active' ? 'success' : scope.row.statusText === 'expired' ? 'danger' : 'info'">
                  {{ scope.row.statusText }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="expiresAt" label="过期时间" min-width="180" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="runtime-grid">
      <el-col :xs="24" :xl="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>代理结论</span>
              <el-tag type="warning">agent_conclusion</el-tag>
            </div>
          </template>
          <el-table :data="overview.recentAgentConclusions" v-loading="loading" empty-text="暂无代理结论">
            <el-table-column prop="createdAt" label="时间" min-width="168" />
            <el-table-column prop="agentName" label="代理" width="140" />
            <el-table-column prop="bias" label="倾向" width="120" />
            <el-table-column prop="confidence" label="置信度" width="120" />
            <el-table-column prop="reason" label="原因" min-width="220" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :xl="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>监督者决策</span>
              <el-tag type="danger">decision_run</el-tag>
            </div>
          </template>
          <el-table :data="overview.recentDecisions" v-loading="loading" empty-text="暂无决策">
            <el-table-column prop="createdAt" label="时间" min-width="168" />
            <el-table-column prop="symbol" label="交易对" width="120" />
            <el-table-column prop="dispatchMode" label="分发模式" width="130" />
            <el-table-column prop="mode" label="运行模式" width="110" />
            <el-table-column prop="action" label="动作" width="140" />
            <el-table-column prop="triggerReason" label="触发原因" min-width="180" show-overflow-tooltip />
            <el-table-column label="执行" width="110">
              <template #default="scope">
                <el-tag :type="executionStatusTag(scope.row.executionStatus)">
                  {{ scope.row.executionStatus || 'pending' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="订单状态" width="120">
              <template #default="scope">
                <el-tag :type="orderStatusTag(scope.row.orderStatus)">
                  {{ scope.row.orderStatus || 'PENDING' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="confidence" label="置信度" width="120" />
            <el-table-column prop="traceId" label="追踪 ID" min-width="180" />
          </el-table>
          <div class="runtime-config__hint runtime-config__hint--compact">
            最近一次选中代理：
            {{ parseOverviewJson(overview.lastSelectedAgentsJson, []).join(', ') || '无' }}
            <br>
            最近一次组合命中：
            {{ parseOverviewJson(overview.lastCombinationMatchJson, {}).code || '无' }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="runtime-grid">
      <el-col :xs="24" :xl="6">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>风险熔断命中</span>
              <el-tag type="danger">risk_guard_hit</el-tag>
            </div>
          </template>
          <el-table :data="overview.recentRiskHits" v-loading="loading" empty-text="暂无风控拦截">
            <el-table-column prop="createdAt" label="时间" min-width="168" />
            <el-table-column prop="ruleCode" label="规则" width="150" />
            <el-table-column prop="traceId" label="追踪 ID" min-width="180" />
            <el-table-column prop="reason" label="原因" min-width="220" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :xl="6">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>最近成交</span>
              <el-tag type="success">trade_action</el-tag>
            </div>
          </template>
          <el-table :data="recentTradeActionRows" v-loading="loading" empty-text="暂无成交">
            <el-table-column prop="createdAt" label="时间" min-width="168" />
            <el-table-column prop="actionText" label="动作" min-width="120" />
            <el-table-column label="方向" min-width="100">
              <template #default="{ row }">
                <el-tag :type="row.positionSide === 'short' ? 'danger' : row.positionSide === 'long' ? 'success' : 'info'" size="small">
                  {{ row.positionSideText }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="openPriceLabel" label="开仓价格" min-width="120" />
            <el-table-column prop="closePriceLabel" label="平仓价格" min-width="120" />
            <el-table-column prop="fillPriceLabel" label="成交价格" min-width="120" />
            <el-table-column prop="fillQuantityLabel" label="成交数量" min-width="120" />
            <el-table-column label="已实现盈亏" min-width="120">
              <template #default="{ row }">
                <span :style="{ color: row.realizedPnlTone === 'success' ? '#67c23a' : row.realizedPnlTone === 'danger' ? '#f56c6c' : '#909399' }">
                  {{ row.realizedPnlLabel }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :xl="6">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>最近订单</span>
              <el-tag type="warning">exchange_order</el-tag>
            </div>
          </template>
          <el-table :data="overview.recentOrders" v-loading="loading" empty-text="暂无订单">
            <el-table-column prop="createdAt" label="时间" min-width="168" />
            <el-table-column prop="symbol" label="交易对" width="120" />
            <el-table-column prop="side" label="方向" width="90" />
            <el-table-column prop="mode" label="运行模式" width="100" />
            <el-table-column label="执行参数" min-width="260" show-overflow-tooltip>
              <template #default="scope">
                {{ formatOrderExecutionMeta(scope.row) }}
              </template>
            </el-table-column>
            <el-table-column label="执行" width="110">
              <template #default="scope">
                <el-tag :type="executionStatusTag(scope.row.status)">
                  {{ scope.row.status || 'pending' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="订单状态" width="120">
              <template #default="scope">
                <el-tag :type="orderStatusTag(scope.row.orderStatus)">
                  {{ scope.row.orderStatus || 'PENDING' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :xl="6">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>当前持仓</span>
              <el-tag type="success">position_snapshot</el-tag>
            </div>
          </template>
          <el-table :data="overview.recentPositions" v-loading="loading" empty-text="暂无持仓">
            <el-table-column prop="symbol" label="交易对" width="120" />
            <el-table-column prop="side" label="方向" width="90">
              <template #default="{ row }">
                <el-tag :type="row.side === 'long' ? 'success' : 'danger'" size="small">
                  {{ row.side === 'long' ? '多' : '空' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="positionQuantity" label="数量" min-width="120" />
            <el-table-column prop="entryPrice" label="开仓价" min-width="120" />
            <el-table-column prop="unrealizedPnl" label="浮盈亏" min-width="120">
              <template #default="{ row }">
                <span :style="{ color: Number(row.unrealizedPnl) > 0 ? '#67c23a' : Number(row.unrealizedPnl) < 0 ? '#f56c6c' : '#909399' }">
                  {{ formatPnl(row.unrealizedPnl) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog
      v-model="runtimeConfigOpen"
      title="编辑运行时配置"
      width="900px"
      append-to-body
      top="5vh"
    >
      <el-form ref="runtimeConfigRef" :model="runtimeConfigForm" :rules="runtimeConfigTabRules.basic" label-width="120px">
        <el-tabs v-model="runtimeConfigActiveTab" type="border-card">
          <!-- 基础配置 -->
          <el-tab-pane label="基础配置" name="basic">
            <el-form-item label="默认模式" prop="defaultMode">
              <el-select v-model="runtimeConfigForm.defaultMode" placeholder="请选择模式" style="width: 100%">
                <el-option
                  v-for="option in runtimeModeOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="实盘交易" prop="liveEnabled">
              <el-switch v-model="runtimeConfigForm.liveEnabled" />
            </el-form-item>
            <el-form-item label="最大仓位比例" prop="maxPositionRatio">
              <el-input-number v-model="runtimeConfigForm.maxPositionRatio" :min="0.01" :max="1" :step="0.01" style="width: 100%" />
            </el-form-item>
            <el-form-item label="最大日亏损" prop="maxDailyLoss">
              <el-input-number v-model="runtimeConfigForm.maxDailyLoss" :step="50" style="width: 100%" />
            </el-form-item>
            <el-form-item label="最大连续失败次数" prop="maxConsecutiveFailures">
              <el-input-number v-model="runtimeConfigForm.maxConsecutiveFailures" :min="1" :max="20" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="允许交易对" prop="allowedSymbols">
              <el-select v-model="runtimeConfigForm.allowedSymbols" multiple placeholder="请选择交易对" style="width: 100%">
                <el-option v-for="symbol in runtimeSymbolOptions" :key="symbol" :label="symbol" :value="symbol" />
              </el-select>
            </el-form-item>
            <el-form-item label="允许交易所" prop="allowedExchanges">
              <el-select v-model="runtimeConfigForm.allowedExchanges" multiple placeholder="请选择交易所" style="width: 100%">
                <el-option v-for="exchange in runtimeExchangeOptions" :key="exchange" :label="exchange" :value="exchange" />
              </el-select>
            </el-form-item>
            <el-form-item label="要求账户绑定" prop="requireAccountBinding">
              <el-switch v-model="runtimeConfigForm.requireAccountBinding" />
            </el-form-item>
            <el-form-item label="仅健康账户可实盘" prop="liveOrderRequiresHealthyAccount">
              <el-switch v-model="runtimeConfigForm.liveOrderRequiresHealthyAccount" />
            </el-form-item>
            <el-form-item label="数据缺口全阻断" prop="haltOnDataGap">
              <el-switch v-model="runtimeConfigForm.haltOnDataGap" />
            </el-form-item>
            <el-form-item label="事件保留天数" prop="eventRetentionDays">
              <el-input-number v-model="runtimeConfigForm.eventRetentionDays" :min="1" :max="365" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="回放保留天数" prop="replayRetentionDays">
              <el-input-number v-model="runtimeConfigForm.replayRetentionDays" :min="1" :max="365" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="路由调度器" prop="routeSchedulerMode">
              <el-select v-model="runtimeConfigForm.routeSchedulerMode" placeholder="请选择调度器" style="width: 100%">
                <el-option
                  v-for="option in routeSchedulerOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="路由并发数" prop="routeMaxConcurrency">
              <el-input-number v-model="runtimeConfigForm.routeMaxConcurrency" :min="1" :max="16" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="多轮协商" prop="deliberationEnabled">
              <el-switch v-model="runtimeConfigForm.deliberationEnabled" />
            </el-form-item>
            <el-form-item label="最大轮次" prop="deliberationMaxRounds">
              <el-input-number v-model="runtimeConfigForm.deliberationMaxRounds" :min="0" :max="2" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="失败放行" prop="deliberationFailOpen">
              <el-switch v-model="runtimeConfigForm.deliberationFailOpen" />
            </el-form-item>
          </el-tab-pane>

          <!-- 触发策略 -->
          <el-tab-pane label="触发策略" name="trigger">
            <el-form-item label="触发模式" prop="triggerMode">
              <el-input v-model="runtimeConfigForm.triggerMode" placeholder="EVENT_GATED" />
            </el-form-item>
            <el-form-item label="规则波动阈值 %" prop="marketTriggerRuleOnlyPriceChangePct">
              <el-input-number v-model="runtimeConfigForm.marketTriggerRuleOnlyPriceChangePct" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="市场波动阈值 %" prop="marketTriggerPriceChangePct">
              <el-input-number v-model="runtimeConfigForm.marketTriggerPriceChangePct" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="市场加速度阈值 %" prop="marketTriggerPriceAccelerationPct">
              <el-input-number v-model="runtimeConfigForm.marketTriggerPriceAccelerationPct" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="资金费率阈值" prop="marketTriggerFundingRateAbs">
              <el-input-number v-model="runtimeConfigForm.marketTriggerFundingRateAbs" :min="0" :step="0.0001" :precision="4" style="width: 100%" />
            </el-form-item>
            <el-form-item label="标记价偏离 %" prop="marketTriggerMarkPriceDeviationPct">
              <el-input-number v-model="runtimeConfigForm.marketTriggerMarkPriceDeviationPct" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="清算金额 USD" prop="marketTriggerLiquidationNotionalUsd">
              <el-input-number v-model="runtimeConfigForm.marketTriggerLiquidationNotionalUsd" :min="0" :step="50000" style="width: 100%" />
            </el-form-item>
            <el-form-item label="K线15m波动 %" prop="marketTriggerKlinePriceChangePct15m">
              <el-input-number v-model="runtimeConfigForm.marketTriggerKlinePriceChangePct15m" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="K线60m波动 %" prop="marketTriggerKlinePriceChangePct60m">
              <el-input-number v-model="runtimeConfigForm.marketTriggerKlinePriceChangePct60m" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="K线240m波动 %" prop="marketTriggerKlinePriceChangePct240m">
              <el-input-number v-model="runtimeConfigForm.marketTriggerKlinePriceChangePct240m" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="15m爆仓聚合 USD" prop="marketTriggerLiquidationNotional15mUsd">
              <el-input-number v-model="runtimeConfigForm.marketTriggerLiquidationNotional15mUsd" :min="0" :step="50000" style="width: 100%" />
            </el-form-item>
            <el-form-item label="60m爆仓聚合 USD" prop="marketTriggerLiquidationNotional60mUsd">
              <el-input-number v-model="runtimeConfigForm.marketTriggerLiquidationNotional60mUsd" :min="0" :step="50000" style="width: 100%" />
            </el-form-item>
            <el-form-item label="240m爆仓聚合 USD" prop="marketTriggerLiquidationNotional240mUsd">
              <el-input-number v-model="runtimeConfigForm.marketTriggerLiquidationNotional240mUsd" :min="0" :step="50000" style="width: 100%" />
            </el-form-item>
            <el-form-item label="新闻分数阈值" prop="newsTriggerScoreThreshold">
              <el-input-number v-model="runtimeConfigForm.newsTriggerScoreThreshold" :min="0" :max="1" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="新闻等级阈值" prop="newsTriggerSeverityThreshold">
              <el-input v-model="runtimeConfigForm.newsTriggerSeverityThreshold" placeholder="high" />
            </el-form-item>
            <el-form-item label="链上资金流 USD" prop="onchainTriggerFlowUsdThreshold">
              <el-input-number v-model="runtimeConfigForm.onchainTriggerFlowUsdThreshold" :min="0" :step="100000" style="width: 100%" />
            </el-form-item>
            <el-form-item label="链上净流偏置" prop="onchainTriggerExchangeNetflowBias">
              <el-input-number v-model="runtimeConfigForm.onchainTriggerExchangeNetflowBias" :min="0" :max="1" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="社交分数阈值" prop="socialTriggerScoreThreshold">
              <el-input-number v-model="runtimeConfigForm.socialTriggerScoreThreshold" :min="0" :max="1" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="社交突发数" prop="socialTriggerBurstCount">
              <el-input-number v-model="runtimeConfigForm.socialTriggerBurstCount" :min="1" :step="1" style="width: 100%" />
            </el-form-item>
          </el-tab-pane>

          <!-- 市场增强 -->
          <el-tab-pane label="市场增强" name="enhancement">
            <el-form-item label="启用增强" prop="marketDataEnhancementEnabled">
              <el-switch v-model="runtimeConfigForm.marketDataEnhancementEnabled" />
            </el-form-item>
            <el-form-item label="REST兜底" prop="marketDataRestFallbackEnabled">
              <el-switch v-model="runtimeConfigForm.marketDataRestFallbackEnabled" />
            </el-form-item>
            <el-form-item label="启用K线" prop="marketDataKlineEnabled">
              <el-switch v-model="runtimeConfigForm.marketDataKlineEnabled" />
            </el-form-item>
            <el-form-item label="K线周期" prop="marketDataKlineIntervalsText">
              <el-input v-model="runtimeConfigForm.marketDataKlineIntervalsText" placeholder="1m, 15m, 1h, 4h" />
            </el-form-item>
            <el-form-item label="K线条数" prop="marketDataKlineLimit">
              <el-input-number v-model="runtimeConfigForm.marketDataKlineLimit" :min="1" :max="300" :step="10" style="width: 100%" />
            </el-form-item>
            <el-form-item label="爆仓聚合窗口" prop="marketDataLiquidationWindowsText">
              <el-input v-model="runtimeConfigForm.marketDataLiquidationWindowsText" placeholder="15, 60, 240" />
            </el-form-item>
            <el-form-item label="主管失败放行" prop="supervisorAiFailOpen">
              <el-switch v-model="runtimeConfigForm.supervisorAiFailOpen" />
              <div class="runtime-config__form-tip">仅建议 paper/shadow 调试使用，live 后端会强制保持失败关闭。</div>
            </el-form-item>
          </el-tab-pane>

          <!-- 威科夫短线 -->
          <el-tab-pane label="威科夫短线" name="wyckoff">
            <el-form-item label="启用策略" prop="wyckoffShorttermEnabled">
              <el-switch v-model="runtimeConfigForm.wyckoffShorttermEnabled" />
            </el-form-item>
            <el-form-item label="15m最少K线" prop="wyckoffShorttermMin15mBars">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermMin15mBars" :min="1" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="量价回看K线" prop="wyckoffShorttermEffortLookbackBars">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermEffortLookbackBars" :min="2" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="突破幅度 %" prop="wyckoffShorttermBreakoutChangePct">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermBreakoutChangePct" :min="0" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="突破量比" prop="wyckoffShorttermBreakoutVolumeRatio">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermBreakoutVolumeRatio" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="确认幅度 %" prop="wyckoffShorttermConfirmedBreakoutChangePct">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermConfirmedBreakoutChangePct" :min="0" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="确认量比" prop="wyckoffShorttermConfirmedBreakoutVolumeRatio">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermConfirmedBreakoutVolumeRatio" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="Spring幅度 %" prop="wyckoffShorttermSpringChangePct">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermSpringChangePct" :min="0" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="Spring量比" prop="wyckoffShorttermSpringVolumeRatio">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermSpringVolumeRatio" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="大级别冲突 %" prop="wyckoffShorttermHigherTimeframeConflictPct">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermHigherTimeframeConflictPct" :min="0" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="大级别确认 %" prop="wyckoffShorttermHigherTimeframeConfirmPct">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermHigherTimeframeConfirmPct" :min="0" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="震荡变化 %" prop="wyckoffShorttermRangeBalanceChangePct">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermRangeBalanceChangePct" :min="0" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="震荡区间 %" prop="wyckoffShorttermRangeBalanceRangePct">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermRangeBalanceRangePct" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="标记价惩罚 %" prop="wyckoffShorttermMarkDeviationPenaltyPct">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermMarkDeviationPenaltyPct" :min="0" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="要求回踩" prop="wyckoffShorttermRequireRetestForReady">
              <el-switch v-model="runtimeConfigForm.wyckoffShorttermRequireRetestForReady" />
            </el-form-item>
            <el-form-item label="回踩距离 %" prop="wyckoffShorttermRetestMaxDistancePct">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermRetestMaxDistancePct" :min="0" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="最大追价 %" prop="wyckoffShorttermMaxReadyExtensionPct">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermMaxReadyExtensionPct" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="诱多空量比" prop="wyckoffShorttermTrapVolumeRatio">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermTrapVolumeRatio" :min="0" :step="0.1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="影线比例" prop="wyckoffShorttermTrapWickRatio">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermTrapWickRatio" :min="0" :max="1" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="诱骗冷却K线" prop="wyckoffShorttermTrapCooldownBars">
              <el-input-number v-model="runtimeConfigForm.wyckoffShorttermTrapCooldownBars" :min="0" :step="1" style="width: 100%" />
              <div class="runtime-config__form-tip">ready 必须先通过确认、回踩、不过度延伸、诱骗风险过滤；watch 只给审议上下文，不直接触发方向。</div>
            </el-form-item>
          </el-tab-pane>

          <!-- 冷却预算 -->
          <el-tab-pane label="冷却预算" name="cooldown">
            <el-divider>冷却策略</el-divider>
            <el-form-item label="全局冷却" prop="cooldownGlobalSeconds">
              <el-input-number v-model="runtimeConfigForm.cooldownGlobalSeconds" :min="0" :step="30" style="width: 100%" />
            </el-form-item>
            <el-form-item label="同源冷却" prop="cooldownSameSourceSeconds">
              <el-input-number v-model="runtimeConfigForm.cooldownSameSourceSeconds" :min="0" :step="30" style="width: 100%" />
            </el-form-item>
            <el-form-item label="回放绕过冷却" prop="cooldownReplayBypass">
              <el-switch v-model="runtimeConfigForm.cooldownReplayBypass" />
            </el-form-item>
            <el-divider>LLM预算</el-divider>
            <el-form-item label="每日预算" prop="llmBudgetPerSymbolDailyLimit">
              <el-input-number v-model="runtimeConfigForm.llmBudgetPerSymbolDailyLimit" :min="0" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="预算窗口分钟数" prop="llmBudgetRollingWindowMinutes">
              <el-input-number v-model="runtimeConfigForm.llmBudgetRollingWindowMinutes" :min="1" :step="5" style="width: 100%" />
            </el-form-item>
            <el-form-item label="窗口预算上限" prop="llmBudgetRollingWindowLimit">
              <el-input-number v-model="runtimeConfigForm.llmBudgetRollingWindowLimit" :min="0" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="预算耗尽转规则" prop="llmBudgetExhaustToRuleOnly">
              <el-switch v-model="runtimeConfigForm.llmBudgetExhaustToRuleOnly" />
            </el-form-item>
            <el-divider>去重策略</el-divider>
            <el-form-item label="去重窗口" prop="dedupeWindowSeconds">
              <el-input-number v-model="runtimeConfigForm.dedupeWindowSeconds" :min="0" :step="30" style="width: 100%" />
            </el-form-item>
            <el-form-item label="仅同方向去重" prop="dedupeSameDirectionOnly">
              <el-switch v-model="runtimeConfigForm.dedupeSameDirectionOnly" />
            </el-form-item>
            <el-form-item label="优先保留更强信号" prop="dedupePreferHigherStrength">
              <el-switch v-model="runtimeConfigForm.dedupePreferHigherStrength" />
            </el-form-item>
            <el-divider>信号记忆</el-divider>
            <div
              v-for="row in runtimeConfigForm.signalMemoryRows"
              :key="row.source"
              class="policy-grid"
            >
              <div class="policy-grid__title">{{ row.source.toUpperCase() }}</div>
              <el-form-item :label="`${row.source} TTL`">
                <el-input-number v-model="row.ttlSeconds" :min="0" :step="60" style="width: 100%" />
              </el-form-item>
              <el-form-item :label="`${row.source} 衰减模式`">
                <el-select v-model="row.decayMode" style="width: 100%">
                  <el-option
                    v-for="option in runtimeDecayModeOptions"
                    :key="option"
                    :label="option"
                    :value="option"
                  />
                </el-select>
              </el-form-item>
              <el-form-item :label="`${row.source} 合并窗口`">
                <el-input-number v-model="row.combineWithinSeconds" :min="0" :step="60" style="width: 100%" />
              </el-form-item>
            </div>
          </el-tab-pane>

          <!-- 高级配置 -->
          <el-tab-pane label="高级配置" name="advanced">
            <el-divider>触发矩阵</el-divider>
            <div
              v-for="(row, index) in runtimeConfigForm.triggerMatrixRows"
              :key="`${row.code}-${index}`"
              class="policy-grid"
            >
              <div class="policy-grid__title">规则 {{ index + 1 }}</div>
              <el-form-item label="规则编码">
                <el-input v-model="row.code" placeholder="strong_news_then_break" />
              </el-form-item>
              <el-form-item label="来源组合">
                <el-input v-model="row.sourcesText" placeholder="news, market" />
              </el-form-item>
              <el-form-item label="分发模式">
                <el-select v-model="row.targetDispatchMode" style="width: 100%">
                  <el-option
                    v-for="option in runtimeTriggerDispatchOptions"
                    :key="option"
                    :label="option"
                    :value="option"
                  />
                </el-select>
              </el-form-item>
            </div>
            <el-divider>运行时 Flags JSON</el-divider>
            <div class="runtime-config__guide">
              <div class="runtime-config__guide-title">运行时 Flags JSON 说明</div>
              <div
                v-for="section in runtimeFlagsJsonGuideSections"
                :key="section.title"
                class="runtime-config__guide-section"
              >
                <div class="runtime-config__guide-label">{{ section.title }}</div>
                <ul class="runtime-config__guide-list">
                  <li v-for="item in section.items" :key="item">{{ item }}</li>
                </ul>
              </div>
              <div class="runtime-config__guide-label">可直接粘贴的示例</div>
              <pre class="runtime-config__guide-code">{{ runtimeFlagsJsonExample }}</pre>
            </div>
            <el-form-item label="高级运行参数" prop="runtimeFlagsJson">
              <TradeAdvancedJsonEditor
                v-model="runtimeConfigForm.runtimeFlagsJson"
                title="运行时 Flags JSON"
                description="这里保留结构化表单未覆盖的运行时开关和兼容字段。"
                placeholder='{"haltOnDataGap":true}'
                :rows="5"
              />
            </el-form-item>
            <el-form-item label="通知默认值" prop="notifyDefaultsJson">
              <TradeAdvancedJsonEditor
                v-model="runtimeConfigForm.notifyDefaultsJson"
                title="通知默认值 JSON"
                description="默认通知渠道等低频配置保留在这里，避免占用主表单空间。"
                placeholder='{"channels":["OPS"]}'
                :rows="4"
              />
            </el-form-item>
            <div class="runtime-config__hint">
              基线说明：运行白名单、绑定保护、账户健康门槛、保留窗口以及高级 JSON 默认值都会持久化到 MySQL，并由 Python 运行时读取。
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="runtimeConfigOpen = false">取消</el-button>
          <el-button
            type="primary"
            :loading="runtimeConfigSaving"
            v-hasPermi="['dca:tradeRuntime:edit']"
            @click="submitRuntimeConfig"
          >
            保存
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
/**
 * 工具函数模块 - 运行时配置解析与格式化
 *
 * 本模块提供运行时配置的解析、格式化、验证等工具函数。
 *
 * 主要功能:
 * 1. 模式格式化: formatModeTag, formatModeLabel, formatModeDisplayZh
 * 2. 模式解析: resolveEffectiveRuntimeMode, buildRuntimeModeSummary
 * 3. 配置解析: createRuntimeConfigForm, buildRuntimeConfigPayload
 * 4. 触发策略解析: resolveRuntimeFlags, buildRuntimeFlagsPayload
 * 5. 数据格式化: buildSummaryCards, buildExecutionSummary
 * 6. JSON解析工具: parseJsonList, parseObjectJson, prettyJson
 *
 * 配置解析流程:
 * ```
 * 后端配置(config)
 *     │
 *     ▼
 * resolveRuntimeFlags() ──► 解析runtimeFlagsJson
 *     │
 *     ├─► marketTrigger: 市场触发阈值
 *     ├─► newsTrigger: 新闻触发阈值
 *     ├─► onchainTrigger: 链上触发阈值
 *     ├─► socialTrigger: 社交触发阈值
 *     ├─► signalMemoryPolicy: 信号记忆策略
 *     ├─► triggerMatrix: 触发矩阵
 *     ├─► cooldownPolicy: 冷却策略
 *     ├─► llmBudgetPolicy: LLM预算策略
 *     └─► dedupePolicy: 去重策略
 *     │
 *     ▼
 * createRuntimeConfigForm() ──► 构建表单对象
 * ```
 */

import {
  executionStatusTag as mapExecutionStatusTag,
  orderStatusTag as mapOrderStatusTag
} from '@/utils/tradeExecutionStatus'
import { formatTradeLabel } from '@/utils/tradeLabels'

export { mapExecutionStatusTag as executionStatusTag, mapOrderStatusTag as orderStatusTag }

/**
 * 标准化运行模式字符串
 *
 * @param {string} mode - 原始模式值
 * @returns {string} 标准化后的模式(paper/shadow/live)
 */
export function normalizeMode(mode) {
  return String(mode || 'paper').trim().toLowerCase()
}

export function formatModeTag(mode) {
  const normalized = normalizeMode(mode)
  if (normalized === 'live') {
    return 'danger'
  }
  if (normalized === 'shadow') {
    return 'warning'
  }
  return 'info'
}

export function formatModeLabel(mode) {
  return normalizeMode(mode).toUpperCase()
}

export function formatModeDisplayZh(mode) {
  const normalized = normalizeMode(mode)
  if (normalized === 'live') {
    return '实盘'
  }
  if (normalized === 'shadow') {
    return '影子'
  }
  return '模拟'
}

export function resolveEffectiveRuntimeMode(config = {}) {
  const requestedMode = normalizeMode(config.defaultMode)
  if (requestedMode === 'live' && !config.liveEnabled) {
    return 'shadow'
  }
  return requestedMode
}

export function buildRuntimeModeSummary(config = {}) {
  const requestedMode = normalizeMode(config.defaultMode)
  const effectiveMode = resolveEffectiveRuntimeMode(config)
  const modeDowngraded = requestedMode !== effectiveMode
  if (modeDowngraded) {
    return {
      requestedMode,
      effectiveMode,
      modeDowngraded,
      summary: '已请求实盘，但因实盘交易未启用，当前生效为影子模式'
    }
  }
  if (effectiveMode === 'live') {
    return {
      requestedMode,
      effectiveMode,
      modeDowngraded,
      summary: config.liveOrderRequiresHealthyAccount === false
        ? '当前为实盘模式，健康账户保护为可选'
        : '当前为实盘模式，且要求账户处于健康状态'
    }
  }
  return {
    requestedMode,
    effectiveMode,
    modeDowngraded,
    summary: `${formatModeDisplayZh(effectiveMode)}模式生效中`
  }
}

export const runtimeSymbolOptions = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
// 交易所选项从后端获取，此处保留默认值作为后备
export const runtimeExchangeOptions = ['BINANCE', 'OKX']
export const runtimeSignalSources = ['market', 'news', 'onchain', 'social']
export const runtimeTriggerDispatchOptions = ['NO_DISPATCH', 'RULE_ONLY', 'LLM_ALLOWED']
export const runtimeDecayModeOptions = ['linear', 'step']
/**
 * 默认运行时标志配置
 *
 * 定义运行时触发策略的默认值，包括:
 * - marketTrigger: 市场触发阈值(价格波动、清算金额、资金费率等)
 * - marketDataEnhancement: 市场数据增强配置(K线、爆仓聚合等)
 * - newsTrigger: 新闻触发阈值(分数、等级)
 * - onchainTrigger: 链上触发阈值(资金流、净流偏置)
 * - socialTrigger: 社交触发阈值(分数、突发数)
 * - signalMemoryPolicy: 信号记忆策略(TTL、衰减模式、合并窗口)
 * - triggerMatrix: 触发矩阵(信号组合规则)
 * - cooldownPolicy: 冷却策略(全局冷却、同源冷却)
 * - llmBudgetPolicy: LLM预算策略(每日限制、滑动窗口)
 * - dedupePolicy: 去重策略(去重窗口、方向限制)
 */
export const defaultRuntimeFlags = {
  triggerMode: 'EVENT_GATED',
  marketTrigger: {
    ruleOnlyPriceChangePct: 1.0,
    priceChangePct: 2.5,
    priceAccelerationPct: 1.2,
    liquidationNotionalUsd: 250000,
    klinePriceChangePct15m: 1.0,
    klinePriceChangePct60m: 2.0,
    klinePriceChangePct240m: 4.0,
    liquidationNotional15mUsd: 250000,
    liquidationNotional60mUsd: 500000,
    liquidationNotional240mUsd: 1000000,
    fundingRateAbs: 0,
    markPriceDeviationPct: 0
  },
  marketDataEnhancement: {
    enabled: true,
    restFallbackEnabled: true,
    klineEnabled: true,
    klineIntervals: ['1m', '3m', '15m', '1h', '4h'],
    klineLimit: 120,
    liquidationAggregateWindowsMinutes: [15, 60, 240]
  },
  wyckoffShortterm: {
    enabled: true,
    min15mBars: 8,
    effortLookbackBars: 4,
    breakoutChangePct: 0.15,
    breakoutVolumeRatio: 0.9,
    confirmedBreakoutChangePct: 0.35,
    confirmedBreakoutVolumeRatio: 1.2,
    springChangePct: 0.08,
    springVolumeRatio: 0.9,
    higherTimeframeConflictPct: 0.15,
    higherTimeframeConfirmPct: 0.35,
    rangeBalanceChangePct: 0.4,
    rangeBalanceRangePct: 2.0,
    markDeviationPenaltyPct: 0.3,
    requireRetestForReady: true,
    retestMaxDistancePct: 0.25,
    maxReadyExtensionPct: 0.9,
    trapVolumeRatio: 1.8,
    trapWickRatio: 0.45,
    trapCooldownBars: 2
  },
  newsTrigger: {
    scoreThreshold: 0.8,
    severityThreshold: 'high'
  },
  onchainTrigger: {
    flowUsdThreshold: 500000,
    exchangeNetflowBias: 0.65
  },
  socialTrigger: {
    scoreThreshold: 0.75,
    burstCount: 3
  },
  signalMemoryPolicy: {
    market: { ttlSeconds: 180, decayMode: 'linear', combineWithinSeconds: 120 },
    news: { ttlSeconds: 900, decayMode: 'linear', combineWithinSeconds: 900 },
    onchain: { ttlSeconds: 3600, decayMode: 'step', combineWithinSeconds: 2400 },
    social: { ttlSeconds: 600, decayMode: 'linear', combineWithinSeconds: 600 }
  },
  triggerMatrix: [
    { code: 'strong_news_then_break', sources: ['news', 'market'], targetDispatchMode: 'LLM_ALLOWED' },
    { code: 'onchain_flow_then_market_weakness', sources: ['onchain', 'market'], targetDispatchMode: 'LLM_ALLOWED' },
    { code: 'social_then_news_confirmation', sources: ['social', 'news'], targetDispatchMode: 'RULE_ONLY' }
  ],
  cooldownPolicy: {
    globalSeconds: 300,
    sameSourceSeconds: 180,
    replayBypass: true
  },
  llmBudgetPolicy: {
    perSymbolDailyLimit: 6,
    rollingWindowMinutes: 60,
    rollingWindowLimit: 2,
    exhaustToRuleOnly: true
  },
  dedupePolicy: {
    sameDirectionOnly: true,
    dedupeWindowSeconds: 300,
    preferHigherStrength: true
  }
}

export const runtimeFlagsJsonGuideSections = [
  {
    title: 'marketTrigger 字段说明',
    items: [
      'marketTrigger.ruleOnlyPriceChangePct：弱波动阈值，低于该值时优先走规则，尽量不调 market_agent LLM。',
      'marketTrigger.priceChangePct：强波动阈值，达到后市场信号会升级为允许调 LLM 的强事件。',
      'marketTrigger.priceAccelerationPct：价格加速度触发阈值，适合识别短时加速行情异动。',
      'marketTrigger.liquidationNotionalUsd：爆仓名义金额阈值，只有达到该值才把 liquidation 视为显著市场事件。',
      'marketTrigger.klinePriceChangePct15m/60m/240m：REST K线窗口涨跌幅阈值，用于补足单点 ticker 无法识别的短线波动。',
      'marketTrigger.liquidationNotional15mUsd/60mUsd/240mUsd：爆仓聚合窗口阈值，用于过滤孤立小额爆仓。',
      'marketTrigger.fundingRateAbs：资金费率绝对值阈值，只有达到该值才把 funding_rate 视为值得调模型的显著事件。',
      'marketTrigger.markPriceDeviationPct：标记价格相对最新成交价的偏离阈值，只有达到该值才把 mark_price 视为显著事件。'
    ]
  },
  {
    title: '使用说明',
    items: [
      'priceChangePct、priceAccelerationPct、liquidationNotionalUsd、fundingRateAbs、markPriceDeviationPct 已有结构化表单。',
      'marketDataEnhancement 可配置 OKX REST 衍生指标、K线周期、K线条数与爆仓聚合窗口。',
      '高级 JSON 中写入的 marketTrigger 扩展字段会在前端保存时保留，不会再被结构化表单覆盖丢失。'
    ]
  }
]

export const runtimeFlagsJsonExample = `{
  "marketTrigger": {
    "ruleOnlyPriceChangePct": 1.0,
    "priceChangePct": 2.5,
    "priceAccelerationPct": 1.2,
    "liquidationNotionalUsd": 250000,
    "klinePriceChangePct15m": 1.0,
    "liquidationNotional60mUsd": 500000,
    "fundingRateAbs": 0.001,
    "markPriceDeviationPct": 1.0
  },
  "marketDataEnhancement": {
    "enabled": true,
    "restFallbackEnabled": true,
    "klineEnabled": true,
    "klineIntervals": ["1m", "15m", "1h"],
    "klineLimit": 120,
    "liquidationAggregateWindowsMinutes": [15, 60, 240]
  },
  "wyckoffShortterm": {
    "enabled": true,
    "requireRetestForReady": true,
    "maxReadyExtensionPct": 0.9,
    "trapVolumeRatio": 1.8,
    "trapWickRatio": 0.45,
    "trapCooldownBars": 2
  }
}`

/**
 * 解析JSON列表字段
 *
 * 将JSON字符串或数组解析为字符串列表。
 *
 * @param {string|Array} rawValue - 原始值(JSON字符串或数组)
 * @param {Array} fallback - 解析失败时的默认值
 * @returns {Array<string>} 解析后的字符串列表
 */
function parseJsonList(rawValue, fallback = []) {
  if (!rawValue) {
    return [...fallback]
  }
  try {
    const parsed = typeof rawValue === 'string' ? JSON.parse(rawValue) : rawValue
    return Array.isArray(parsed) ? parsed.map((item) => String(item || '').trim()).filter(Boolean) : [...fallback]
  } catch {
    return [...fallback]
  }
}

function stringifyJson(value, fallback = '{}') {
  if (!value || !String(value).trim()) {
    return fallback
  }
  const parsed = typeof value === 'string' ? JSON.parse(value) : value
  return JSON.stringify(parsed)
}

function prettyJson(value, fallback = '{}') {
  try {
    const serialized = stringifyJson(value, fallback)
    return JSON.stringify(JSON.parse(serialized), null, 2)
  } catch {
    return fallback
  }
}

function parseObjectJson(rawValue, fallback = {}) {
  if (!rawValue) {
    return { ...fallback }
  }
  try {
    const parsed = typeof rawValue === 'string' ? JSON.parse(rawValue) : rawValue
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : { ...fallback }
  } catch {
    return { ...fallback }
  }
}

function normalizeSignalMemoryRows(signalMemoryPolicy = {}) {
  return runtimeSignalSources.map((source) => {
    const policy = signalMemoryPolicy?.[source] || defaultRuntimeFlags.signalMemoryPolicy[source] || {}
    return {
      source,
      ttlSeconds: Number(policy.ttlSeconds ?? defaultRuntimeFlags.signalMemoryPolicy[source].ttlSeconds),
      decayMode: String(policy.decayMode || defaultRuntimeFlags.signalMemoryPolicy[source].decayMode),
      combineWithinSeconds: Number(
        policy.combineWithinSeconds ?? defaultRuntimeFlags.signalMemoryPolicy[source].combineWithinSeconds
      )
    }
  })
}

function normalizeTriggerMatrixRows(triggerMatrix = []) {
  const normalized = Array.isArray(triggerMatrix) ? triggerMatrix : defaultRuntimeFlags.triggerMatrix
  return normalized.map((item, index) => ({
    code: String(item?.code || `trigger_rule_${index + 1}`).trim(),
    sourcesText: Array.isArray(item?.sources) ? item.sources.join(', ') : String(item?.sources || '').trim(),
    targetDispatchMode: String(
      item?.targetDispatchMode || item?.target_dispatch_mode || item?.upgradeTo || item?.upgrade_to || 'RULE_ONLY'
    ).trim().toUpperCase()
  }))
}

/**
 * 解析运行时标志配置
 *
 * 从配置对象中解析并合并运行时标志，优先级:
 * 1. config顶层字段
 * 2. config.runtimeFlagsJson中的字段
 * 3. defaultRuntimeFlags默认值
 *
 * @param {Object} config - 配置对象
 * @returns {Object} 解析后的运行时标志对象
 */
function resolveRuntimeFlags(config = {}) {
  const rawFlags = parseObjectJson(config.runtimeFlagsJson, defaultRuntimeFlags)
  return {
    triggerMode: String(config.triggerMode || rawFlags.triggerMode || defaultRuntimeFlags.triggerMode).trim().toUpperCase(),
    marketTrigger: {
      ...defaultRuntimeFlags.marketTrigger,
      ...parseObjectJson(rawFlags.marketTrigger, defaultRuntimeFlags.marketTrigger),
      ...parseObjectJson(config.marketTrigger, {})
    },
    marketDataEnhancement: {
      ...defaultRuntimeFlags.marketDataEnhancement,
      ...parseObjectJson(rawFlags.marketDataEnhancement, defaultRuntimeFlags.marketDataEnhancement),
      ...parseObjectJson(config.marketDataEnhancement, {})
    },
    wyckoffShortterm: {
      ...defaultRuntimeFlags.wyckoffShortterm,
      ...parseObjectJson(rawFlags.wyckoffShortterm, defaultRuntimeFlags.wyckoffShortterm),
      ...parseObjectJson(config.wyckoffShortterm, {})
    },
    newsTrigger: {
      ...defaultRuntimeFlags.newsTrigger,
      ...parseObjectJson(rawFlags.newsTrigger, defaultRuntimeFlags.newsTrigger),
      ...parseObjectJson(config.newsTrigger, {})
    },
    onchainTrigger: {
      ...defaultRuntimeFlags.onchainTrigger,
      ...parseObjectJson(rawFlags.onchainTrigger, defaultRuntimeFlags.onchainTrigger),
      ...parseObjectJson(config.onchainTrigger, {})
    },
    socialTrigger: {
      ...defaultRuntimeFlags.socialTrigger,
      ...parseObjectJson(rawFlags.socialTrigger, defaultRuntimeFlags.socialTrigger),
      ...parseObjectJson(config.socialTrigger, {})
    },
    signalMemoryPolicy: {
      ...defaultRuntimeFlags.signalMemoryPolicy,
      ...parseObjectJson(rawFlags.signalMemoryPolicy, defaultRuntimeFlags.signalMemoryPolicy),
      ...parseObjectJson(config.signalMemoryPolicy, {})
    },
    triggerMatrix: Array.isArray(config.triggerMatrix)
      ? config.triggerMatrix
      : Array.isArray(rawFlags.triggerMatrix)
        ? rawFlags.triggerMatrix
        : defaultRuntimeFlags.triggerMatrix,
    cooldownPolicy: {
      ...defaultRuntimeFlags.cooldownPolicy,
      ...parseObjectJson(rawFlags.cooldownPolicy, defaultRuntimeFlags.cooldownPolicy),
      ...parseObjectJson(config.cooldownPolicy, {})
    },
    llmBudgetPolicy: {
      ...defaultRuntimeFlags.llmBudgetPolicy,
      ...parseObjectJson(rawFlags.llmBudgetPolicy, defaultRuntimeFlags.llmBudgetPolicy),
      ...parseObjectJson(config.llmBudgetPolicy, {})
    },
    dedupePolicy: {
      ...defaultRuntimeFlags.dedupePolicy,
      ...parseObjectJson(rawFlags.dedupePolicy, defaultRuntimeFlags.dedupePolicy),
      ...parseObjectJson(config.dedupePolicy, {})
    },
    haltOnDataGap: rawFlags.haltOnDataGap === true || config.haltOnDataGap === true,
    supervisorAiFailOpen: rawFlags.supervisorAiFailOpen === true || config.supervisorAiFailOpen === true
  }
}

/**
 * 构建运行时标志提交载荷
 *
 * 将表单数据转换为后端需要的runtimeFlagsJson格式。
 *
 * @param {Object} form - 表单数据
 * @returns {Object} 运行时标志对象(用于JSON序列化)
 */
export function buildRuntimeFlagsPayload(form = {}) {
  const base = parseObjectJson(form.runtimeFlagsJson, {})
  const baseMarketTrigger = parseObjectJson(base.marketTrigger, {})
  const baseMarketDataEnhancement = parseObjectJson(base.marketDataEnhancement, {})
  const baseWyckoffShortterm = parseObjectJson(base.wyckoffShortterm, {})
  const baseNewsTrigger = parseObjectJson(base.newsTrigger, {})
  const baseOnchainTrigger = parseObjectJson(base.onchainTrigger, {})
  const baseSocialTrigger = parseObjectJson(base.socialTrigger, {})
  const signalMemoryPolicy = {}
  ;(Array.isArray(form.signalMemoryRows) ? form.signalMemoryRows : []).forEach((row) => {
    const source = String(row?.source || '').trim()
    if (!source) {
      return
    }
    signalMemoryPolicy[source] = {
      ttlSeconds: Number(row.ttlSeconds ?? 0),
      decayMode: String(row.decayMode || 'linear').trim() || 'linear',
      combineWithinSeconds: Number(row.combineWithinSeconds ?? 0)
    }
  })
  const triggerMatrix = (Array.isArray(form.triggerMatrixRows) ? form.triggerMatrixRows : [])
    .filter((row) => String(row?.code || '').trim() && String(row?.sourcesText || '').trim())
    .map((row) => ({
      code: String(row.code || '').trim(),
      sources: normalizeScopeLines(row.sourcesText, (item) => item.toLowerCase()),
      targetDispatchMode: String(row.targetDispatchMode || 'RULE_ONLY').trim().toUpperCase() || 'RULE_ONLY',
      upgradeTo: String(row.targetDispatchMode || 'RULE_ONLY').trim().toUpperCase() || 'RULE_ONLY'
    }))
  const payload = {
    ...base,
    triggerMode: String(form.triggerMode || defaultRuntimeFlags.triggerMode).trim().toUpperCase() || defaultRuntimeFlags.triggerMode,
    marketTrigger: {
      ...baseMarketTrigger,
      ruleOnlyPriceChangePct: Number(
        form.marketTriggerRuleOnlyPriceChangePct ?? defaultRuntimeFlags.marketTrigger.ruleOnlyPriceChangePct
      ),
      priceChangePct: Number(form.marketTriggerPriceChangePct ?? defaultRuntimeFlags.marketTrigger.priceChangePct),
      priceAccelerationPct: Number(form.marketTriggerPriceAccelerationPct ?? defaultRuntimeFlags.marketTrigger.priceAccelerationPct),
      liquidationNotionalUsd: Number(
        form.marketTriggerLiquidationNotionalUsd ?? defaultRuntimeFlags.marketTrigger.liquidationNotionalUsd
      ),
      klinePriceChangePct15m: Number(form.marketTriggerKlinePriceChangePct15m ?? defaultRuntimeFlags.marketTrigger.klinePriceChangePct15m),
      klinePriceChangePct60m: Number(form.marketTriggerKlinePriceChangePct60m ?? defaultRuntimeFlags.marketTrigger.klinePriceChangePct60m),
      klinePriceChangePct240m: Number(form.marketTriggerKlinePriceChangePct240m ?? defaultRuntimeFlags.marketTrigger.klinePriceChangePct240m),
      liquidationNotional15mUsd: Number(form.marketTriggerLiquidationNotional15mUsd ?? defaultRuntimeFlags.marketTrigger.liquidationNotional15mUsd),
      liquidationNotional60mUsd: Number(form.marketTriggerLiquidationNotional60mUsd ?? defaultRuntimeFlags.marketTrigger.liquidationNotional60mUsd),
      liquidationNotional240mUsd: Number(form.marketTriggerLiquidationNotional240mUsd ?? defaultRuntimeFlags.marketTrigger.liquidationNotional240mUsd),
      fundingRateAbs: Number(form.marketTriggerFundingRateAbs ?? defaultRuntimeFlags.marketTrigger.fundingRateAbs),
      markPriceDeviationPct: Number(form.marketTriggerMarkPriceDeviationPct ?? defaultRuntimeFlags.marketTrigger.markPriceDeviationPct)
    },
    marketDataEnhancement: {
      ...baseMarketDataEnhancement,
      enabled: Object.prototype.hasOwnProperty.call(form, 'marketDataEnhancementEnabled')
        ? Boolean(form.marketDataEnhancementEnabled)
        : baseMarketDataEnhancement.enabled !== false,
      restFallbackEnabled: Object.prototype.hasOwnProperty.call(form, 'marketDataRestFallbackEnabled')
        ? Boolean(form.marketDataRestFallbackEnabled)
        : baseMarketDataEnhancement.restFallbackEnabled !== false,
      klineEnabled: Object.prototype.hasOwnProperty.call(form, 'marketDataKlineEnabled')
        ? Boolean(form.marketDataKlineEnabled)
        : baseMarketDataEnhancement.klineEnabled !== false,
      klineIntervals: normalizeScopeLines(
        form.marketDataKlineIntervalsText || (baseMarketDataEnhancement.klineIntervals || defaultRuntimeFlags.marketDataEnhancement.klineIntervals).join(', ')
      ),
      klineLimit: Number(form.marketDataKlineLimit ?? baseMarketDataEnhancement.klineLimit ?? defaultRuntimeFlags.marketDataEnhancement.klineLimit),
      liquidationAggregateWindowsMinutes: normalizeNumberLines(
        form.marketDataLiquidationWindowsText || (baseMarketDataEnhancement.liquidationAggregateWindowsMinutes || defaultRuntimeFlags.marketDataEnhancement.liquidationAggregateWindowsMinutes).join(', ')
      )
    },
    wyckoffShortterm: {
      ...baseWyckoffShortterm,
      enabled: Object.prototype.hasOwnProperty.call(form, 'wyckoffShorttermEnabled')
        ? Boolean(form.wyckoffShorttermEnabled)
        : baseWyckoffShortterm.enabled !== false,
      min15mBars: Number(form.wyckoffShorttermMin15mBars ?? baseWyckoffShortterm.min15mBars ?? defaultRuntimeFlags.wyckoffShortterm.min15mBars),
      effortLookbackBars: Number(form.wyckoffShorttermEffortLookbackBars ?? baseWyckoffShortterm.effortLookbackBars ?? defaultRuntimeFlags.wyckoffShortterm.effortLookbackBars),
      breakoutChangePct: Number(form.wyckoffShorttermBreakoutChangePct ?? baseWyckoffShortterm.breakoutChangePct ?? defaultRuntimeFlags.wyckoffShortterm.breakoutChangePct),
      breakoutVolumeRatio: Number(form.wyckoffShorttermBreakoutVolumeRatio ?? baseWyckoffShortterm.breakoutVolumeRatio ?? defaultRuntimeFlags.wyckoffShortterm.breakoutVolumeRatio),
      confirmedBreakoutChangePct: Number(form.wyckoffShorttermConfirmedBreakoutChangePct ?? baseWyckoffShortterm.confirmedBreakoutChangePct ?? defaultRuntimeFlags.wyckoffShortterm.confirmedBreakoutChangePct),
      confirmedBreakoutVolumeRatio: Number(form.wyckoffShorttermConfirmedBreakoutVolumeRatio ?? baseWyckoffShortterm.confirmedBreakoutVolumeRatio ?? defaultRuntimeFlags.wyckoffShortterm.confirmedBreakoutVolumeRatio),
      springChangePct: Number(form.wyckoffShorttermSpringChangePct ?? baseWyckoffShortterm.springChangePct ?? defaultRuntimeFlags.wyckoffShortterm.springChangePct),
      springVolumeRatio: Number(form.wyckoffShorttermSpringVolumeRatio ?? baseWyckoffShortterm.springVolumeRatio ?? defaultRuntimeFlags.wyckoffShortterm.springVolumeRatio),
      higherTimeframeConflictPct: Number(form.wyckoffShorttermHigherTimeframeConflictPct ?? baseWyckoffShortterm.higherTimeframeConflictPct ?? defaultRuntimeFlags.wyckoffShortterm.higherTimeframeConflictPct),
      higherTimeframeConfirmPct: Number(form.wyckoffShorttermHigherTimeframeConfirmPct ?? baseWyckoffShortterm.higherTimeframeConfirmPct ?? defaultRuntimeFlags.wyckoffShortterm.higherTimeframeConfirmPct),
      rangeBalanceChangePct: Number(form.wyckoffShorttermRangeBalanceChangePct ?? baseWyckoffShortterm.rangeBalanceChangePct ?? defaultRuntimeFlags.wyckoffShortterm.rangeBalanceChangePct),
      rangeBalanceRangePct: Number(form.wyckoffShorttermRangeBalanceRangePct ?? baseWyckoffShortterm.rangeBalanceRangePct ?? defaultRuntimeFlags.wyckoffShortterm.rangeBalanceRangePct),
      markDeviationPenaltyPct: Number(form.wyckoffShorttermMarkDeviationPenaltyPct ?? baseWyckoffShortterm.markDeviationPenaltyPct ?? defaultRuntimeFlags.wyckoffShortterm.markDeviationPenaltyPct),
      requireRetestForReady: Object.prototype.hasOwnProperty.call(form, 'wyckoffShorttermRequireRetestForReady')
        ? Boolean(form.wyckoffShorttermRequireRetestForReady)
        : baseWyckoffShortterm.requireRetestForReady !== false,
      retestMaxDistancePct: Number(form.wyckoffShorttermRetestMaxDistancePct ?? baseWyckoffShortterm.retestMaxDistancePct ?? defaultRuntimeFlags.wyckoffShortterm.retestMaxDistancePct),
      maxReadyExtensionPct: Number(form.wyckoffShorttermMaxReadyExtensionPct ?? baseWyckoffShortterm.maxReadyExtensionPct ?? defaultRuntimeFlags.wyckoffShortterm.maxReadyExtensionPct),
      trapVolumeRatio: Number(form.wyckoffShorttermTrapVolumeRatio ?? baseWyckoffShortterm.trapVolumeRatio ?? defaultRuntimeFlags.wyckoffShortterm.trapVolumeRatio),
      trapWickRatio: Number(form.wyckoffShorttermTrapWickRatio ?? baseWyckoffShortterm.trapWickRatio ?? defaultRuntimeFlags.wyckoffShortterm.trapWickRatio),
      trapCooldownBars: Number(form.wyckoffShorttermTrapCooldownBars ?? baseWyckoffShortterm.trapCooldownBars ?? defaultRuntimeFlags.wyckoffShortterm.trapCooldownBars)
    },
    newsTrigger: {
      ...baseNewsTrigger,
      scoreThreshold: Number(form.newsTriggerScoreThreshold ?? defaultRuntimeFlags.newsTrigger.scoreThreshold),
      severityThreshold: String(form.newsTriggerSeverityThreshold || defaultRuntimeFlags.newsTrigger.severityThreshold).trim() || defaultRuntimeFlags.newsTrigger.severityThreshold
    },
    onchainTrigger: {
      ...baseOnchainTrigger,
      flowUsdThreshold: Number(form.onchainTriggerFlowUsdThreshold ?? defaultRuntimeFlags.onchainTrigger.flowUsdThreshold),
      exchangeNetflowBias: Number(form.onchainTriggerExchangeNetflowBias ?? defaultRuntimeFlags.onchainTrigger.exchangeNetflowBias)
    },
    socialTrigger: {
      ...baseSocialTrigger,
      scoreThreshold: Number(form.socialTriggerScoreThreshold ?? defaultRuntimeFlags.socialTrigger.scoreThreshold),
      burstCount: Number(form.socialTriggerBurstCount ?? defaultRuntimeFlags.socialTrigger.burstCount)
    },
    signalMemoryPolicy,
    triggerMatrix,
    cooldownPolicy: {
      globalSeconds: Number(form.cooldownGlobalSeconds ?? defaultRuntimeFlags.cooldownPolicy.globalSeconds),
      sameSourceSeconds: Number(form.cooldownSameSourceSeconds ?? defaultRuntimeFlags.cooldownPolicy.sameSourceSeconds),
      replayBypass: Boolean(form.cooldownReplayBypass)
    },
    llmBudgetPolicy: {
      perSymbolDailyLimit: Number(form.llmBudgetPerSymbolDailyLimit ?? defaultRuntimeFlags.llmBudgetPolicy.perSymbolDailyLimit),
      rollingWindowMinutes: Number(form.llmBudgetRollingWindowMinutes ?? defaultRuntimeFlags.llmBudgetPolicy.rollingWindowMinutes),
      rollingWindowLimit: Number(form.llmBudgetRollingWindowLimit ?? defaultRuntimeFlags.llmBudgetPolicy.rollingWindowLimit),
      exhaustToRuleOnly: Boolean(form.llmBudgetExhaustToRuleOnly)
    },
    dedupePolicy: {
      sameDirectionOnly: Boolean(form.dedupeSameDirectionOnly),
      dedupeWindowSeconds: Number(form.dedupeWindowSeconds ?? defaultRuntimeFlags.dedupePolicy.dedupeWindowSeconds),
      preferHigherStrength: Boolean(form.dedupePreferHigherStrength)
    }
  }
  if (Object.prototype.hasOwnProperty.call(form, 'haltOnDataGap')) {
    payload.haltOnDataGap = Boolean(form.haltOnDataGap)
  }
  if (Object.prototype.hasOwnProperty.call(form, 'supervisorAiFailOpen')) {
    payload.supervisorAiFailOpen = Boolean(form.supervisorAiFailOpen)
  }
  return payload
}

function normalizeScopeList(values = [], fallback = []) {
  const normalized = Array.from(
    new Set(
      (Array.isArray(values) ? values : fallback)
        .map((item) => String(item || '').trim().toUpperCase())
        .filter(Boolean)
    )
  )
  return normalized.length ? normalized : [...fallback]
}

function normalizeScopeLines(value, transform = (item) => item) {
  return Array.from(
    new Set(
      String(value || '')
        .split(/[\n,]/)
        .map((item) => transform(item.trim()))
        .filter(Boolean)
    )
  )
}

function normalizeNumberLines(value) {
  return normalizeScopeLines(value)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item) && item > 0)
}

/**
 * 创建运行时配置表单对象
 *
 * 将后端配置转换为前端表单格式，包括:
 * - 基础字段映射
 * - JSON字段解析
 * - 触发策略字段展开
 * - 信号记忆策略行展开
 * - 触发矩阵行展开
 *
 * @param {Object} config - 后端配置对象
 * @returns {Object} 前端表单对象
 */
export function createRuntimeConfigForm(config = {}) {
  const runtimeFlags = resolveRuntimeFlags(config)
  return {
    id: config.id,
    defaultMode: normalizeMode(config.defaultMode),
    liveEnabled: Boolean(config.liveEnabled),
    maxPositionRatio: Number(config.maxPositionRatio ?? 0.4),
    maxDailyLoss: Number(config.maxDailyLoss ?? -500),
    maxConsecutiveFailures: Number(config.maxConsecutiveFailures ?? 3),
    allowedSymbols: parseJsonList(config.allowedSymbolsJson, runtimeSymbolOptions),
    allowedExchanges: parseJsonList(config.allowedExchangesJson, runtimeExchangeOptions),
    requireAccountBinding: config.requireAccountBinding !== false,
    liveOrderRequiresHealthyAccount: config.liveOrderRequiresHealthyAccount !== false,
    runtimeFlagsJson: prettyJson(config.runtimeFlagsJson, '{}'),
    haltOnDataGap: runtimeFlags.haltOnDataGap === true,
    triggerMode: runtimeFlags.triggerMode,
    marketTriggerRuleOnlyPriceChangePct: Number(runtimeFlags.marketTrigger.ruleOnlyPriceChangePct ?? defaultRuntimeFlags.marketTrigger.ruleOnlyPriceChangePct),
    marketTriggerPriceChangePct: Number(runtimeFlags.marketTrigger.priceChangePct ?? defaultRuntimeFlags.marketTrigger.priceChangePct),
    marketTriggerPriceAccelerationPct: Number(runtimeFlags.marketTrigger.priceAccelerationPct ?? defaultRuntimeFlags.marketTrigger.priceAccelerationPct),
    marketTriggerLiquidationNotionalUsd: Number(runtimeFlags.marketTrigger.liquidationNotionalUsd ?? defaultRuntimeFlags.marketTrigger.liquidationNotionalUsd),
    marketTriggerKlinePriceChangePct15m: Number(runtimeFlags.marketTrigger.klinePriceChangePct15m ?? defaultRuntimeFlags.marketTrigger.klinePriceChangePct15m),
    marketTriggerKlinePriceChangePct60m: Number(runtimeFlags.marketTrigger.klinePriceChangePct60m ?? defaultRuntimeFlags.marketTrigger.klinePriceChangePct60m),
    marketTriggerKlinePriceChangePct240m: Number(runtimeFlags.marketTrigger.klinePriceChangePct240m ?? defaultRuntimeFlags.marketTrigger.klinePriceChangePct240m),
    marketTriggerLiquidationNotional15mUsd: Number(runtimeFlags.marketTrigger.liquidationNotional15mUsd ?? defaultRuntimeFlags.marketTrigger.liquidationNotional15mUsd),
    marketTriggerLiquidationNotional60mUsd: Number(runtimeFlags.marketTrigger.liquidationNotional60mUsd ?? defaultRuntimeFlags.marketTrigger.liquidationNotional60mUsd),
    marketTriggerLiquidationNotional240mUsd: Number(runtimeFlags.marketTrigger.liquidationNotional240mUsd ?? defaultRuntimeFlags.marketTrigger.liquidationNotional240mUsd),
    marketTriggerFundingRateAbs: Number(runtimeFlags.marketTrigger.fundingRateAbs ?? defaultRuntimeFlags.marketTrigger.fundingRateAbs),
    marketTriggerMarkPriceDeviationPct: Number(runtimeFlags.marketTrigger.markPriceDeviationPct ?? defaultRuntimeFlags.marketTrigger.markPriceDeviationPct),
    marketDataEnhancementEnabled: runtimeFlags.marketDataEnhancement.enabled !== false,
    marketDataRestFallbackEnabled: runtimeFlags.marketDataEnhancement.restFallbackEnabled !== false,
    marketDataKlineEnabled: runtimeFlags.marketDataEnhancement.klineEnabled !== false,
    marketDataKlineIntervalsText: (runtimeFlags.marketDataEnhancement.klineIntervals || defaultRuntimeFlags.marketDataEnhancement.klineIntervals).join(', '),
    marketDataKlineLimit: Number(runtimeFlags.marketDataEnhancement.klineLimit ?? defaultRuntimeFlags.marketDataEnhancement.klineLimit),
    marketDataLiquidationWindowsText: (runtimeFlags.marketDataEnhancement.liquidationAggregateWindowsMinutes || defaultRuntimeFlags.marketDataEnhancement.liquidationAggregateWindowsMinutes).join(', '),
    supervisorAiFailOpen: runtimeFlags.supervisorAiFailOpen === true,
    wyckoffShorttermEnabled: runtimeFlags.wyckoffShortterm.enabled !== false,
    wyckoffShorttermMin15mBars: Number(runtimeFlags.wyckoffShortterm.min15mBars ?? defaultRuntimeFlags.wyckoffShortterm.min15mBars),
    wyckoffShorttermEffortLookbackBars: Number(runtimeFlags.wyckoffShortterm.effortLookbackBars ?? defaultRuntimeFlags.wyckoffShortterm.effortLookbackBars),
    wyckoffShorttermBreakoutChangePct: Number(runtimeFlags.wyckoffShortterm.breakoutChangePct ?? defaultRuntimeFlags.wyckoffShortterm.breakoutChangePct),
    wyckoffShorttermBreakoutVolumeRatio: Number(runtimeFlags.wyckoffShortterm.breakoutVolumeRatio ?? defaultRuntimeFlags.wyckoffShortterm.breakoutVolumeRatio),
    wyckoffShorttermConfirmedBreakoutChangePct: Number(runtimeFlags.wyckoffShortterm.confirmedBreakoutChangePct ?? defaultRuntimeFlags.wyckoffShortterm.confirmedBreakoutChangePct),
    wyckoffShorttermConfirmedBreakoutVolumeRatio: Number(runtimeFlags.wyckoffShortterm.confirmedBreakoutVolumeRatio ?? defaultRuntimeFlags.wyckoffShortterm.confirmedBreakoutVolumeRatio),
    wyckoffShorttermSpringChangePct: Number(runtimeFlags.wyckoffShortterm.springChangePct ?? defaultRuntimeFlags.wyckoffShortterm.springChangePct),
    wyckoffShorttermSpringVolumeRatio: Number(runtimeFlags.wyckoffShortterm.springVolumeRatio ?? defaultRuntimeFlags.wyckoffShortterm.springVolumeRatio),
    wyckoffShorttermHigherTimeframeConflictPct: Number(runtimeFlags.wyckoffShortterm.higherTimeframeConflictPct ?? defaultRuntimeFlags.wyckoffShortterm.higherTimeframeConflictPct),
    wyckoffShorttermHigherTimeframeConfirmPct: Number(runtimeFlags.wyckoffShortterm.higherTimeframeConfirmPct ?? defaultRuntimeFlags.wyckoffShortterm.higherTimeframeConfirmPct),
    wyckoffShorttermRangeBalanceChangePct: Number(runtimeFlags.wyckoffShortterm.rangeBalanceChangePct ?? defaultRuntimeFlags.wyckoffShortterm.rangeBalanceChangePct),
    wyckoffShorttermRangeBalanceRangePct: Number(runtimeFlags.wyckoffShortterm.rangeBalanceRangePct ?? defaultRuntimeFlags.wyckoffShortterm.rangeBalanceRangePct),
    wyckoffShorttermMarkDeviationPenaltyPct: Number(runtimeFlags.wyckoffShortterm.markDeviationPenaltyPct ?? defaultRuntimeFlags.wyckoffShortterm.markDeviationPenaltyPct),
    wyckoffShorttermRequireRetestForReady: runtimeFlags.wyckoffShortterm.requireRetestForReady !== false,
    wyckoffShorttermRetestMaxDistancePct: Number(runtimeFlags.wyckoffShortterm.retestMaxDistancePct ?? defaultRuntimeFlags.wyckoffShortterm.retestMaxDistancePct),
    wyckoffShorttermMaxReadyExtensionPct: Number(runtimeFlags.wyckoffShortterm.maxReadyExtensionPct ?? defaultRuntimeFlags.wyckoffShortterm.maxReadyExtensionPct),
    wyckoffShorttermTrapVolumeRatio: Number(runtimeFlags.wyckoffShortterm.trapVolumeRatio ?? defaultRuntimeFlags.wyckoffShortterm.trapVolumeRatio),
    wyckoffShorttermTrapWickRatio: Number(runtimeFlags.wyckoffShortterm.trapWickRatio ?? defaultRuntimeFlags.wyckoffShortterm.trapWickRatio),
    wyckoffShorttermTrapCooldownBars: Number(runtimeFlags.wyckoffShortterm.trapCooldownBars ?? defaultRuntimeFlags.wyckoffShortterm.trapCooldownBars),
    newsTriggerScoreThreshold: Number(runtimeFlags.newsTrigger.scoreThreshold ?? defaultRuntimeFlags.newsTrigger.scoreThreshold),
    newsTriggerSeverityThreshold: String(runtimeFlags.newsTrigger.severityThreshold || defaultRuntimeFlags.newsTrigger.severityThreshold),
    onchainTriggerFlowUsdThreshold: Number(runtimeFlags.onchainTrigger.flowUsdThreshold ?? defaultRuntimeFlags.onchainTrigger.flowUsdThreshold),
    onchainTriggerExchangeNetflowBias: Number(runtimeFlags.onchainTrigger.exchangeNetflowBias ?? defaultRuntimeFlags.onchainTrigger.exchangeNetflowBias),
    socialTriggerScoreThreshold: Number(runtimeFlags.socialTrigger.scoreThreshold ?? defaultRuntimeFlags.socialTrigger.scoreThreshold),
    socialTriggerBurstCount: Number(runtimeFlags.socialTrigger.burstCount ?? defaultRuntimeFlags.socialTrigger.burstCount),
    signalMemoryRows: normalizeSignalMemoryRows(runtimeFlags.signalMemoryPolicy),
    triggerMatrixRows: normalizeTriggerMatrixRows(runtimeFlags.triggerMatrix),
    cooldownGlobalSeconds: Number(runtimeFlags.cooldownPolicy.globalSeconds ?? defaultRuntimeFlags.cooldownPolicy.globalSeconds),
    cooldownSameSourceSeconds: Number(runtimeFlags.cooldownPolicy.sameSourceSeconds ?? defaultRuntimeFlags.cooldownPolicy.sameSourceSeconds),
    cooldownReplayBypass: runtimeFlags.cooldownPolicy.replayBypass !== false,
    llmBudgetPerSymbolDailyLimit: Number(runtimeFlags.llmBudgetPolicy.perSymbolDailyLimit ?? defaultRuntimeFlags.llmBudgetPolicy.perSymbolDailyLimit),
    llmBudgetRollingWindowMinutes: Number(runtimeFlags.llmBudgetPolicy.rollingWindowMinutes ?? defaultRuntimeFlags.llmBudgetPolicy.rollingWindowMinutes),
    llmBudgetRollingWindowLimit: Number(runtimeFlags.llmBudgetPolicy.rollingWindowLimit ?? defaultRuntimeFlags.llmBudgetPolicy.rollingWindowLimit),
    llmBudgetExhaustToRuleOnly: runtimeFlags.llmBudgetPolicy.exhaustToRuleOnly !== false,
    dedupeSameDirectionOnly: runtimeFlags.dedupePolicy.sameDirectionOnly !== false,
    dedupeWindowSeconds: Number(runtimeFlags.dedupePolicy.dedupeWindowSeconds ?? defaultRuntimeFlags.dedupePolicy.dedupeWindowSeconds),
    dedupePreferHigherStrength: runtimeFlags.dedupePolicy.preferHigherStrength !== false,
    notifyDefaultsJson: prettyJson(config.notifyDefaultsJson, '{}'),
    eventRetentionDays: Number(config.eventRetentionDays ?? 30),
    replayRetentionDays: Number(config.replayRetentionDays ?? 30),
    routeSchedulerMode: String(config.routeSchedulerMode || 'SERIAL').trim().toUpperCase() || 'SERIAL',
    routeMaxConcurrency: Number(config.routeMaxConcurrency ?? 1),
    deliberationEnabled: Boolean(config.deliberationEnabled),
    deliberationMaxRounds: Number(config.deliberationMaxRounds ?? 0),
    deliberationFailOpen: config.deliberationFailOpen !== false
  }
}

/**
 * 构建运行时配置提交载荷
 *
 * 将前端表单转换为后端API需要的格式，包括:
 * - 字段标准化
 * - JSON字段序列化
 * - 数组字段JSON化
 *
 * @param {Object} form - 前端表单对象
 * @returns {Object} 后端API载荷对象
 */
export function buildRuntimeConfigPayload(form = {}) {
  return {
    id: form.id,
    defaultMode: normalizeMode(form.defaultMode),
    liveEnabled: Boolean(form.liveEnabled),
    maxPositionRatio: Number(form.maxPositionRatio ?? 0.4),
    maxDailyLoss: Number(form.maxDailyLoss ?? -500),
    maxConsecutiveFailures: Number(form.maxConsecutiveFailures ?? 3),
    allowedSymbolsJson: JSON.stringify(normalizeScopeList(form.allowedSymbols, runtimeSymbolOptions)),
    allowedExchangesJson: JSON.stringify(normalizeScopeList(form.allowedExchanges, runtimeExchangeOptions)),
    requireAccountBinding: Boolean(form.requireAccountBinding),
    liveOrderRequiresHealthyAccount: Boolean(form.liveOrderRequiresHealthyAccount),
    runtimeFlagsJson: stringifyJson(buildRuntimeFlagsPayload(form), '{}'),
    notifyDefaultsJson: stringifyJson(form.notifyDefaultsJson, '{}'),
    eventRetentionDays: Number(form.eventRetentionDays ?? 30),
    replayRetentionDays: Number(form.replayRetentionDays ?? 30),
    routeSchedulerMode: String(form.routeSchedulerMode || 'SERIAL').trim().toUpperCase() || 'SERIAL',
    routeMaxConcurrency: Number(form.routeMaxConcurrency ?? 1),
    deliberationEnabled: Boolean(form.deliberationEnabled),
    deliberationMaxRounds: Number(form.deliberationMaxRounds ?? 0),
    deliberationFailOpen: Boolean(form.deliberationFailOpen)
  }
}

/**
 * 验证运行时配置提交载荷
 *
 * 在提交前验证表单数据的有效性，包括:
 * - 必填字段检查
 * - JSON格式验证
 * - 调度器模式验证
 * - 数值范围验证
 *
 * @param {Object} form - 前端表单对象
 * @throws {Error} 验证失败时抛出错误
 */
export function validateRuntimeConfigPayload(form = {}) {
  if (!normalizeScopeList(form.allowedSymbols, []).length) {
    throw new Error('至少需要选择一个允许交易对')
  }
  if (!normalizeScopeList(form.allowedExchanges, []).length) {
    throw new Error('至少需要选择一个允许交易所')
  }
  try {
    stringifyJson(form.runtimeFlagsJson, '{}')
  } catch {
    throw new Error('运行时 Flags JSON 格式不合法')
  }
  try {
    stringifyJson(buildRuntimeFlagsPayload(form), '{}')
  } catch {
    throw new Error('运行时 Flags JSON 格式不合法')
  }
  try {
    stringifyJson(form.notifyDefaultsJson, '{}')
  } catch {
    throw new Error('通知默认值 JSON 格式不合法')
  }
  const routeSchedulerMode = String(form.routeSchedulerMode || 'SERIAL').trim().toUpperCase()
  if (!['SERIAL', 'THREAD_POOL'].includes(routeSchedulerMode)) {
    throw new Error('路由调度器模式不合法')
  }
  if (Number(form.routeMaxConcurrency ?? 1) < 1) {
    throw new Error('路由并发数不能小于 1')
  }
  if (Number(form.deliberationMaxRounds ?? 0) < 0) {
    throw new Error('多轮协商最大轮次不能小于 0')
  }
  if (Number(form.wyckoffShorttermMin15mBars ?? 1) < 1) {
    throw new Error('威科夫短线最少K线不能小于 1')
  }
  if (Number(form.wyckoffShorttermTrapWickRatio ?? 0) < 0 || Number(form.wyckoffShorttermTrapWickRatio ?? 0) > 1) {
    throw new Error('威科夫短线影线比例必须在 0 到 1 之间')
  }
  if (!(Array.isArray(form.signalMemoryRows) ? form.signalMemoryRows : []).length) {
    throw new Error('信号记忆策略不能为空')
  }
}

function normalizeCount(value) {
  return String(value == null ? 0 : value)
}

function formatPnl(value) {
  const num = Number(value ?? 0)
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(4)}`
}

function formatPnlTone(value) {
  const num = Number(value ?? 0)
  if (num > 0) return 'success'
  if (num < 0) return 'danger'
  return 'neutral'
}

const EXECUTION_STATUS_ORDER = ['filled', 'submitted', 'pending', 'partial', 'canceled', 'expired', 'failed', 'blocked', 'skipped']

function normalizeExecutionStats(stats = {}) {
  return {
    total: Number(stats.total || 0),
    filled: Number(stats.filled || 0),
    submitted: Number(stats.submitted || 0),
    pending: Number(stats.pending || 0),
    partial: Number(stats.partial || 0),
    canceled: Number(stats.canceled || 0),
    expired: Number(stats.expired || 0),
    failed: Number(stats.failed || 0),
    blocked: Number(stats.blocked || 0),
    skipped: Number(stats.skipped || 0)
  }
}

/**
 * 构建概览指标卡片数据
 *
 * 将overview数据转换为指标卡片数组，包括:
 * - 事件数、信号数、决策数
 * - 风控命中数、活跃持仓数
 * - 浮动盈亏、当日盈亏、最大回撤
 *
 * @param {Object} overview - 概览数据对象
 * @returns {Array<Object>} 指标卡片数组
 */
export function buildSummaryCards(overview = {}) {
  const totalPnl = Number(overview.totalUnrealizedPnl ?? 0)
  const dailyPnl = Number(overview.latestDailyPnl ?? 0)
  const maxDrawdown = Number(overview.maxDrawdownPct ?? 0)
  return [
    { key: 'events', label: '事件数', value: normalizeCount(overview.eventCount), tone: 'info' },
    { key: 'signals', label: '信号数', value: normalizeCount(overview.signalCount), tone: 'success' },
    { key: 'decisions', label: '决策数', value: normalizeCount(overview.decisionCount), tone: 'warning' },
    { key: 'riskHits', label: '风控命中', value: normalizeCount(overview.riskHitCount), tone: 'danger' },
    { key: 'positions', label: '活跃持仓', value: normalizeCount(overview.activePositionCount), tone: 'primary' },
    { key: 'unrealizedPnl', label: '浮动盈亏', value: formatPnl(totalPnl), tone: formatPnlTone(totalPnl) },
    { key: 'dailyPnl', label: '当日盈亏', value: formatPnl(dailyPnl), tone: formatPnlTone(dailyPnl) },
    { key: 'maxDrawdownPct', label: '最大回撤', value: `${maxDrawdown.toFixed(2)}%`, tone: maxDrawdown > 10 ? 'danger' : 'warning' }
  ]
}

/**
 * 构建执行状态统计卡片数据
 *
 * 将executionStats转换为状态统计卡片数组，按优先级排序:
 * filled > submitted > pending > partial > canceled > expired > failed > blocked > skipped
 *
 * @param {Object} stats - 执行统计数据
 * @returns {Array<Object>} 状态统计卡片数组
 */
export function buildExecutionSummary(stats = {}) {
  const labelMap = {
    submitted: '已提交',
    filled: '已成交',
    pending: '待处理',
    partial: '部分成交',
    canceled: '已取消',
    expired: '已过期',
    failed: '失败',
    blocked: '已拦截',
    skipped: '已跳过'
  }
  const normalized = normalizeExecutionStats(stats)
  return EXECUTION_STATUS_ORDER.map((key) => ({
    key,
    label: labelMap[key] || key,
    value: normalizeCount(normalized[key]),
    tone: mapExecutionStatusTag(key)
  }))
}

export function formatExecutionTotalLabel(stats = {}) {
  return `总计 ${normalizeExecutionStats(stats).total}`
}

export function parseOverviewJson(value, fallback = []) {
  if (!value) {
    return Array.isArray(fallback) ? [...fallback] : { ...fallback }
  }
  try {
    const parsed = typeof value === 'string' ? JSON.parse(value) : value
    if (Array.isArray(fallback)) {
      return Array.isArray(parsed) ? parsed : [...fallback]
    }
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : { ...fallback }
  } catch {
    return Array.isArray(fallback) ? [...fallback] : { ...fallback }
  }
}

function parseWindowDate(value) {
  if (!value) {
    return null
  }
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

/**
 * 构建活跃信号窗口表格数据
 *
 * 将activeSignalWindows转换为表格行数据，包括:
 * - 来源类型标签
 * - 信号类型标签
 * - 方向标签
 * - 强度分数标签
 * - 状态判断(active/inactive/expired)
 *
 * @param {Array<Object>} rows - 活跃信号窗口原始数据
 * @returns {Array<Object>} 表格行数据
 */
export function buildActiveSignalWindowRows(rows = []) {
  if (!Array.isArray(rows)) {
    return []
  }
  const now = Date.now()
  return rows.map((row) => {
    const expiresAt = row?.expiresAt || row?.expires_at || ''
    const expiresDate = parseWindowDate(expiresAt)
    const active = row?.active !== false
    let statusText = 'active'
    if (!active) {
      statusText = 'inactive'
    } else if (expiresDate && expiresDate.getTime() < now) {
      statusText = 'expired'
    }
    const strengthScore = row?.strengthScore ?? row?.strength_score
    return {
      ...row,
      sourceTypeLabel: String(row?.sourceType || row?.source_type || '-').toUpperCase(),
      signalTypeLabel: String(row?.signalType || row?.signal_type || '-'),
      directionLabel: String(row?.direction || '-'),
      strengthScoreLabel: strengthScore === 0 || strengthScore ? Number(strengthScore).toFixed(2) : '-',
      statusText
    }
  })
}

export function buildDispatchOverviewCards(overview = {}) {
  return [
    { key: 'dispatchMode', label: '分发模式', value: String(overview.latestDispatchMode || 'NO_DISPATCH') },
    { key: 'triggerReason', label: '最近触发原因', value: String(overview.lastTriggerReason || '无') },
    { key: 'triggerSource', label: '最近触发来源', value: String(overview.lastTriggerSource || '无') },
    { key: 'cooldownSuppressionCount', label: '冷却拦截次数', value: normalizeCount(overview.cooldownSuppressionCount) },
    { key: 'budgetSuppressionCount', label: '预算拦截次数', value: normalizeCount(overview.budgetSuppressionCount) },
    { key: 'activeSignalWindows', label: '活跃窗口数', value: normalizeCount((overview.activeSignalWindows || []).length) }
  ]
}

function formatTradeSummaryValue(value) {
  return value === undefined || value === null || value === '' ? '-' : String(value)
}

function normalizeTradePositionSide(value) {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'buy') {
    return 'long'
  }
  if (normalized === 'sell') {
    return 'short'
  }
  return normalized
}

/**
 * 构建成交记录表格数据
 *
 * 将recentTradeActions转换为表格行数据，包括:
 * - 动作文本
 * - 方向标签
 * - 价格标签
 * - 盈亏标签和颜色
 *
 * @param {Array<Object>} rows - 成交记录原始数据
 * @returns {Array<Object>} 表格行数据
 */
export function buildRecentTradeActionRows(rows = []) {
  if (!Array.isArray(rows)) {
    return []
  }
  return rows.map((row) => {
    const positionSide = normalizeTradePositionSide(row?.positionSide || row?.side)
    return {
      ...row,
      positionSide,
      actionText: formatTradeLabel('action', row?.action) || formatTradeSummaryValue(row?.action),
      positionSideText: formatTradeLabel('orderSide', positionSide) || formatTradeSummaryValue(positionSide),
      fillPriceLabel: formatTradeSummaryValue(row?.fillPrice),
      fillQuantityLabel: formatTradeSummaryValue(row?.fillQuantity),
      openPriceLabel: formatTradeSummaryValue(row?.openPrice),
      closePriceLabel: formatTradeSummaryValue(row?.closePrice),
      realizedPnlLabel: formatPnl(row?.realizedPnl),
      realizedPnlTone: formatPnlTone(row?.realizedPnl)
    }
  })
}

export function formatOrderExecutionMeta(order = {}) {
  const parts = []
  if (order.action) {
    parts.push(String(order.action))
  }
  if (order.orderType) {
    parts.push(String(order.orderType))
  }
  if (order.positionSide) {
    parts.push(String(order.positionSide))
  }
  if (order.reduceOnly === true || order.reduceOnly === false) {
    parts.push(`reduceOnly=${order.reduceOnly}`)
  }
  if (order.tdMode) {
    parts.push(String(order.tdMode))
  }
  if (order.leverage !== undefined && order.leverage !== null && order.leverage !== '') {
    parts.push(`${order.leverage}x`)
  }
  if (order.limitPrice !== undefined && order.limitPrice !== null && order.limitPrice !== '') {
    parts.push(`px ${order.limitPrice}`)
  }
  if (order.quantityBase !== undefined && order.quantityBase !== null && order.quantityBase !== '') {
    parts.push(`qty ${order.quantityBase}`)
  }
  if (order.okxEnhancedExecution === true) {
    parts.push('OKX+')
  }
  return parts.length ? parts.join(' / ') : '-'
}
</script>

/**
 * Vue组件Setup模块 - 响应式状态与生命周期
 *
 * 本模块定义组件的响应式状态、计算属性和方法。
 *
 * 响应式状态:
 * - overview: 运行时概览数据(配置、统计、事件、决策等)
 * - loading: 加载状态
 * - runtimeConfigOpen: 配置对话框开关
 * - runtimeConfigSaving: 保存状态
 * - runtimeConfigForm: 配置表单数据
 *
 * 计算属性:
 * - summaryCards: 指标卡片数据
 * - dispatchOverviewCards: 分发概览卡片数据
 * - executionSummaryCards: 执行状态统计卡片数据
 * - runtimeModeSummary: 运行模式摘要
 * - activeSignalWindowRows: 活跃信号窗口表格数据
 * - recentTradeActionRows: 成交记录表格数据
 *
 * 方法:
 * - loadOverview: 加载概览数据
 * - resetRuntimeConfigForm: 重置配置表单
 * - handleEditRuntimeConfig: 打开编辑对话框
 * - submitRuntimeConfig: 提交配置更改
 */
<script setup>
import { computed, getCurrentInstance, onMounted, reactive, ref } from 'vue'

import { getTradeRuntimeOverview, updateTradeRuntimeConfig } from '@/api/dca/tradeRuntime'
import TradeAdvancedJsonEditor from '@/components/trade/TradeAdvancedJsonEditor.vue'
import { executionStatusTag, orderStatusTag } from '@/utils/tradeExecutionStatus'

const { proxy } = getCurrentInstance()

/**
 * 运行时概览响应式对象
 *
 * 包含所有运行时相关的数据:
 * - runtimeConfig: 运行时配置
 * - executionStats: 执行统计
 * - recentEvents/Signals/Decisions/...: 各类实时数据列表
 */
const overview = reactive({
  runtimeConfig: {
    defaultMode: 'paper',
    liveEnabled: false,
    maxPositionRatio: 0.4,
    maxDailyLoss: -500,
    maxConsecutiveFailures: 3
  },
  eventCount: 0,
  signalCount: 0,
  decisionCount: 0,
  riskHitCount: 0,
  activePositionCount: 0,
  totalUnrealizedPnl: '0',
  latestDailyPnl: '0',
  maxDrawdownPct: '0',
  latestPnlSnapshot: null,
  latestDispatchMode: 'NO_DISPATCH',
  lastTriggerReason: '',
  lastTriggerSource: '',
  cooldownSuppressionCount: 0,
  budgetSuppressionCount: 0,
  lastSelectedAgentsJson: '[]',
  lastCombinationMatchJson: '{}',
  executionStats: {
    total: 0,
    filled: 0,
    pending: 0,
    partial: 0,
    canceled: 0,
    expired: 0,
    failed: 0,
    blocked: 0,
    skipped: 0
  },
  recentEvents: [],
  recentSignals: [],
  activeSignalWindows: [],
  recentAgentConclusions: [],
  recentDecisions: [],
  recentRiskHits: [],
  recentTradeActions: [],
  recentFills: [],
  recentOrders: [],
  recentPositions: []
})
const loading = ref(false)
const runtimeConfigOpen = ref(false)
const runtimeConfigSaving = ref(false)
const runtimeConfigRef = ref()
const runtimeConfigActiveTab = ref('basic')
const runtimeConfigForm = reactive(createRuntimeConfigForm())

/**
 * 标签页分组验证规则
 *
 * 每个标签页只验证该标签页内的必填字段
 */
const runtimeConfigTabRules = {
  basic: {
    defaultMode: [{ required: true, message: '请选择默认模式', trigger: 'change' }],
    maxPositionRatio: [{ required: true, message: '请输入最大仓位比例', trigger: 'blur' }],
    maxDailyLoss: [{ required: true, message: '请输入最大日亏损', trigger: 'blur' }],
    maxConsecutiveFailures: [{ required: true, message: '请输入最大连续失败次数', trigger: 'blur' }],
    allowedSymbols: [{ required: true, message: '请至少选择一个交易对', trigger: 'change', type: 'array' }],
    allowedExchanges: [{ required: true, message: '请至少选择一个交易所', trigger: 'change', type: 'array' }],
    routeSchedulerMode: [{ required: true, message: '请选择路由调度器', trigger: 'change' }],
    routeMaxConcurrency: [{ required: true, message: '请输入路由并发数', trigger: 'blur' }]
  },
  trigger: {},
  enhancement: {},
  wyckoff: {
    wyckoffShorttermMin15mBars: [{ required: true, message: '请输入15m最少K线', trigger: 'blur' }],
    wyckoffShorttermTrapWickRatio: [
      { required: true, message: '请输入影线比例', trigger: 'blur' },
      { type: 'number', min: 0, max: 1, message: '影线比例必须在 0 到 1 之间', trigger: 'blur' }
    ]
  },
  cooldown: {},
  advanced: {}
}

/**
 * 验证所有标签页
 */
async function validateAllTabs() {
  const tabNames = ['basic', 'trigger', 'enhancement', 'wyckoff', 'cooldown', 'advanced']
  for (const tabName of tabNames) {
    const rules = runtimeConfigTabRules[tabName] || {}
    const fields = Object.keys(rules)
    if (fields.length > 0) {
      try {
        await runtimeConfigRef.value?.validateField(fields)
      } catch {
        runtimeConfigActiveTab.value = tabName
        return false
      }
    }
  }
  return true
}
const runtimeModeOptions = [
  { label: '模拟', value: 'paper' },
  { label: '影子', value: 'shadow' },
  { label: '实盘', value: 'live' }
]
const routeSchedulerOptions = [
  { label: '串行', value: 'SERIAL' },
  { label: '线程池', value: 'THREAD_POOL' }
]
const summaryCards = computed(() => buildSummaryCards(overview))
const dispatchOverviewCards = computed(() => buildDispatchOverviewCards(overview))
const executionSummaryCards = computed(() => buildExecutionSummary(overview.executionStats))
const runtimeModeSummary = computed(() => buildRuntimeModeSummary(overview.runtimeConfig))
const activeSignalWindowRows = computed(() => buildActiveSignalWindowRows(overview.activeSignalWindows))
const recentTradeActionRows = computed(() => buildRecentTradeActionRows(overview.recentTradeActions))

/**
 * 运行时配置展示数据（用于描述列表展示，避免模板中重复调用 createRuntimeConfigForm）
 */
const runtimeConfigDisplay = computed(() => createRuntimeConfigForm(overview.runtimeConfig))

/**
 * 加载运行时概览数据
 *
 * 调用后端API获取运行时概览，并更新响应式状态。
 *
 * API: GET /dca/trade/runtime/overview
 *
 * 返回数据包括:
 * - runtimeConfig: 运行时配置
 * - executionStats: 执行统计
 * - recentEvents: 最近事件
 * - recentSignals: 最近信号
 * - activeSignalWindows: 活跃信号窗口
 * - recentAgentConclusions: Agent结论
 * - recentDecisions: 主管决策
 * - recentRiskHits: 风控命中
 * - recentTradeActions: 成交记录
 * - recentOrders: 订单记录
 * - recentPositions: 持仓快照
 */
async function loadOverview() {
  loading.value = true
  try {
    const response = await getTradeRuntimeOverview()
    const data = response?.data || {}
    Object.assign(overview, {
      ...overview,
      ...data,
      runtimeConfig: {
        ...overview.runtimeConfig,
        ...(data.runtimeConfig || {})
      },
      latestDispatchMode: data.latestDispatchMode || 'NO_DISPATCH',
      lastTriggerReason: data.lastTriggerReason || '',
      lastTriggerSource: data.lastTriggerSource || '',
      cooldownSuppressionCount: Number(data.cooldownSuppressionCount || 0),
      budgetSuppressionCount: Number(data.budgetSuppressionCount || 0),
      lastSelectedAgentsJson: data.lastSelectedAgentsJson || '[]',
      lastCombinationMatchJson: data.lastCombinationMatchJson || '{}',
      executionStats: normalizeExecutionStats(data.executionStats),
      recentEvents: data.recentEvents || [],
      recentSignals: data.recentSignals || [],
      activeSignalWindows: data.activeSignalWindows || [],
      recentAgentConclusions: data.recentAgentConclusions || [],
      recentDecisions: data.recentDecisions || [],
      recentRiskHits: data.recentRiskHits || [],
      recentTradeActions: data.recentTradeActions || [],
      recentFills: data.recentFills || [],
      recentOrders: data.recentOrders || [],
      recentPositions: data.recentPositions || []
    })
  } finally {
    loading.value = false
  }
}

function resetRuntimeConfigForm(config = overview.runtimeConfig) {
  Object.assign(runtimeConfigForm, createRuntimeConfigForm(config))
  runtimeConfigRef.value?.clearValidate()
  runtimeConfigActiveTab.value = 'basic'
}

function handleEditRuntimeConfig() {
  resetRuntimeConfigForm()
  runtimeConfigOpen.value = true
}

/**
 * 提交运行时配置
 *
 * 验证并提交配置更改到后端。
 *
 * 流程:
 * 1. 验证所有标签页表单
 * 2. 验证配置载荷
 * 3. 调用API更新配置
 * 4. 刷新概览数据
 *
 * API: PUT /dca/trade/runtime/config
 */
async function submitRuntimeConfig() {
  const allValid = await validateAllTabs()
  if (!allValid) {
    proxy?.$modal?.msgError?.('请检查当前标签页的必填项')
    return
  }
  runtimeConfigSaving.value = true
  try {
    validateRuntimeConfigPayload(runtimeConfigForm)
    await updateTradeRuntimeConfig(buildRuntimeConfigPayload(runtimeConfigForm))
    proxy?.$modal?.msgSuccess?.('运行时配置已更新')
    runtimeConfigOpen.value = false
    await loadOverview()
  } catch (error) {
    if (error?.message) {
      proxy?.$modal?.msgError?.(error.message)
    }
    throw error
  } finally {
    runtimeConfigSaving.value = false
  }
}

onMounted(() => {
  loadOverview()
})
</script>

<style scoped>
.runtime-grid {
  margin-bottom: 20px;
}

.runtime-summary {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 指标卡片网格 */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.metric-card {
  position: relative;
  border-radius: 16px;
  padding: 20px;
  border: none;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.metric-card--info {
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
}

.metric-card--success {
  background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
}

.metric-card--warning {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
}

.metric-card--danger {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
}

.metric-card--primary {
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
}

.metric-card--neutral {
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
}

.metric-label {
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.metric-value {
  margin-top: 12px;
  color: #1e293b;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}

/* 执行状态汇总 */
.execution-summary {
  margin-top: 24px;
  padding: 20px;
  border-radius: 16px;
  background: #f8fafc;
}

.execution-summary__header {
  margin-bottom: 16px;
  color: #475569;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.execution-summary__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.execution-summary__item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03);
}

.execution-summary__label {
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
}

/* 配置提示 */
.runtime-config__hint {
  padding: 16px 20px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  color: #64748b;
  font-size: 13px;
  line-height: 1.8;
  border: 1px solid #e2e8f0;
}

.runtime-config__hint--compact {
  margin-top: 16px;
}

/* 配置指南 */
.runtime-config__guide {
  margin-bottom: 20px;
  padding: 24px;
  border-radius: 16px;
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 50%, #f0fdf4 100%);
  border: 1px solid #fde68a;
}

.runtime-config__guide-title {
  margin-bottom: 16px;
  color: #1e293b;
  font-size: 15px;
  font-weight: 700;
}

.runtime-config__guide-section + .runtime-config__guide-section {
  margin-top: 16px;
}

.runtime-config__guide-label {
  margin-bottom: 10px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.runtime-config__guide-list {
  margin: 0;
  padding-left: 20px;
  color: #475569;
  font-size: 13px;
  line-height: 1.8;
}

.runtime-config__guide-code {
  margin: 0;
  padding: 16px;
  border-radius: 12px;
  background: #1e293b;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.7;
  overflow-x: auto;
}

/* 策略网格 */
.policy-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
  padding: 20px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
}

.policy-grid__title {
  grid-column: 1 / -1;
  padding-bottom: 12px;
  margin-bottom: 4px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* 表格样式增强 */
:deep(.el-card) {
  border-radius: 16px;
  border: none;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

:deep(.el-card__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
}

:deep(.el-card__body) {
  padding: 24px;
}

:deep(.el-table) {
  border-radius: 12px;
}

:deep(.el-table th.el-table__cell) {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  font-size: 13px;
}

:deep(.el-table td.el-table__cell) {
  font-size: 13px;
}

:deep(.el-descriptions) {
  border-radius: 12px;
}

:deep(.el-descriptions__label) {
  background: #f8fafc;
  color: #64748b;
  font-weight: 500;
  font-size: 13px;
}

:deep(.el-descriptions__content) {
  font-size: 13px;
}

/* 响应式 */
@media (max-width: 1400px) {
  .metric-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 1200px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .execution-summary__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .policy-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .metric-card {
    padding: 16px;
    border-radius: 12px;
  }

  .metric-value {
    font-size: 22px;
  }

  .execution-summary {
    padding: 16px;
    border-radius: 12px;
  }

  .execution-summary__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .execution-summary__item {
    padding: 10px 12px;
    border-radius: 10px;
  }

  .policy-grid {
    grid-template-columns: 1fr;
    padding: 16px;
    border-radius: 12px;
    gap: 12px;
  }

  .policy-grid__title {
    font-size: 12px;
    padding-bottom: 10px;
  }

  :deep(.el-card__header) {
    padding: 16px;
  }

  :deep(.el-card__body) {
    padding: 16px;
  }

  :deep(.el-descriptions__label) {
    font-size: 12px;
  }

  :deep(.el-descriptions__content) {
    font-size: 12px;
  }

  :deep(.el-table th.el-table__cell) {
    font-size: 12px;
  }

  :deep(.el-table td.el-table__cell) {
    font-size: 12px;
  }

  .card-header {
    flex-wrap: wrap;
    gap: 8px;
  }

  .card-header__actions {
    flex-wrap: wrap;
    gap: 8px;
  }

  .runtime-config__hint {
    padding: 12px 16px;
    font-size: 12px;
    line-height: 1.6;
  }

  .runtime-config__guide {
    padding: 16px;
    border-radius: 12px;
  }

  .runtime-config__guide-title {
    font-size: 14px;
  }

  .runtime-config__guide-list {
    font-size: 12px;
    line-height: 1.6;
  }

  .runtime-config__guide-code {
    padding: 12px;
    font-size: 11px;
    border-radius: 10px;
  }
}

@media (max-width: 480px) {
  .metric-grid {
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .metric-card {
    padding: 14px;
    border-radius: 10px;
  }

  .metric-label {
    font-size: 12px;
  }

  .metric-value {
    font-size: 20px;
    margin-top: 8px;
  }

  .execution-summary__grid {
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }

  .execution-summary__item {
    padding: 8px 10px;
    border-radius: 8px;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .execution-summary__label {
    font-size: 11px;
  }

  .runtime-grid {
    margin-bottom: 12px;
  }

  :deep(.el-card) {
    border-radius: 12px;
  }

  :deep(.el-card__header) {
    padding: 12px 14px;
  }

  :deep(.el-card__body) {
    padding: 14px;
  }

  :deep(.el-form-item__label) {
    font-size: 12px;
  }

  :deep(.el-input__inner) {
    font-size: 14px;
  }

  :deep(.el-select .el-input__inner) {
    font-size: 14px;
  }

  :deep(.el-dialog) {
    width: 95% !important;
    margin: 5vh auto !important;
  }

  :deep(.el-dialog__body) {
    padding: 16px;
    max-height: 70vh;
    overflow-y: auto;
  }

  :deep(.el-descriptions) {
    font-size: 12px;
  }

  :deep(.el-table) {
    font-size: 11px;
  }

  :deep(.el-table th.el-table__cell) {
    font-size: 11px;
    padding: 8px 0;
  }

  :deep(.el-table td.el-table__cell) {
    font-size: 11px;
    padding: 8px 0;
  }

  :deep(.el-button) {
    font-size: 12px;
    padding: 8px 12px;
  }

  :deep(.el-tag) {
    font-size: 11px;
    padding: 2px 6px;
  }

  :deep(.el-form-item) {
    margin-bottom: 16px;
  }

  :deep(.el-divider__text) {
    font-size: 12px;
  }

  :deep(.el-input-number) {
    width: 100%;
  }

  :deep(.el-select) {
    width: 100%;
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }

  .runtime-config__form-tip {
    font-size: 11px;
    line-height: 1.4;
  }
}

/* 标签页表单样式 */
.runtime-config__form-tip {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
}

:deep(.el-tabs--border-card) {
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  box-shadow: none;
}

:deep(.el-tabs--border-card > .el-tabs__header) {
  border-radius: 12px 12px 0 0;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

:deep(.el-tabs--border-card > .el-tabs__content) {
  padding: 20px;
  max-height: 60vh;
  overflow-y: auto;
}

:deep(.el-tabs--border-card .el-tabs__item) {
  font-size: 13px;
  font-weight: 500;
  padding: 0 20px;
  height: 42px;
  line-height: 42px;
}

:deep(.el-tabs--border-card .el-tabs__item.is-active) {
  color: #409eff;
  background: #fff;
  border-right-color: #dcdfe6;
  border-left-color: #dcdfe6;
}

:deep(.el-tabs--border-card .el-tabs__item:hover) {
  color: #409eff;
}

/* 标签页内分隔线 */
:deep(.el-tab-pane .el-divider) {
  margin: 24px 0 16px;
}

:deep(.el-tab-pane .el-divider:first-child) {
  margin-top: 0;
}

:deep(.el-tab-pane .el-divider__text) {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}
</style>
