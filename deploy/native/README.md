# 原生部署（不使用 Docker）

面向单机、与其他服务共存的部署。MySQL / Redis / nginx 走 apt，三个应用进程走 systemd。

## 为什么另开一条路径

仓库原有的部署路径只有 Docker，而它开箱跑不起来。落地过程中实际踩到并已修复的问题：

| 问题 | 后果 | 处理 |
| --- | --- | --- |
| 建表脚本完全缺失。`.gitignore` 排除 `sql/ai_trading.sql`，`deploy/prod/README.md` 声称保留的 `ruoyi_boot_min.sql` / `trade_runtime_boot_min.sql` 从未提交 | 后端无法启动 | 从 MyBatis mapper + Java 实体反向重建 77 张表 / 1032 列，见 `sql/` |
| 根目录 `compose.yaml` 的 build context 指向 `./frontend`、`./backend`，仓库根本没有这些目录 | `docker compose up --build` 直接失败 | 改为从源码多阶段构建，见 `deploy/docker/` |
| compose 里没有 mysql 和 redis | 后端起来也没有库可连 | 补齐，并挂载 `sql/` 做首次自动初始化 |
| `deploy/prod/python-worker/Dockerfile` 里 `COPY core ./core`、`COPY modules ./modules`，这两个目录不存在 | 镜像构建失败 | `deploy/docker/python-worker.Dockerfile` 只拷贝真实存在的 `main.py` 和 `trade_runtime/` |
| `logback.xml` 把日志路径写死为 `/home/ruoyi/logs` | appender 创建失败 = 启动即崩，任何未预建该目录的机器都中招 | 改为可用 `LOG_PATH` 覆盖 |
| `dca-ui/package.json` 的 `build:prod` 是 `-ui   build`（疑似批量替换事故） | README 让你执行的构建命令必然失败 | 修正为 `vite build --mode production` |
| README 第 6 节让你跑 `deploy/compose.yaml` | 该文件不存在 | 用根目录 `compose.yaml` 或本目录的原生路径 |

## 快速开始

```bash
sudo ./deploy/native/install.sh bootstrap   # 建用户/目录/env 模板、装 systemd 与 nginx
# 编辑 /opt/dca/env/*.env，填掉所有 __CHANGE_ME__
sudo ./deploy/native/install.sh schema      # 仅对空库执行；会 DROP TABLE
./deploy/native/install.sh build            # 构建 jar 与前端产物
sudo ./deploy/native/install.sh deploy      # 安装产物并拉起服务
sudo ./deploy/native/install.sh status
```

`schema` 会拒绝在已有表的库上执行——这些脚本带 `DROP TABLE`，误跑会抹掉订单与审计历史。

## 端口

| 组件 | 监听 | 对外 |
| --- | --- | --- |
| 控制台 nginx | `0.0.0.0:8099` | 是（唯一入口） |
| 后端 | `127.0.0.1:18081` | 否 |
| feed-adapter | `127.0.0.1:18080` | 否 |
| MySQL / Redis | `127.0.0.1` | 否 |

## 安全：worker 的私有控制通道

`/dca/` 下有 **43 个端点带 `@Anonymous`**，因为 worker 与后端的协议假定二者同处可信网络。这个假设本身没错，但它要求后端永不直接对外，且反向代理不能把这些路由透出去。

危害最大的几个：

- `GET /dca/ai/models/config/default`、`/config/{id}` —— **免鉴权返回解密后的明文模型 API Key**
- `POST /dca/trade/runtime/model-call` —— 免鉴权的 LLM 调用，等于把你的额度做成公共代理
- `POST /dca/event/ingest` —— 直接向决策图注入行情/新闻/链上/社交事件
- `POST /dca/taskqueue/{pull,result,heartbeat}` —— 冒充 worker 接管任务
- `POST /dca/trade/execution/*`、`/dca/callback/*` —— 免鉴权写入订单、成交、持仓与告警

`nginx-dca.conf` 逐条封堵了这些路由，并且每一条都先比对过 `dca-ui` 的 API 层，确认控制台不会用到。有几个是控制台确实要用的只读接口，故意保留：`/dca/trade/runtime/config`、`/dca/decision/runs`、`/dca/trade/replay/source`、`/dca/trade/constants/*`。

注意 `event`/`events`、`session`/`sessions` 只差一个字母，因此这两组必须用 `location =` 精确匹配，用前缀匹配会连带打死回放控制台。

其余加固项：

- 所有密钥只存在于 `/opt/dca/env/*.env`（0600），仓库内不落任何凭据
- `TOKEN_SECRET` 必须覆盖：`application.yml` 的默认值是字面量 `abcdefghijklmnopqrstuvwxyz`，知道它就能签发管理员 token
- Druid 控制台（`statViewServlet` 默认启用且 allow 列表为空）与 OpenAPI 路由在 nginx 层 404，需要时走 SSH 隧道到 `127.0.0.1:18081`
- `LOG_LEVEL_RUOYI` 默认 `debug` 会把每条 SQL（含订单流）写进日志，生产改 `info`
- systemd 单元启用 `ProtectSystem=strict` / `NoNewPrivileges` / `PrivateTmp`，并设 `MemoryMax`
- worker 单元设了 `StartLimitBurst=5`：下单通路反复崩溃时停止重启，而不是拿坏版本反复冲击交易所

