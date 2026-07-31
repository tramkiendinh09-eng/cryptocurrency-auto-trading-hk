# Java后端模块说明

## 一、项目结构

```
ruoyi-dca/                          # DCA交易系统核心模块
├── controller/                     # 控制器层
│   ├── CardKeyController.java      # 卡密管理控制器
│   ├── NotifyRecordController.java # 通知记录控制器
│   ├── AuditController.java        # 审计控制器
│   └── trade/                      # 交易相关控制器
│       ├── TradeRuntimeConfigController.java  # 运行时配置控制器
│       ├── TradeStrategyController.java       # 策略管理控制器
│       ├── ExchangeAccountController.java     # 交易所账户控制器
│       └── ...
│
├── service/                        # 服务层
│   ├── ICardKeyService.java        # 卡密服务接口
│   ├── impl/
│   │   └── CardKeyServiceImpl.java # 卡密服务实现
│   └── trade/                      # 交易相关服务
│       ├── ITradeRuntimeConfigService.java    # 运行时配置服务
│       ├── ITradeStrategyService.java         # 策略服务
│       └── impl/
│           └── TradeRuntimeConfigServiceImpl.java
│
├── mapper/                         # 数据访问层
│   ├── CardKeyMapper.java          # 卡密Mapper
│   └── trade/                      # 交易相关Mapper
│
├── domain/                         # 领域模型
│   ├── CardKey.java                # 卡密实体
│   ├── AiModelConfig.java          # AI模型配置
│   ├── trade/                      # 交易相关实体
│   │   ├── TradeRuntimeConfig.java # 运行时配置
│   │   ├── TradeStrategy.java      # 交易策略
│   │   ├── ExchangeAccount.java    # 交易所账户
│   │   └── TradeRuntimeBootstrap.java # 运行时引导配置
│   ├── event/                      # 事件模型
│   │   ├── MarketEvent.java        # 市场事件
│   │   ├── NewsEvent.java          # 新闻事件
│   │   ├── OnchainEvent.java       # 链上事件
│   │   └── SocialEvent.java        # 社交事件
│   └── decision/                   # 决策模型
│       ├── AgentConclusion.java    # Agent结论
│       └── FeatureSnapshot.java    # 特征快照
│
├── client/                         # 外部客户端
│   ├── BinanceMarketApiClient.java # Binance市场数据客户端
│   └── OkxMarketApiClient.java     # OKX市场数据客户端
│
└── aspectj/                        # 切面
    └── AuditLogAspect.java         # 审计日志切面
```

## 二、核心业务流程

### 1. 运行时配置流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           运行时配置流程                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Python Worker                                                              │
│       │                                                                     │
│       │ GET /dca/trade/runtime/bootstrap?symbol=BTCUSDT&exchange=binance   │
│       ▼                                                                     │
│  TradeRuntimeConfigController                                               │
│       │                                                                     │
│       ▼                                                                     │
│  TradeRuntimeConfigServiceImpl.getBootstrapConfig()                         │
│       │                                                                     │
│       ├─► 查询运行时配置(TradeRuntimeConfig)                                 │
│       │                                                                     │
│       ├─► 查询启用的策略(TradeStrategy)                                      │
│       │                                                                     │
│       ├─► 查询策略版本(TradeStrategyVersion)                                 │
│       │                                                                     │
│       ├─► 查询交易对范围(TradeSymbolScope)                                   │
│       │                                                                     │
│       ├─► 查询交易所账户绑定(ExchangeAccountBinding)                         │
│       │                                                                     │
│       ├─► 查询AI模型配置(AiModelConfig)                                     │
│       │                                                                     │
│       ├─► 查询市场API配置(MarketApiConfig)                                  │
│       │                                                                     │
│       ├─► 查询Agent配置(TradeAgentProfile)                                  │
│       │                                                                     │
│       ├─► 查询提示绑定(TradePromptBinding)                                  │
│       │                                                                     │
│       └─► 构建TradeRuntimeBootstrap对象返回                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. 卡密激活流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           卡密激活流程                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  用户端                                                                     │
│       │                                                                     │
│       │ POST /dca/card/activate                                            │
│       │ {cardKey, userId, machineCode}                                     │
│       ▼                                                                     │
│  CardKeyController.activate()                                               │
│       │                                                                     │
│       ▼                                                                     │
│  CardKeyServiceImpl.activateCard()                                          │
│       │                                                                     │
│       ├─► 验证卡密是否存在                                                   │
│       │                                                                     │
│       ├─► 验证卡密状态(unused/activated/expired/disabled)                   │
│       │                                                                     │
│       ├─► 绑定用户ID和机器码                                                │
│       │                                                                     │
│       ├─► 设置激活时间                                                      │
│       │                                                                     │
│       ├─► 更新状态为activated                                               │
│       │                                                                     │
│       └─► 清除缓存并返回                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 三、核心实体说明

### TradeRuntimeBootstrap (运行时引导配置)

