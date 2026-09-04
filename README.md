# Cryptocurrency Auto-Trading（AI 加密货币自动交易系统）

一个面向加密合约的多源驱动、多 Agent 决策的自动化交易系统。系统对接 Binance / OKX 等主流交易所，整合行情、新闻、链上、社交四类信号，通过触发策略评估事件强度，由 LangGraph 决策图汇总多 Agent 观点并产出主管决策，再经风控、冷却、预算等多重约束后落地为真实/影子/模拟订单。

> 项目基于若依（RuoYi-Vue）脚手架二次开发，后台与权限/调度/代码生成等通用能力来自若依；交易域（`ruoyi-dca`）、Python 决策运行时（`python-worker/trade_runtime`）、数据适配层（`feed-adapter`）以及前端交易控制台（`dca-ui`）为本项目的核心自研代码。

## 项目简介

传统的"指标触发—策略下单"型机器人很难应对加密市场的高噪声与多源信息耦合。本项目把交易决策抽象成一条可观测、可回放、可审计的状态流：

- **事件门控（Event-Gated）**：所有信号先按触发策略分级（strong / normal / noise），只有通过门控的事件才会消耗 LLM 预算
- **多 Agent 协作**：行情、新闻、链上、社交四个 Agent 并行分析，主管（Supervisor）汇总并给出最终动作
- **三态执行**：`paper`（模拟）/ `shadow`（影子）/ `live`（实盘）三种模式可热切换
- **完整审计**：决策、风控、订单、回放全程留痕，支持基于 `trace_id` 的事件级重放

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          交易运行时系统架构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐      ┌──────────────────┐      ┌─────────────────┐      │
│   │  数据摄入层   │─────▶│  触发策略评估     │─────▶│  决策图执行      │      │
│   │ (Ingestion)  │      │ (Trigger Policy) │      │ (Decision Graph)│      │
│   └──────────────┘      └──────────────────┘      └─────────────────┘      │
│         │                       │                        │                 │
│         ▼                       ▼                        ▼                 │
│   ┌──────────────┐      ┌──────────────────┐      ┌─────────────────┐      │
│   │ - 行情/K线    │     │ - 事件强度分类    │     │ - 多 Agent 协作  │      │
│   │ - 新闻资讯    │     │ - 信号组合匹配    │     │ - 主管决策       │      │
│   │ - 链上资金    │     │ - 冷却 / 预算     │     │ - 风控检查       │      │
│   │ - 社交舆情    │     │ - LLM 调用预算    │     │ - 订单执行       │      │
│   └──────────────┘      └──────────────────┘      └─────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 数据流向

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Binance WS  │    │  News API    │    │  Onchain API │    │  Social API  │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │                   │
       └──────────┬────────┴───────────────────┴───────────────────┘
                  ▼
          ┌─────────────────┐                ┌─────────────────┐
          │  feed-adapter   │                │   Java 后端      │
          │  (Python)       │                │  (配置/审计/卡密) │
          └────────┬────────┘                └────────┬────────┘
                   │                                  │
                   │      ┌───────────────────┐       │
                   └─────▶│  python-worker     │◀──────┘
                          │  (trade_runtime)   │
                          │  LangGraph 决策图   │
                          └─────────┬──────────┘
                                    │
                                    ▼
                          ┌───────────────────┐
                          │   交易所执行层     │
                          │  Binance / OKX    │
                          └───────────────────┘