## 香港网络适配

这台机的实测结论（其他机房未必相同，建议自测）：

| 目标 | 结果 |
| --- | --- |
| `fapi.binance.com` REST | 通，约 180ms |
| `www.okx.com` REST | 通 |
| `stream.binance.com:9443` 现货 WS | 通，1 秒内有数据 |
| **`fstream.binance.com` 合约 WS** | **TLS 握手成功，但 30 秒零数据帧** |
| `api.openai.com` | 403 `unsupported_country_region_territory` |
| `api.anthropic.com` | 403 forbidden |
| `api.deepseek.com` | 401（通，仅缺 key） |

两点由此决定：

**LLM 走 DeepSeek。** worker 本身不直连任何模型厂商——它 POST 到后端的 `/dca/trade/runtime/model-call`，由 Java 侧按 `ai_model_config.api_endpoint` 发起请求。所以换模型只是改一行配置，种子默认就是 `deepseek-reasoner`。这条间接层正是被地区封锁的机器仍能跑决策图的原因。

**行情源用 REST 而非 WS。** 合约 WS 握手能成但永不推数据，`ws_supervisor` 会把每次 fetch 判为失败、回退 REST 并标记 `degraded`；而 `risk/guard.py` 把 `degraded` 视为数据源异常 **拦掉每一笔下单**——网络问题会静默地把交易整个关停。

因此给 supervisor 加了 `rest_primary`：当 `market_api_config.transport_type` 为 `http`/`rest` 时，轮询就是既定传输方式，取到数据即报 `ready`。安全性保留——REST 自己失败时仍然是 `degraded`。

本机对应的配置：

```sql
UPDATE market_api_config SET transport_type='http' WHERE id=101;
```

`sql/seed_min.sql` 里仍默认 `ws`，因为多数网络下 WS 是更好的选择（延迟更低，触发判定更细）。REST 轮询按 `collect_interval` 取数，触发时效性会粗一些。

## 时区

应用以 GMT+8 写时间戳（JDBC `serverTimezone=GMT+8`，Jackson 同）。MySQL 若停留在 UTC，`NOW()` 会与每一条 `created_at` 相差 8 小时，任何基于 `NOW()` 的保留期查询都会算错（例如 `MarketDataCollectLogMapper.cleanOldLogs`）。交易域的清理走 Java 传入的 `#{cutoffTime}`，不受影响。

安装脚本不会替你改共享实例的全局配置。若该 MySQL 只服务本项目：

```ini
# /etc/mysql/mysql.conf.d/zz-dca.cnf
[mysqld]
default-time-zone = '+08:00'
```

## 依赖瘦身

`python-worker/requirements.txt` 从 12 个包减到 6 个。以下均经核实在整个 `python-worker/` 下没有任何 import：

- `openai`、`anthropic` —— worker 从不直连模型厂商（见上）
- `langchain` —— 只用到 `langgraph.graph`，langgraph 自带所需的 langchain-core
- `binance-connector` —— `execution/` 用 `requests` 直接打 REST
- `pyyaml`、`python-dotenv` —— 配置全部来自环境变量

装完跑 `pytest tests/`：543 通过。（另有 2 个失败是 `test_sql_prompt_rendering.py` 找不到同样被 gitignore 掉的 `sql/ai_trading_online.sql`，与本次改动无关。）

## schema 是怎么重建的

原始 dump 不在仓库里，重建依据是树里仅存的三类权威信息：

1. **MyBatis resultMap** —— 列与属性的对应，`<id>` 标记主键
2. **Java 实体字段** —— 属性到 Java 类型，再映射到 MySQL 类型
3. **insert 的列表与值列表按位置配对** —— 补出 resultMap 里没有的列，`#{property}` 回查 `parameterType` 得到类型
4. **where / order by 的使用频次** —— 生成索引候选

字段长度与精度是推断值（`BigDecimal` 统一给 `decimal(36,18)`，字符串按列名尾词判断 varchar/text），只有仓库自带契约测试和 `sql/migrations/` 里写死的类型是确定的。表结构与列名是精确的；类型足够跑通，但不保证与作者原始 dump 逐字节一致。

验证方式：后端正常启动、admin 登录、菜单树渲染、12 个交易域接口全部 200，以及 worker 持续向 `decision_run` / `signal_event` / `event_raw` / `market_event` 写入——读写两侧都过了。

## 行情信号覆盖（Binance）

调研了一圈近期活跃的开源量化项目后，最值得做的升级并不是引入新框架，而是**把这个系统自己已经写好、却没有数据的触发维度接通**。

