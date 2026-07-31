# 前端模块说明

## 一、项目结构

```
dca-ui/                              # Vue.js前端项目
├── src/
│   ├── views/dca/trade/             # 交易模块视图
│   │   ├── runtime/                 # 运行时监控与配置
│   │   │   └── index.vue            # 运行时主页面
│   │   ├── strategy/                # 策略管理
│   │   │   └── index.vue            # 策略列表与编辑
│   │   ├── decision/                # 决策记录
│   │   │   └── index.vue            # 决策历史查询
│   │   ├── agentProfile/            # Agent配置
│   │   │   └── index.vue            # Agent档案管理
│   │   ├── promptBinding/           # 提示绑定
│   │   │   └── index.vue            # 提示词绑定配置
│   │   ├── promptTemplate/          # 提示模板
│   │   │   └── index.vue            # 提示词模板管理
│   │   ├── account/                 # 交易所账户
│   │   │   └── index.vue            # 账户管理
│   │   ├── positions/               # 持仓管理
│   │   │   └── index.vue            # 持仓列表
│   │   ├── orders/                  # 订单管理
│   │   │   └── index.vue            # 订单列表
│   │   ├── fills/                   # 成交记录
│   │   │   └── index.vue            # 成交列表
│   │   ├── riskHits/                # 风控命中
│   │   │   └── index.vue            # 风控记录
│   │   ├── notifyPolicy/            # 通知策略
│   │   │   └── index.vue            # 通知策略配置
│   │   ├── notifyTemplate/          # 通知模板
│   │   │   └── index.vue            # 通知模板管理
│   │   ├── traceAudit/              # 追踪审计
│   │   │   └── index.vue            # 审计日志
│   │   ├── replay/                  # 回放功能
│   │   │   └── index.vue            # 事件回放
│   │   └── positionGuard/           # 持仓守护
│   │       └── index.vue            # 持仓保护配置
│   │
│   ├── api/dca/                     # API接口
│   │   └── tradeRuntime.js          # 运行时API
│   │
│   ├── components/trade/            # 交易组件
│   │   └── TradeAdvancedJsonEditor.vue  # JSON编辑器
│   │
│   └── utils/                       # 工具函数
│       ├── tradeExecutionStatus.js  # 执行状态工具
│       └── tradeLabels.js           # 交易标签工具
│
└── package.json
```

## 二、核心页面说明

### 1. 运行时监控页面 (runtime/index.vue)

**功能**: 交易运行时的核心监控与配置界面

**数据展示**:
- 运行时配置: 运行模式、风控参数、触发策略
- 运行时指标: 事件数、信号数、决策数、盈亏统计
- 实时表格: 事件、信号、决策、风控、订单、持仓

**交互功能**:
- 编辑运行时配置
- 配置触发策略
- 配置冷却策略
- 配置LLM预算

**数据流向**:
```
页面加载
    │
    ▼
GET /dca/trade/runtime/overview
    │
    ├─► runtimeConfig: 运行时配置
    ├─► executionStats: 执行统计
    ├─► recentEvents: 最近事件
    ├─► recentSignals: 最近信号
    ├─► recentDecisions: 主管决策
    └─► recentPositions: 持仓快照
```

### 2. 策略管理页面 (strategy/index.vue)

**功能**: 管理交易策略和策略版本

**数据展示**:
- 策略列表: 策略名称、描述、状态
- 策略版本: 版本号、配置JSON、启用状态

**交互功能**:
- 创建/编辑策略
- 创建/编辑策略版本
- 启用/禁用策略

### 3. Agent配置页面 (agentProfile/index.vue)

**功能**: 管理Agent档案和配置

**数据展示**:
- Agent列表: 名称、类型、配置
- Agent能力: 分析能力、决策能力

**交互功能**:
- 创建/编辑Agent
- 配置Agent参数
- 绑定提示模板

### 4. 持仓管理页面 (positions/index.vue)

**功能**: 查看和管理当前持仓

**数据展示**:
- 持仓列表: 交易对、方向、数量、开仓价、浮盈亏
- 持仓统计: 总持仓、总盈亏

**交互功能**:
- 查看持仓详情
- 手动平仓(需权限)

### 5. 订单管理页面 (orders/index.vue)

**功能**: 查看订单历史和状态

**数据展示**:
- 订单列表: 订单ID、交易对、方向、状态、执行状态
- 订单详情: 执行参数、成交信息

**交互功能**:
- 查看订单详情
- 取消未成交订单(需权限)

## 三、核心组件说明

### TradeAdvancedJsonEditor.vue

**功能**: 高级JSON编辑器组件

**特性**:
- JSON格式化
- 语法高亮
- 格式验证
- 错误提示

**使用场景**:
- 编辑runtimeFlagsJson
- 编辑notifyDefaultsJson
- 编辑策略配置JSON

## 四、工具函数说明

### tradeExecutionStatus.js

**功能**: 执行状态标签工具

**函数**:
- `executionStatusTag(status)`: 获取执行状态对应的标签类型
- `orderStatusTag(status)`: 获取订单状态对应的标签类型

**状态映射**:
```javascript
// 执行状态
pending   → info
submitted → primary
filled    → success
partial   → warning
canceled  → info
expired   → danger
failed    → danger
blocked   → danger
skipped   → info

// 订单状态
PENDING   → info
SUBMITTED → primary
FILLED    → success
CANCELED  → info
EXPIRED   → danger
FAILED    → danger
```