```

## 技术栈

### 后端（Java）

| 技术 | 说明 |
| --- | --- |
| Spring Boot 3.5.11 | 后端核心框架 |
| Spring Security + JWT | 认证授权 |
| MyBatis + PageHelper | ORM 与分页 |
| Druid | 数据库连接池 |
| MySQL 8.0 | 关系型数据库 |
| Redis 6 | 缓存与事件流 |
| SpringDoc OpenAPI | 接口文档 |
| Quartz | 定时任务 |
| Maven | 构建管理 |

### 决策运行时（Python）

| 技术 | 说明 |
| --- | --- |
| Python 3.11 | 运行时 |
| LangGraph 0.2 | 决策图编排 |
| LangChain 0.3 | LLM 编排框架 |
| OpenAI / Anthropic SDK | 多模型客户端 |
| Pydantic 2 | 配置与状态建模 |
| redis-py + Stream | 事件流与去重 |
| binance-connector | Binance REST 客户端 |
| websocket-client | Binance / OKX 实时行情 |
| pytest | 单元测试 |

### 前端（Vue）

| 技术 | 说明 |
| --- | --- |
| Vue 3.4 | 前端框架 |
| Vite 5 | 构建工具 |
| Element Plus 2.7 | UI 组件库 |
| Pinia | 状态管理 |
| Vue Router 4 | 路由 |
| ECharts 5 | 数据可视化 |
| Axios | HTTP 客户端 |

## 项目结构

```
cryptocurrency-auto-trading
├── ruoyi-admin/              # 后端启动模块（含 Security、Swagger 配置）
├── ruoyi-framework/          # 核心框架（认证、拦截器、AOP）
├── ruoyi-system/             # 系统管理（用户、菜单、字典等）
├── ruoyi-common/             # 通用工具
├── ruoyi-quartz/             # 定时任务
├── ruoyi-generator/          # 代码生成器
├── ruoyi-dca/                # ★ 交易域核心模块（DCA）
│   ├── controller/           # 运行时配置、策略、账户、卡密、回调
│   ├── service/trade/        # 交易域服务
│   ├── domain/trade/         # 运行时引导、Agent 档案、持仓守护…
│   ├── domain/event/         # 市场/新闻/链上/社交事件
│   ├── domain/decision/      # Agent 结论、特征快照
│   ├── client/               # Binance / OKX 市场数据客户端
│   └── aspectj/              # 审计日志切面
├── python-worker/            # ★ 决策运行时（LangGraph）
│   ├── main.py               # 入口（解析 WORKER_PROFILE）
│   └── trade_runtime/
│       ├── app.py            # TradeRuntimeApp 主流程
│       ├── runtime_runner.py # 单次运行循环
│       ├── config.py         # RuntimeConfig / RuntimeBootstrap
│       ├── trigger_policy.py # 事件强度分类与门控
│       ├── decision/         # 决策图与节点（多 Agent + 主管）
│       ├── ingestion/        # 行情/新闻/链上/社交数据源
│       ├── execution/        # Binance / OKX 期货执行路由
│       ├── memory/           # 短期/长期记忆与生命周期总结
│       ├── risk/             # 风控规则
│       ├── prompting/        # Prompt 模板
│       └── llm_budget.py     # LLM 调用预算
├── feed-adapter/             # ★ 辅助数据源适配（news/onchain/social）
│   ├── app.py
│   └── feed_adapter/
│       ├── server.py         # FastAPI/Flask 接口
│       ├── service.py        # 缓存与聚合
│       └── providers/        # 各数据源 Provider
├── dca-ui/                   # ★ 交易控制台前端
│   └── src/views/dca/trade/  # runtime / strategy / agent / positions…
├── sql/
│   ├── ai_trading.sql        # 数据库初始化脚本（含菜单/种子）
│   └── migrations/           # 增量迁移
├── deploy/
│   ├── compose.yaml          # 本地编排（前端/后端/适配器/Worker）
│   ├── prod/                 # 生产部署目录（Dockerfile + nginx）
│   └── memos/                # 长期记忆 MCP 部署说明
├── docs/                     # 项目文档与图片
└── pom.xml                   # 父 POM
```

## 核心功能

### 1. 多源数据摄入

- **行情**：Binance / OKX 的 REST + WebSocket（K 线、Ticker、资金费率、强平）
- **新闻**：通过 `feed-adapter` 聚合，输出情绪分与事件强度
- **链上**：资金流向、巨鲸地址、异常转账
- **社交**：Twitter / Reddit 等舆情得分

### 2. 触发策略（Event-Gated）

| 维度 | 阈值示例 | 说明 |
| --- | --- | --- |
| 行情 | 价格变化 ≥ 2.5% / 清算 ≥ 25 万 USD | 强信号触发 LLM 决策 |
| 新闻 | score ≥ 0.9 | 路由到 `LLM_ALLOWED` |
| 链上 | 资金流 ≥ 100 万 USD | 触发链上事件分类 |
| 社交 | score ≥ 0.85 | 触发社交事件分类 |
| 冷却 | 全局 180s / 同源 60s | 防止噪声轰炸 |
| LLM 预算 | 每品种 30 次/日 | 控制 LLM 成本 |

### 3. 多 Agent 决策图

决策图基于 LangGraph 构建，节点顺序：

```
ingest_context → build_feature_snapshot → classify
   → retrieve_memory → multi_agent(market/news/onchain/social)
   → deliberation? → supervisor → risk_gate → execute_order → audit