### 原状：一半以上的行情触发是死的

`mark_price`、`funding_rate`、`liquidation` 事件**只在 `binance_ws.py` 里生产**，`open_interest` 则完全没有 Binance 的生产者。REST 回退路径（`BinancePublicMarketFeed`）只返回最新价和成交额三个字段。

更彻底的是，K 线与技术指标所在的 `_enhanced_market_events` 开头就是 `if self.exchange != "okx"` —— **整个增强层是 OKX 专用的**。而默认交易所是 Binance。

于是在 Binance 上（尤其是本机这种 WS 被封、只能走 REST 的环境），下列全部无数据可评估：

| 触发/特征 | 原状 |
| --- | --- |
| `fundingRateAbs` | 无数据 |
| `markPriceDeviationPct` | 无数据 |
| `klinePriceChangePct15m / 60m / 240m` | 无 K 线 |
| `atr_pct` / `rsi_14` / `ema_trend` | 无 K 线 |
| 量价信号、Wyckoff 短线分析 | 无 K 线 |
| 持仓量及其变化 | 无生产者 |
| 爆仓聚合窗口 | 无数据 |

实际参与门控的只剩价格变化和加速度两项。而这恰恰是对「持仓拥挤度」信息量最低的两个指标——资金费率持续高于 0.05–0.1%/8h 意味着多头过度杠杆、常先于爆仓瀑布，持仓量则是永续三大核心观测量之一。

### 现状

新增 `ingestion/binance_rest.py`，用公开且免鉴权的 REST 端点补齐：

| 端点 | 产出 |
| --- | --- |
| `/fapi/v1/premiumIndex` | `mark_price`（含 indexPrice 与基差）、`funding_rate` |
| `/fapi/v1/openInterest` | `open_interest`（附按标记价折算的 USD 名义值） |
| `/futures/data/openInterestHist` | 持仓量变化率 |
| `/fapi/v1/klines` | K 线 → ATR / RSI / EMA 趋势 / 三窗口涨跌与量比 |

接入点是 `_market_events`——websocket 路径本来就用这个键把补充事件交给 `_supplemental_market_events`，所以装配器、触发策略和决策图都不需要改动。资金费率每 8 小时结算、持仓量约每分钟更新，因此衍生品端点默认 30 秒节流，不会浪费限频权重；任一衍生品端点失败都不影响价格 tick，因为 tick 决定数据源健康度，而 `risk/guard.py` 一旦判定数据源异常就会拦下所有下单。

**关于爆仓数据**：全市场爆仓只有 `!forceOrder@arr` 这个 websocket 流，`/fapi/v1/forceOrders` 是 USER_DATA、只返回你自己的爆仓。公开 REST 没有对应来源，所以本模块**不合成** `liquidation` 事件——在一个准备上实盘的系统里，把推断值伪装成交易所上报事实是不可接受的。取而代之提供持仓量，它才是去杠杆过程中真正可观测的量。因此爆仓聚合窗口在纯 REST 环境下仍为 0。

### 配置

增强层的 `exchanges` **默认仍只有 OKX**。打开 Binance 会改变进入门控的事件构成，这不是应该在策略运行中被静默切换的东西：

```json
{
  "marketDataEnhancement": {
    "exchanges": ["okx", "binance"],
    "klineIntervals": ["1m", "15m"],
    "klineLimit": 500
  },
  "marketTrigger": {
    "fundingRateAbs": 0.0005,
    "markPriceDeviationPct": 0.25
  }
}
```

`klineIntervals` 只取 1m 和 15m：`summarize_kline_context` 以 1m 为主序列推导 15m/60m/240m 窗口，另用 15m 序列算 60m 指标，默认那五个区间里有三个拉了没人用。`klineLimit` 需要 500——240m 量比要比较前后各 240 根 1m 线，默认的 120 会让这个「240 分钟窗口」实际只有 120 分钟且量比恒为 0。

两个阈值的取值依据：本机实测 mark 与最新价偏离常态在 ±0.05% 以内，0.25% 是真正的价格脱节；资金费率基准约 0.01%/8h，0.05% 是文献中「多头拥挤」的下沿。

**这些阈值没有经过回测。** 这个仓库没有任何历史回测设施（`replay` 只是把单条 `trace_id` 重放一遍，不是历史检验），所以全部触发阈值——包括原有的 `priceChangePct: 2.5`——都是人工选定值。上实盘前，把阈值放到历史数据上校准是比再加信号更有价值的下一步。

### 顺带修掉的一个隐性缺陷

`_market_data_enhancement_config` 遇到非 dict 入参会**静默返回全部默认值**。而调用方并不一致：`runtime_runner` 传的是 `RuntimeConfig.model_dump()`，bootstrap 路径传的是 `RuntimeConfig` 对象。结果同一份运维配置在一条路径上生效、在另一条路径上被忽略，且没有任何日志。现在两种入参都接受。