### tradeLabels.js

**功能**: 交易标签格式化工具

**函数**:
- `formatTradeLabel(type, value)`: 格式化交易标签

**标签类型**:
- action: 动作类型(OPEN_LONG, OPEN_SHORT, CLOSE_LONG, CLOSE_SHORT)
- orderSide: 订单方向(buy, sell)
- positionSide: 持仓方向(long, short, flat)

## 五、API接口说明

### tradeRuntime.js

**接口列表**:

| 函数名 | 方法 | 路径 | 说明 |
|--------|------|------|------|
| `getTradeRuntimeOverview` | GET | `/dca/trade/runtime/overview` | 获取运行时概览 |
| `getTradeRuntimeConfig` | GET | `/dca/trade/runtime/config` | 获取运行时配置 |
| `updateTradeRuntimeConfig` | PUT | `/dca/trade/runtime/config` | 更新运行时配置 |
| `getTradeRuntimeRoutes` | GET | `/dca/trade/runtime/routes` | 获取路由列表 |

## 六、配置表单字段说明

### 运行时配置表单

**基础配置**:
- `defaultMode`: 默认运行模式(paper/shadow/live)
- `liveEnabled`: 是否启用实盘交易
- `maxPositionRatio`: 最大仓位比例(0-1)
- `maxDailyLoss`: 最大日亏损(USD)
- `maxConsecutiveFailures`: 最大连续失败次数

**风控配置**:
- `requireAccountBinding`: 是否要求账户绑定
- `liveOrderRequiresHealthyAccount`: 实盘是否要求健康账户
- `haltOnDataGap`: 数据缺口是否阻断

**触发策略配置**:
- `triggerMode`: 触发模式(EVENT_GATED)
- `marketTriggerPriceChangePct`: 市场波动阈值(%)
- `newsTriggerScoreThreshold`: 新闻分数阈值
- `onchainTriggerFlowUsdThreshold`: 链上资金流阈值
- `socialTriggerScoreThreshold`: 社交分数阈值

**冷却策略配置**:
- `cooldownGlobalSeconds`: 全局冷却时间(秒)
- `cooldownSameSourceSeconds`: 同源冷却时间(秒)

**LLM预算配置**:
- `llmBudgetPerSymbolDailyLimit`: 每交易对每日限制
- `llmBudgetRollingWindowMinutes`: 滑动窗口时间(分钟)
- `llmBudgetRollingWindowLimit`: 滑动窗口限制

**信号记忆配置**:
- `signalMemoryRows`: 信号记忆策略行
  - `source`: 来源(market/news/onchain/social)
  - `ttlSeconds`: TTL(秒)
  - `decayMode`: 衰减模式(linear/step)
  - `combineWithinSeconds`: 合并窗口(秒)

**触发矩阵配置**:
- `triggerMatrixRows`: 触发矩阵规则行
  - `code`: 规则编码
  - `sourcesText`: 来源组合(逗号分隔)
  - `targetDispatchMode`: 目标分发模式

## 七、数据流向图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           前端数据流向                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  用户操作                                                                    │
│      │                                                                      │
│      ▼                                                                      │
│  Vue组件                                                                    │
│      │                                                                      │
│      ├─► 查询操作 ──► API调用 ──► 后端服务                                   │
│      │                           │                                         │
│      │                           ▼                                         │
│      │                        响应数据                                       │
│      │                           │                                         │
│      │                           ▼                                         │
│      │                        更新状态                                       │
│      │                           │                                         │
│      │                           ▼                                         │
│      │                        渲染视图                                       │
│      │                                                                      │
│      └─► 编辑操作 ──► 表单验证 ──► API调用 ──► 后端服务                       │
│                                                      │                      │
│                                                      ▼                      │
│                                                   更新成功                   │
│                                                      │                      │
│                                                      ▼                      │
│                                                   刷新数据                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 八、权限控制

页面权限通过`v-hasPermi`指令控制:

```vue
<!-- 编辑按钮需要编辑权限 -->
<el-button v-hasPermi="['dca:tradeRuntime:edit']">编辑</el-button>
```

**权限标识**:
- `dca:tradeRuntime:query`: 查询运行时
- `dca:tradeRuntime:edit`: 编辑运行时配置
- `dca:tradeStrategy:query`: 查询策略
- `dca:tradeStrategy:edit`: 编辑策略

## 九、开发指南

### 1. 添加新页面

1. 在`src/views/dca/trade/`下创建目录
2. 创建`index.vue`文件
3. 在路由配置中添加路由

### 2. 添加新API

1. 在`src/api/dca/`下创建或编辑API文件
2. 定义API函数
3. 在组件中导入使用

### 3. 添加新组件

1. 在`src/components/trade/`下创建组件
2. 实现组件逻辑
3. 在页面中导入使用

## 十、快速上手

### 1. 启动开发服务器

```bash
cd dca-ui
npm install
npm run dev
```

### 2. 核心文件阅读顺序

1. `src/views/dca/trade/runtime/index.vue` - 运行时主页面
2. `src/api/dca/tradeRuntime.js` - 运行时API
3. `src/utils/tradeExecutionStatus.js` - 状态工具
4. `src/components/trade/TradeAdvancedJsonEditor.vue` - JSON编辑器

### 3. 测试账号

- 用户名: admin
- 密码: admin123