```

- **多 Agent**：四个领域 Agent 并行产出观点
- **Deliberation**：可选的 Agent 间审议环节
- **Supervisor**：汇总观点调用 LLM 输出 `action / side / confidence / size_hint`
- **Risk Gate**：仓位上限、日亏损上限、连续失败熔断、数据源健康检查

### 4. 三种运行模式

| 模式 | 行为 | 适用场景 |
| --- | --- | --- |
| `paper` | 模拟成交，不实际下单 | 策略验证 |
| `shadow` | 产生决策但不执行 | 实盘前验证 |
| `live` | 实盘下单 | 真实交易（需账户绑定 + 健康检查） |

### 5. 卡密授权系统

支持 `time`（时长）/ `permanent`（永久）/ `count`（次数）/ `trial`（试用）四种卡密类型，绑定用户 ID 与机器码，支持批量生成与启用/禁用。

### 6. 完整审计与回放

- **审计**：决策日志、Agent 观点、风控结果、订单生命周期全程留痕
- **回放**：基于 `trace_id` 的事件级回放，支持 Replay Console 一键发起
- **追踪**：每个决策有唯一 `trace_id`，可在前后端串联全链路

## 快速开始

### 环境要求

- JDK 17+
- Node.js 18+
- Python 3.11+
- MySQL 8.0+
- Redis 6+
- Maven 3.8+
- Docker / Docker Compose（推荐）

### 1. 导入数据库

由于原始导出文件包含真实账户/凭据/IP 等敏感数据，**公开仓库不附带完整 SQL dump**。请按以下任一方式初始化：

- **方式 A（推荐）**：基于 `ruoyi-dca/src/main/resources/mapper/dca/*.xml` 中的 MyBatis 映射与 `sql/migrations/` 下的增量脚本自行建立表结构，并参考若依官方 [RuoYi-Vue](https://gitee.com/y_project/RuoYi-Vue) 的初始化脚本补齐 `sys_*` 系统表。
- **方式 B**：从你的私有备份恢复 `sql/ai_trading.sql`（仅本地保留，切勿提交到公开仓库）。

无论哪种方式，初始化后请：

1. 修改默认管理员账号密码
2. 在「AI 模型配置」页面填入你自己的模型 API Key
3. 在「通知渠道」页面填入你自己的 SMTP 配置

### 2. 后端启动

修改 `ruoyi-admin/src/main/resources/application-druid.yml` 与 `application.yml` 中的数据库、Redis 配置后：

```bash
mvn -pl ruoyi-admin -am -DskipTests package
java -jar ruoyi-admin/target/ruoyi-admin.jar
```

或使用 Maven 直接运行：

```bash
mvn spring-boot:run -pl ruoyi-admin
```

### 3. 前端启动

```bash
cd dca-ui
npm install
npm run dev
```

访问 `http://localhost:80`，默认账号 `admin / admin123`。

### 4. Python Worker 启动

```bash
cd python-worker
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # Linux/Mac
pip install -r requirements.txt

cp .env.example .env            # 按 .env.example 注释填写
python -m python-worker.main
```

### 5. Feed Adapter 启动

```bash
cd feed-adapter
pip install -r requirements.txt
cp .env.example .env
python app.py
```

### 6. Docker Compose 一键启动（推荐）

```bash
docker compose -f deploy/compose.yaml up -d --build
```

容器编排如下：

| 服务 | 端口（宿主） | 说明 |
| --- | --- | --- |
| `dca-frontend` | 28080 | Vue 前端（Nginx） |
| `dca-backend` | 28081 | Spring Boot 后端 |
| `feed-adapter` | 18080 | 辅助数据源适配 |
| `python-worker` | — | 决策运行时 |

## 关键配置说明

### Python Worker `.env`

```env
WORKER_PROFILE=trade_runtime
TRADE_RUNTIME_RUN_MODE=forever            # forever / once / replay
TRADE_RUNTIME_BASE_URL=http://localhost:8080
TRADE_RUNTIME_DEFAULT_SYMBOL=BTCUSDT
TRADE_RUNTIME_POLL_INTERVAL_SECONDS=60

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# 事件流
TRADE_RUNTIME_STREAM_NAME=trade.runtime.events

# 长期记忆（可选）
TRADE_RUNTIME_MEMORY_STORE=hybrid
```

> 交易所 API Key/Secret 必须在后端账户绑定中配置，Worker 不会从 `.env` 读取交易所凭据下单。

### 运行时配置（前端「运行时监控」页面）

- **defaultMode**：默认运行模式（paper / shadow / live）
- **maxPositionRatio**：最大仓位比例
- **maxDailyLoss**：最大日亏损（USD）
- **maxConsecutiveFailures**：最大连续失败次数
- **triggerMatrixRows**：信号组合触发矩阵
- **cooldownGlobalSeconds**：全局冷却时间
- **llmBudgetPerSymbolDailyLimit**：每品种每日 LLM 调用上限

## 测试

```bash
# Python Worker 测试
cd python-worker
pytest tests/trade_runtime/

# Feed Adapter 测试
cd feed-adapter
pytest tests/

# 前端单元测试
cd dca-ui
npm run test:unit
```

## 生产部署

生产部署细节见 [`deploy/prod/README.md`](deploy/prod/README.md)，包含：

- 构建产物（前端 dist / 后端 jar / Python 模块）的准备
- 服务器目录布局（`/opt/web4-first`）
- 数据库引导脚本（`sql/ruoyi_boot_min.sql` + `sql/trade_runtime_boot_min.sql`）
- Replay / 长期记忆（MemOS MCP）运维说明

## 模块文档

- 前端模块详细文档：[`dca-ui/README.md`](dca-ui/README.md)
- Java 后端交易域文档：[`ruoyi-dca/README.md`](ruoyi-dca/README.md)
- Python 决策运行时文档：[`python-worker/trade_runtime/README.md`](python-worker/trade_runtime/README.md)
- 生产部署文档：[`deploy/prod/README.md`](deploy/prod/README.md)
- 长期记忆部署说明：[`deploy/memos/README.md`](deploy/memos/README.md)

## 风险声明

本项目仅用于学习、研究和技术验证。加密货币合约交易涉及高杠杆与高风险，可能造成本金全部损失。

- 默认运行模式为 `paper`，**不会**真实下单
- 切换到 `live` 实盘模式前，请充分理解触发策略、风控规则与仓位约束
- 作者不对任何直接或间接损失承担责任，请自行评估并承担相应风险

## 许可证

本项目基于 MIT 协议开源，详见 [`LICENSE`](LICENSE)。

本项目基于若依（RuoYi-Vue）框架开发，感谢若依团队提供的优秀开源框架。