```java
{
    // 用户ID
    "userId": 1,
    
    // 运行时配置
    "runtimeConfig": {
        "defaultMode": "paper",           // 运行模式(paper/shadow/live)
        "liveEnabled": false,             // 是否启用实盘
        "maxPositionRatio": 0.4,          // 最大仓位比例
        "maxDailyLoss": -500.00,          // 最大日亏损
        "maxConsecutiveFailures": 3,      // 最大连续失败次数
        "runtimeFlagsJson": "{...}"       // 运行时标志JSON
    },
    
    // 策略信息
    "strategy": {...},
    "strategyVersion": {...},
    "symbolScope": {
        "symbol": "BTCUSDT",
        "exchangeCode": "binance"
    },
    
    // 交易所账户
    "exchangeAccountBinding": {...},
    "exchangeAccount": {...},
    
    // AI模型配置
    "aiModelConfig": {...},
    
    // 数据源配置
    "newsApiConfig": {...},
    "onchainApiConfig": {...},
    "socialApiConfig": {...},
    "marketApiConfig": {...},
    
    // Agent配置
    "agentProfiles": [...],
    "promptBindings": [...],
    "resolvedAgentConfigs": [...],
    
    // 账户上下文
    "runtimeAccountContext": {
        "accountEquity": 10000.00,
        "dailyPnl": 0.0,
        "currentPositionSide": "flat",
        ...
    }
}
```

### CardKey (卡密实体)

```java
{
    "id": 1,
    "cardKey": "BASIC-1234567890-ABCD1234",  // 卡密
    "cardType": "time",                        // 类型(time/permanent/count/trial)
    "cardLevel": "basic",                      // 等级(basic/pro/premium)
    "days": 30,                                // 有效天数
    "counts": null,                            // 使用次数(次数版)
    "status": "unused",                        // 状态(unused/activated/expired/disabled)
    "bindUserId": null,                        // 绑定用户ID
    "bindMachine": null,                       // 绑定机器码
    "activeTime": null,                        // 激活时间
    "expireTime": "2024-05-01T00:00:00Z",     // 过期时间
    "featureFlags": "{...}",                   // 功能开关JSON
    "batchNo": "time-basic-2024-04-01-ABCD1234" // 批次号
}
```

## 四、API接口说明

### 运行时配置接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/dca/trade/runtime/config` | GET | 获取当前运行时配置 |
| `/dca/trade/runtime/config` | PUT | 更新运行时配置 |
| `/dca/trade/runtime/bootstrap` | GET | 获取启动配置 |
| `/dca/trade/runtime/routes` | GET | 获取路由列表 |
| `/dca/trade/runtime/overview` | GET | 获取运行时概览 |
| `/dca/trade/runtime/model-call` | POST | 调用运行时模型 |

### 卡密管理接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/dca/card/list` | GET | 查询卡密列表 |
| `/dca/card/generate` | POST | 批量生成卡密 |
| `/dca/card/activate` | POST | 激活卡密 |
| `/dca/card/validate` | POST | 验证卡密有效性 |
| `/dca/card/{id}/disable` | POST | 禁用卡密 |
| `/dca/card/{id}/enable` | POST | 启用卡密 |
| `/dca/card/my` | GET | 获取我的卡密 |

## 五、与Python Worker的交互

### 1. Python Worker启动流程

```python
# Python Worker启动时调用Java后端获取配置
response = requests.get(
    "http://java-backend/dca/trade/runtime/bootstrap",
    params={"symbol": "BTCUSDT", "exchange": "binance"}
)
bootstrap = response.json()

# 解析配置并启动运行时
runtime_config = bootstrap["runtimeConfig"]
strategy_context = bootstrap["strategy"]
exchange_account = bootstrap["exchangeAccount"]
...
```

### 2. 数据流向

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Java后端      │◄───►│   MySQL数据库   │     │   Redis缓存    │
│  (配置管理)     │     │   (持久化)      │     │   (缓存)       │
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
         │ HTTP API
         ▼
┌─────────────────┐
│  Python Worker  │
│  (交易运行时)   │
└────────┬────────┘
         │
         │ WebSocket/REST
         ▼
┌─────────────────┐
│    交易所API    │
│ (Binance/OKX)  │
└─────────────────┘
```

## 六、关键服务类

### TradeRuntimeConfigServiceImpl

核心职责：
1. 组装运行时引导配置(TradeRuntimeBootstrap)
2. 解析策略配置和版本
3. 解析Agent配置和提示绑定
4. 构建账户上下文
5. 处理运行时标志和触发策略

关键方法：
- `getBootstrapConfig()`: 获取启动配置
- `listBootstrapConfigs()`: 获取所有路由配置
- `getCurrentConfig()`: 获取当前运行时配置
- `saveCurrentConfig()`: 保存运行时配置

### CardKeyServiceImpl

核心职责：
1. 卡密生成和激活
2. 卡密验证和状态管理
3. 用户绑定和机器码绑定
4. 过期检查和状态更新

关键方法：
- `generateCards()`: 批量生成卡密
- `activateCard()`: 激活卡密
- `validateCard()`: 验证卡密有效性
- `checkExpire()`: 检查是否过期
