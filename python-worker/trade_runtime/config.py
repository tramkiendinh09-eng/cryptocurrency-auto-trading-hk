"""
运行时配置模块 - 定义交易运行时的所有配置模型

包含交易运行时的各种配置模型和工具函数，用于管理和验证运行时配置。

配置层次结构:
```
RuntimeBootstrap (运行时引导配置)
    │
    ├── RuntimeConfig (运行时核心配置)
    │       ├── default_mode: 默认运行模式(paper/shadow/live)
    │       ├── live_enabled: 是否启用实盘模式
    │       ├── max_position_ratio: 最大仓位比例
    │       ├── max_daily_loss: 最大日亏损
    │       ├── max_consecutive_failures: 最大连续失败次数
    │       ├── allowed_symbols: 允许的交易对
    │       ├── allowed_exchanges: 允许的交易所
    │       └── 触发策略配置(market_trigger, news_trigger等)
    │
    ├── RuntimeStrategy (策略配置)
    │       ├── strategy_key: 策略键
    │       ├── strategy_name: 策略名称
    │       └── runtime_mode: 运行模式
    │
    ├── RuntimeExchangeAccount (交易所账户配置)
    │       ├── exchange_code: 交易所代码
    │       ├── api_key_ciphertext: API密钥(加密)
    │       ├── api_secret_ciphertext: API密钥密文(加密)
    │       └── testnet: 是否测试网
    │
    ├── RuntimeAiModelConfig (AI模型配置)
    │       ├── model_code: 模型代码
    │       ├── provider: 提供商
    │       ├── api_endpoint: API端点
    │       └── temperature: 温度参数
    │
    └── RuntimeAccountContext (账户上下文)
            ├── account_equity: 账户权益
            ├── daily_pnl: 日盈亏
            ├── current_position_side: 当前仓位方向
            └── consecutive_failures: 连续失败次数
```

触发策略配置说明:
- triggerMode: 触发模式(EVENT_GATED等)
- marketTrigger: 市场触发条件
  - priceChangePct: 价格变化阈值(%)
  - liquidationNotionalUsd: 清算金额阈值(USD)
  - fundingRateAbs: 资金费率阈值
- newsTrigger: 新闻触发条件
  - scoreThreshold: 情绪得分阈值
- onchainTrigger: 链上触发条件
  - flowUsdThreshold: 资金流阈值(USD)
- socialTrigger: 社交触发条件
  - scoreThreshold: 情绪得分阈值
- triggerMatrix: 信号组合触发矩阵
- cooldownPolicy: 冷却期策略
- llmBudgetPolicy: LLM调用预算策略
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator


# V1版本支持的交易对
V1_ALLOWED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# V1版本支持的交易所
V1_ALLOWED_EXCHANGES = ["BINANCE", "OKX"]

DEFAULT_MIN_POSITION_HOLD_MINUTES = 15


def _deep_merge_dicts(base: Any, override: Any) -> Any:
    if not isinstance(base, dict) or not isinstance(override, dict):
        return deepcopy(override) if override not in (None, "") else deepcopy(base)
    merged = deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _runtime_policy_defaults() -> dict[str, Any]:
    return {
        # 杠杆的默认倍数。上界的硬夹持在 decision/sizing.py，那里不允许
        # 超过 12——把上限写死在代码里，是为了让"配置多打一个零"不至于
        # 变成 100 倍杠杆。
        "maxLeverage": 10.0,
        # 开仓时 size_hint 的下界，口径见 decision/sizing.py。
        "minPositionRatio": 0.05,
        "triggerMode": "EVENT_GATED",
        "marketTrigger": {
            "priceChangePct": 2.5,
            "ruleOnlyPriceChangePct": 1.0,
            "priceAccelerationPct": 1.2,
            "liquidationNotionalUsd": 250000,
            "fundingRateAbs": 0.0,
            "markPriceDeviationPct": 0.0,
        },
        "newsTrigger": {
            "scoreThreshold": 0.90,
            "ruleOnlyScoreThreshold": 0.7,
        },
        "onchainTrigger": {
            "scoreThreshold": 0.9,
            "ruleOnlyScoreThreshold": 0.7,
            "flowUsdThreshold": 1000000,
            "ruleOnlyFlowUsdThreshold": 250000,
        },
        "socialTrigger": {
            "scoreThreshold": 0.85,
            "ruleOnlyScoreThreshold": 0.65,
        },
        "signalMemoryPolicy": {
            "market": {"ttlSeconds": 300, "decayMode": "linear", "combineWithinSeconds": 300},
            "news": {"ttlSeconds": 900, "decayMode": "linear", "combineWithinSeconds": 900},
            "onchain": {"ttlSeconds": 1800, "decayMode": "linear", "combineWithinSeconds": 1800},
            "social": {"ttlSeconds": 600, "decayMode": "linear", "combineWithinSeconds": 600},
        },
        "triggerMatrix": [
            {"code": "strong_news_then_break", "sources": ["news", "market"], "targetDispatchMode": "LLM_ALLOWED"},
            {"code": "onchain_then_market_weakness", "sources": ["onchain", "market"], "targetDispatchMode": "LLM_ALLOWED"},
            {"code": "social_news_market_chain", "sources": ["social", "news", "market"], "targetDispatchMode": "LLM_ALLOWED"},
        ],
        "cooldownPolicy": {"globalSeconds": 300},
        "llmBudgetPolicy": {"perSymbolDailyLimit": 30, "rollingWindowLimit": 3, "rollingWindowMinutes": 20},
        "dedupePolicy": {"sameDirectionOnly": True, "dedupeWindowSeconds": 300},
        "wyckoffShortterm": {
            "enabled": True,
            "min15mBars": 8,
            "effortLookbackBars": 4,
            "breakoutChangePct": 0.15,
            "breakoutVolumeRatio": 0.9,
            "confirmedBreakoutChangePct": 0.35,
            "confirmedBreakoutVolumeRatio": 1.2,
            "springChangePct": 0.08,
            "springVolumeRatio": 0.9,
            "higherTimeframeConflictPct": 0.15,
            "higherTimeframeConfirmPct": 0.35,
            "rangeBalanceChangePct": 0.4,
            "rangeBalanceRangePct": 2.0,
            "markDeviationPenaltyPct": 0.3,
            "requireRetestForReady": True,
            "retestMaxDistancePct": 0.25,
            "maxReadyExtensionPct": 0.9,
            "trapVolumeRatio": 1.8,
            "trapWickRatio": 0.45,
            "trapCooldownBars": 2,
        },
    }


def _parse_json_object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def parse_object_json(raw_value: Any, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    """解析 JSON 对象，供其他模块使用。

    Args:
        raw_value: 输入值，可以是 dict 或 JSON 字符串
        fallback: 解析失败时的默认返回值

    Returns:
        dict[str, Any]: 解析后的字典对象
    """
    if fallback is None:
        fallback = {}
    if not raw_value:
        return dict(fallback)
    try:
        parsed = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
        return parsed if isinstance(parsed, dict) else dict(fallback)
    except (json.JSONDecodeError, TypeError):
        return dict(fallback)


def _normalize_runtime_policy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    defaults = _runtime_policy_defaults()
    merged = dict(payload)
    for key, default_value in defaults.items():
        current_value = payload.get(key)
        if isinstance(default_value, dict):
            merged[key] = _deep_merge_dicts(default_value, current_value or {})
        elif isinstance(default_value, list):
            merged[key] = current_value if isinstance(current_value, list) and current_value else deepcopy(default_value)
        else:
            merged[key] = current_value if current_value not in (None, "") else default_value
    return merged


def normalize_exchange_code(value: Any) -> str | None:
    """标准化交易所代码为小写。"""
    if value in (None, ""):
        return None
    return str(value).strip().lower()


def _normalize_mode(value: object) -> str:
    """
    标准化运行模式

    Args:
        value: 运行模式值

    Returns:
        str: 标准化后的运行模式

    Raises:
        ValueError: 不支持的运行模式
    """
    normalized = str(value or "paper").strip().lower()
    if normalized not in {"paper", "shadow", "live"}:
        raise ValueError(f"Unsupported runtime mode: {value}")
    return normalized


def _normalize_scope_list(value: object, default_values: list[str]) -> list[str]:
    """
    标准化范围列表
    
    Args:
        value: 范围值
        default_values: 默认值列表
        
    Returns:
        list[str]: 标准化后的范围列表
        
    Raises:
        ValueError: 范围值必须是数组
    """
    if value in (None, ""):
        return list(default_values)
    parsed = value
    if isinstance(value, str):
        parsed = json.loads(value)
    if not isinstance(parsed, (list, tuple, set)):
        raise ValueError("Runtime scope values must be arrays")
    normalized: list[str] = []
    for item in parsed:
        canonical = str(item or "").strip().upper()
        if canonical and canonical not in normalized:
            normalized.append(canonical)
    return normalized or list(default_values)


class RuntimeConfig(BaseModel):
    """运行时配置
    
    包含运行时的核心配置参数
    """
    # 默认运行模式
    default_mode: str = Field(default="paper", alias="defaultMode")
    # 是否启用实盘模式
    live_enabled: bool = Field(default=False, alias="liveEnabled")
    runtime_flags_json: str | None = Field(default=None, alias="runtimeFlagsJson")
    # 最大仓位比例
    max_position_ratio: float = Field(default=0.4, alias="maxPositionRatio")
    # 最大日亏损
    max_daily_loss: float = Field(default=-500.0, alias="maxDailyLoss")
    # 最大连续失败次数
    max_consecutive_failures: int = Field(default=3, alias="maxConsecutiveFailures")
    # 允许的交易对
    allowed_symbols: list[str] = Field(
        default_factory=lambda: list(V1_ALLOWED_SYMBOLS),
        validation_alias=AliasChoices("allowedSymbolsJson", "allowedSymbols"),
    )
    # 允许的交易所
    allowed_exchanges: list[str] = Field(
        default_factory=lambda: list(V1_ALLOWED_EXCHANGES),
        validation_alias=AliasChoices("allowedExchangesJson", "allowedExchanges"),
    )
    # 实盘订单是否需要健康账户
    live_order_requires_healthy_account: bool = Field(default=True, alias="liveOrderRequiresHealthyAccount")

    deliberation_enabled: bool = Field(default=False, alias="deliberationEnabled")
    deliberation_max_rounds: int = Field(default=0, alias="deliberationMaxRounds")
    deliberation_fail_open: bool = Field(default=True, alias="deliberationFailOpen")
    route_max_concurrency: int = Field(default=1, alias="routeMaxConcurrency")
    route_scheduler_mode: str = Field(default="SERIAL", alias="routeSchedulerMode")
    trigger_mode: str = Field(default="EVENT_GATED", alias="triggerMode")
    market_trigger: dict[str, Any] = Field(default_factory=lambda: deepcopy(_runtime_policy_defaults()["marketTrigger"]), alias="marketTrigger")
    news_trigger: dict[str, Any] = Field(default_factory=lambda: deepcopy(_runtime_policy_defaults()["newsTrigger"]), alias="newsTrigger")
    onchain_trigger: dict[str, Any] = Field(default_factory=lambda: deepcopy(_runtime_policy_defaults()["onchainTrigger"]), alias="onchainTrigger")
    social_trigger: dict[str, Any] = Field(default_factory=lambda: deepcopy(_runtime_policy_defaults()["socialTrigger"]), alias="socialTrigger")
    signal_memory_policy: dict[str, Any] = Field(default_factory=lambda: deepcopy(_runtime_policy_defaults()["signalMemoryPolicy"]), alias="signalMemoryPolicy")
    trigger_matrix: list[dict[str, Any]] = Field(default_factory=lambda: deepcopy(_runtime_policy_defaults()["triggerMatrix"]), alias="triggerMatrix")
    cooldown_policy: dict[str, Any] = Field(default_factory=lambda: deepcopy(_runtime_policy_defaults()["cooldownPolicy"]), alias="cooldownPolicy")
    llm_budget_policy: dict[str, Any] = Field(default_factory=lambda: deepcopy(_runtime_policy_defaults()["llmBudgetPolicy"]), alias="llmBudgetPolicy")
    dedupe_policy: dict[str, Any] = Field(default_factory=lambda: deepcopy(_runtime_policy_defaults()["dedupePolicy"]), alias="dedupePolicy")
    wyckoff_shortterm: dict[str, Any] = Field(default_factory=lambda: deepcopy(_runtime_policy_defaults()["wyckoffShortterm"]), alias="wyckoffShortterm")
    # 只存在于 runtimeFlagsJson 里，需要显式声明才不会在 model_dump 时被丢掉。
    # 缺省与 decision/sizing.py 的 DEFAULT_LEVERAGE 一致：读不到配置时
    # 往保守一侧倒，杠杆太小只是一单被拒，太大是爆仓。
    max_leverage: float = Field(default=10.0, alias="maxLeverage")
    # 同样只存在于 runtimeFlagsJson 里。不显式声明，model_dump 就会把它丢掉，
    # 而 supervisor 拿到的正是 model_dump 的结果——下界会静默地退回代码默认值。
    min_position_ratio: float = Field(default=0.05, alias="minPositionRatio")

    @model_validator(mode="before")
    @classmethod
    def normalize_runtime_policy_fields(cls, value):
        if not isinstance(value, dict):
            return value
        resolved = dict(value)
        runtime_policy = _parse_json_object(resolved.get("runtimeFlagsJson") or resolved.get("runtime_flags_json"))
        direct_policy = {
            "maxLeverage": resolved.get("maxLeverage") or resolved.get("max_leverage"),
            "minPositionRatio": resolved.get("minPositionRatio") or resolved.get("min_position_ratio"),
            "triggerMode": resolved.get("triggerMode") or resolved.get("trigger_mode"),
            "marketTrigger": resolved.get("marketTrigger") or resolved.get("market_trigger"),
            "newsTrigger": resolved.get("newsTrigger") or resolved.get("news_trigger"),
            "onchainTrigger": resolved.get("onchainTrigger") or resolved.get("onchain_trigger"),
            "socialTrigger": resolved.get("socialTrigger") or resolved.get("social_trigger"),
            "signalMemoryPolicy": resolved.get("signalMemoryPolicy") or resolved.get("signal_memory_policy"),
            "triggerMatrix": resolved.get("triggerMatrix") or resolved.get("trigger_matrix"),
            "cooldownPolicy": resolved.get("cooldownPolicy") or resolved.get("cooldown_policy"),
            "llmBudgetPolicy": resolved.get("llmBudgetPolicy") or resolved.get("llm_budget_policy"),
            "dedupePolicy": resolved.get("dedupePolicy") or resolved.get("dedupe_policy"),
            "wyckoffShortterm": resolved.get("wyckoffShortterm") or resolved.get("wyckoff_shortterm"),
        }
        merged_policy = dict(runtime_policy)
        for key, item in direct_policy.items():
            if item in (None, ""):
                continue
            if isinstance(item, dict):
                merged_policy[key] = _deep_merge_dicts(merged_policy.get(key) or {}, item)
            else:
                merged_policy[key] = item
        normalized_policy = _normalize_runtime_policy_payload(merged_policy)
        resolved["runtimeFlagsJson"] = json.dumps(normalized_policy, ensure_ascii=True, separators=(",", ":"))
        for key in (
            "maxLeverage",
            "minPositionRatio",
            "triggerMode",
            "marketTrigger",
            "newsTrigger",
            "onchainTrigger",
            "socialTrigger",
            "signalMemoryPolicy",
            "triggerMatrix",
            "cooldownPolicy",
            "llmBudgetPolicy",
            "dedupePolicy",
            "wyckoffShortterm",
        ):
            resolved[key] = normalized_policy[key]
        return resolved
    @field_validator("default_mode", mode="before")
    @classmethod
    def normalize_default_mode(cls, value):
        """标准化默认运行模式"""
        return _normalize_mode(value)

    @field_validator("max_leverage", mode="before")
    @classmethod
    def normalize_max_leverage(cls, value):
        """配置缺失或非法时退回 10 倍（同 decision/sizing.py 的 DEFAULT_LEVERAGE）。
        上界的硬夹持在 decision/sizing.py，这里只保证类型与下界。"""
        if value in (None, ""):
            return 10.0
        try:
            resolved = float(value)
        except (TypeError, ValueError):
            return 10.0
        return resolved if resolved > 0 else 10.0

    @field_validator("min_position_ratio", mode="before")
    @classmethod
    def normalize_min_position_ratio(cls, value):
        """配置缺失或非法时退回 0.05（同 decision/sizing.py 的
        DEFAULT_MIN_POSITION_RATIO）。0 是合法取值，表示不要下界。"""
        if value in (None, ""):
            return 0.05
        try:
            resolved = float(value)
        except (TypeError, ValueError):
            return 0.05
        return resolved if resolved >= 0 else 0.05

    @field_validator("max_position_ratio", mode="before")
    @classmethod
    def normalize_max_position_ratio(cls, value):
        """标准化最大仓位比例"""
        return 0.4 if value in (None, "") else float(value)

    @field_validator("max_daily_loss", mode="before")
    @classmethod
    def normalize_max_daily_loss(cls, value):
        """标准化最大日亏损"""
        return -500.0 if value in (None, "") else float(value)

    @field_validator("max_consecutive_failures", mode="before")
    @classmethod
    def normalize_max_consecutive_failures(cls, value):
        """标准化最大连续失败次数"""
        return 3 if value in (None, "") else int(value)

    @field_validator("allowed_symbols", mode="before")
    @classmethod
    def normalize_allowed_symbols(cls, value):
        """标准化允许的交易对"""
        return _normalize_scope_list(value, V1_ALLOWED_SYMBOLS)

    @field_validator("allowed_exchanges", mode="before")
    @classmethod
    def normalize_allowed_exchanges(cls, value):
        """标准化允许的交易所"""
        return _normalize_scope_list(value, V1_ALLOWED_EXCHANGES)

    @field_validator("live_order_requires_healthy_account", mode="before")
    @classmethod
    def normalize_live_order_requires_healthy_account(cls, value):
        """标准化实盘订单健康账户要求"""
        return True if value in (None, "") else bool(value)

    @field_validator("deliberation_enabled", mode="before")
    @classmethod
    def normalize_deliberation_enabled(cls, value):
        return False if value in (None, "") else bool(value)

    @field_validator("deliberation_max_rounds", mode="before")
    @classmethod
    def normalize_deliberation_max_rounds(cls, value):
        return 0 if value in (None, "") else int(value)

    @field_validator("deliberation_fail_open", mode="before")
    @classmethod
    def normalize_deliberation_fail_open(cls, value):
        return True if value in (None, "") else bool(value)

    @field_validator("route_max_concurrency", mode="before")
    @classmethod
    def normalize_route_max_concurrency(cls, value):
        if value in (None, ""):
            return 1
        return max(1, int(value))

    @field_validator("route_scheduler_mode", mode="before")
    @classmethod
    def normalize_route_scheduler_mode(cls, value):
        normalized = str(value or "SERIAL").strip().upper()
        if normalized not in {"SERIAL", "THREAD_POOL"}:
            return "SERIAL"
        return normalized

    def effective_mode(self) -> str:
        """
        获取有效运行模式
        
        Returns:
            str: 有效运行模式
        """
        if self.default_mode == "live" and not self.live_enabled:
            return "shadow"
        return self.default_mode

    model_config = {
        "populate_by_name": True,
    }


class RuntimeStrategy(BaseModel):
    """运行时策略配置
    
    包含策略的基本信息和运行模式
    """
    # 策略ID
    id: int | None = None
    # 策略键
    strategy_key: str | None = Field(default=None, alias="strategyKey")
    # 策略名称
    strategy_name: str | None = Field(default=None, alias="strategyName")
    # 运行模式
    runtime_mode: str | None = Field(default=None, alias="runtimeMode")
    # 是否启用
    enabled: bool | None = None

    @field_validator("runtime_mode", mode="before")
    @classmethod
    def normalize_runtime_mode(cls, value):
        """标准化运行模式"""
        if value in (None, ""):
            return None
        return _normalize_mode(value)

    model_config = {
        "populate_by_name": True,
    }


class RuntimeStrategyVersion(BaseModel):
    """运行时策略版本
    
    包含策略版本的详细信息
    """
    # 版本ID
    id: int | None = None
    # 策略ID
    strategy_id: int | None = Field(default=None, alias="strategyId")
    # 版本号
    version_no: int | None = Field(default=None, alias="versionNo")
    # 配置JSON
    config_json: str | None = Field(default=None, alias="configJson")

    model_config = {
        "populate_by_name": True,
    }


class RuntimeSymbolScope(BaseModel):
    """运行时交易对范围
    
    定义策略适用的交易对和交易所
    """
    # 策略ID
    strategy_id: int | None = Field(default=None, alias="strategyId")
    # 交易对
    symbol: str | None = None
    # 交易所代码
    exchange_code: str | None = Field(default=None, alias="exchangeCode")

    @field_validator("exchange_code", mode="before")
    @classmethod
    def normalize_exchange_code(cls, value):
        """标准化交易所代码"""
        return normalize_exchange_code(value)

    model_config = {
        "populate_by_name": True,
    }


class RuntimeExchangeAccountBinding(BaseModel):
    """运行时交易所账户绑定
    
    定义策略与交易所账户的绑定关系
    """
    # 策略ID
    strategy_id: int | None = Field(default=None, alias="strategyId")
    # 账户ID
    account_id: int | None = Field(default=None, alias="accountId")
    # 交易所代码
    exchange_code: str | None = Field(default=None, alias="exchangeCode")
    # 是否启用
    enabled: bool | None = None

    @field_validator("exchange_code", mode="before")
    @classmethod
    def normalize_exchange_code(cls, value):
        """标准化交易所代码"""
        return normalize_exchange_code(value)

    model_config = {
        "populate_by_name": True,
    }


class RuntimeExchangeAccount(BaseModel):
    """运行时交易所账户
    
    包含交易所账户的详细信息
    """
    # 账户ID
    id: int | None = None
    # 交易所代码
    exchange_code: str | None = Field(default=None, alias="exchangeCode")
    # 账户名称
    account_name: str | None = Field(default=None, alias="accountName")
    # API密钥密文
    api_key_ciphertext: str | None = Field(default=None, alias="apiKeyCiphertext")
    # API密钥密文
    api_secret_ciphertext: str | None = Field(default=None, alias="apiSecretCiphertext")
    # 密码密文
    passphrase_ciphertext: str | None = Field(default=None, alias="passphraseCiphertext")
    # API基础URL
    api_base_url: str | None = Field(default=None, alias="apiBaseUrl")
    # 是否测试网
    testnet: bool = False
    # 是否演示交易
    demo_trading: bool = Field(default=False, alias="demoTrading")
    # 是否启用
    enabled: bool | None = None
    # 健康状态
    health_status: str | None = Field(default=None, alias="healthStatus")
    # 最后验证时间
    last_validated_at: str | None = Field(default=None, alias="lastValidatedAt")
    # 最后错误信息
    last_error_message: str | None = Field(default=None, alias="lastErrorMessage")

    @field_validator("exchange_code", mode="before")
    @classmethod
    def normalize_exchange_code(cls, value):
        """标准化交易所代码"""
        return normalize_exchange_code(value)

    @field_validator("health_status", mode="before")
    @classmethod
    def normalize_health_status(cls, value):
        """标准化健康状态"""
        if value in (None, ""):
            return None
        return str(value).strip().lower()

    model_config = {
        "populate_by_name": True,
    }


class RuntimeAiModelConfig(BaseModel):
    """运行时AI模型配置
    
    包含AI模型的详细配置
    """
    # 模型ID
    id: int | None = None
    # 模型键
    model_key: str | None = Field(default=None, alias="modelKey")
    # 模型代码
    model_code: str | None = Field(default=None, alias="modelCode")
    # 模型名称
    model_name: str | None = Field(default=None, alias="modelName")
    # 提供商
    provider: str | None = None
    # API端点
    api_endpoint: str | None = Field(default=None, alias="apiEndpoint")
    # API基础URL
    api_base_url: str | None = Field(default=None, alias="apiBaseUrl")
    # API版本
    api_version: str | None = Field(default=None, alias="apiVersion")
    # 模型版本
    model_version: str | None = Field(default=None, alias="modelVersion")
    # 超时时间（秒）
    timeout_seconds: int | None = Field(default=None, alias="timeoutSeconds")
    # 重试次数
    retry_times: int | None = Field(default=None, alias="retryTimes")
    # 优先级
    priority: int | None = None
    # 温度参数
    temperature: float | None = None
    # 采样参数
    top_p: float | None = Field(default=None, alias="topP")
    # 最大 tokens
    max_tokens: int | None = Field(default=None, alias="maxTokens")
    # 是否启用
    is_enabled: int | None = Field(default=None, alias="isEnabled")
    # 是否默认
    is_default: int | None = Field(default=None, alias="isDefault")

    model_config = {
        "populate_by_name": True,
        "protected_namespaces": (),
    }


class RuntimeMarketApiConfig(BaseModel):
    """运行时市场API配置
    
    包含市场数据API的详细配置
    """
    # 配置ID
    id: int | None = None
    # 版本号
    version_no: int | None = Field(default=None, alias="versionNo")
    # 配置名称
    config_name: str | None = Field(default=None, alias="configName")
    # 数据类别
    data_category: str | None = Field(default=None, alias="dataCategory")
    # 数据子类型
    data_sub_type: str | None = Field(default=None, alias="dataSubType")
    # 传输类型
    transport_type: str | None = Field(default=None, alias="transportType")
    # 供应商代码
    vendor_code: str | None = Field(default=None, alias="vendorCode")
    # 市场范围
    market_scope: str | None = Field(default=None, alias="marketScope")
    # API名称
    api_name: str | None = Field(default=None, alias="apiName")
    # API URL
    api_url: str | None = Field(default=None, alias="apiUrl")
    # WebSocket基础URL
    ws_base_url: str | None = Field(default=None, alias="wsBaseUrl")
    # WebSocket路径
    ws_path: str | None = Field(default=None, alias="wsPath")
    # WebSocket流名称模板
    ws_stream_name_template: str | None = Field(default=None, alias="wsStreamNameTemplate")
    # WebSocket合并启用
    ws_combined_enabled: bool | None = Field(default=None, alias="wsCombinedEnabled")
    # WebSocket交易对小写
    ws_symbol_lowercase: bool | None = Field(default=None, alias="wsSymbolLowercase")
    # WebSocket ping间隔（秒）
    ws_ping_interval_seconds: int | None = Field(default=None, alias="wsPingIntervalSeconds")
    # WebSocket pong超时（秒）
    ws_pong_timeout_seconds: int | None = Field(default=None, alias="wsPongTimeoutSeconds")
    # WebSocket连接TTL（小时）
    ws_connection_ttl_hours: int | None = Field(default=None, alias="wsConnectionTtlHours")
    # WebSocket每连接最大流数
    ws_max_streams_per_connection: int | None = Field(default=None, alias="wsMaxStreamsPerConnection")
    # WebSocket每秒控制消息数
    ws_control_messages_per_second: int | None = Field(default=None, alias="wsControlMessagesPerSecond")
    ws_reconnect_attempts: int | None = Field(default=None, alias="wsReconnectAttempts")
    # 文档参考URL
    doc_reference_url: str | None = Field(default=None, alias="docReferenceUrl")
    # HTTP方法
    http_method: str | None = Field(default=None, alias="httpMethod")
    # 响应路径
    response_path: str | None = Field(default=None, alias="responsePath")
    # 字段映射
    field_mapping: str | None = Field(default=None, alias="fieldMapping")
    # 超时时间
    timeout: int | None = None
    # 是否启用
    enabled: str | None = None
    # 优先级
    priority: int | None = None
    # 数据转换
    data_transform: str | None = Field(default=None, alias="dataTransform")
    # 是否使用代理
    use_proxy: str | None = Field(default=None, alias="useProxy")
    # 代理URL
    proxy_url: str | None = Field(default=None, alias="proxyUrl")
    # 应用交易对
    apply_symbols: str | None = Field(default=None, alias="applySymbols")
    # 更新时间
    update_time: str | None = Field(default=None, alias="updateTime")

    model_config = {
        "populate_by_name": True,
    }


class RuntimeMarketDataConfig(BaseModel):
    """运行时市场数据配置
    
    包含市场数据收集的详细配置
    """
    # 配置ID
    id: int | None = None
    # 配置名称
    config_name: str | None = Field(default=None, alias="configName")
    # 交易对
    symbol: str | None = None
    # 是否启用
    enabled: str | None = None
    # 收集间隔
    collect_interval: int | None = Field(default=None, alias="collectInterval")
    # 数据源
    data_sources: str | None = Field(default=None, alias="dataSources")
    # 是否收集K线
    collect_kline: str | None = Field(default=None, alias="collectKline")
    # K线周期
    kline_periods: str | None = Field(default=None, alias="klinePeriods")
    # 是否收集恐慌贪婪指数
    collect_fear_greed: str | None = Field(default=None, alias="collectFearGreed")
    # 是否收集链上数据
    collect_onchain: str | None = Field(default=None, alias="collectOnchain")

    model_config = {
        "populate_by_name": True,
    }


class RuntimeAccountContext(BaseModel):
    """运行时账户上下文

    包含账户的实时状态信息
    """
    # 账户权益
    account_equity: float = Field(default=10_000.0, alias="accountEquity")
    # 日盈亏
    daily_pnl: float = Field(default=0.0, alias="dailyPnl")
    realized_pnl: float = Field(default=0.0, alias="realizedPnl")
    unrealized_pnl: float = Field(default=0.0, alias="unrealizedPnl")
    # 当前仓位方向
    current_position_side: str = Field(default="flat", alias="currentPositionSide")
    # 当前仓位数量
    current_position_quantity: float = Field(default=0.0, alias="currentPositionQuantity")
    # 当前仓位名义价值
    current_position_notional: float = Field(default=0.0, alias="currentPositionNotional")
    entry_price: float = Field(default=0.0, alias="entryPrice")
    max_drawdown_pct: float = Field(default=0.0, alias="maxDrawdownPct")
    peak_account_equity: float = Field(default=0.0, alias="peakAccountEquity")
    # 连续失败次数
    consecutive_failures: int = Field(default=0, alias="consecutiveFailures")
    current_position_opened_at: str | None = Field(default=None, alias="currentPositionOpenedAt")
    current_time: str | None = Field(default=None, alias="currentTime")
    current_position_holding_minutes: int | None = Field(default=None, alias="currentPositionHoldingMinutes")
    # 开仓时的trace_id，用于平仓时关联开仓记录
    entry_trace_id: str | None = Field(default=None, alias="entryTraceId")

    model_config = {
        "populate_by_name": True,
    }


class RuntimePromptBinding(BaseModel):
    id: int | None = None
    binding_name: str | None = Field(default=None, alias="bindingName")
    binding_scope: str | None = Field(default=None, alias="bindingScope")
    template_code: str | None = Field(default=None, alias="templateCode")
    fallback_template_code: str | None = Field(default=None, alias="fallbackTemplateCode")
    model_id: int | None = Field(default=None, alias="modelId")
    output_schema_code: str | None = Field(default=None, alias="outputSchemaCode")
    priority: int | None = None
    mode_scope_json: str | None = Field(default=None, alias="modeScopeJson")
    event_strength_scope_json: str | None = Field(default=None, alias="eventStrengthScopeJson")
    enabled: bool | None = None
    remark: str | None = None

    model_config = {
        "populate_by_name": True,
        "protected_namespaces": (),
    }


class RuntimeAgentProfile(BaseModel):
    id: int | None = None
    agent_code: str | None = Field(default=None, alias="agentCode")
    agent_name: str | None = Field(default=None, alias="agentName")
    agent_type: str | None = Field(default=None, alias="agentType")
    enabled: bool | None = None
    llm_enabled: bool | None = Field(default=None, alias="llmEnabled")
    dialogue_enabled: bool | None = Field(default=None, alias="dialogueEnabled")
    max_dialogue_rounds: int | None = Field(default=None, alias="maxDialogueRounds")
    speak_order: int | None = Field(default=None, alias="speakOrder")
    timeout_seconds: int | None = Field(default=None, alias="timeoutSeconds")
    max_retries: int | None = Field(default=None, alias="maxRetries")
    temperature_override: float | None = Field(default=None, alias="temperatureOverride")
    top_p_override: float | None = Field(default=None, alias="topPOverride")
    max_tokens_override: int | None = Field(default=None, alias="maxTokensOverride")
    structured_schema_code: str | None = Field(default=None, alias="structuredSchemaCode")
    tool_policy_json: str | None = Field(default=None, alias="toolPolicyJson")
    runtime_options_json: str | None = Field(default=None, alias="runtimeOptionsJson")
    remark: str | None = None

    model_config = {
        "populate_by_name": True,
    }


class RuntimeResolvedAgentConfig(BaseModel):
    agent_code: str | None = Field(default=None, alias="agentCode")
    agent_type: str | None = Field(default=None, alias="agentType")
    enabled: bool | None = None
    llm_enabled: bool | None = Field(default=None, alias="llmEnabled")
    model_id: int | None = Field(default=None, alias="modelId")
    model_code: str | None = Field(default=None, alias="modelCode")
    model_provider: str | None = Field(default=None, alias="modelProvider")
    template_code: str | None = Field(default=None, alias="templateCode")
    fallback_template_code: str | None = Field(default=None, alias="fallbackTemplateCode")
    output_schema_code: str | None = Field(default=None, alias="outputSchemaCode")
    source_profile_id: int | None = Field(default=None, alias="sourceProfileId")
    source_binding_id: int | None = Field(default=None, alias="sourceBindingId")
    resolution_source: str | None = Field(default=None, alias="resolutionSource")

    model_config = {
        "populate_by_name": True,
        "protected_namespaces": (),
    }


class RuntimePositionGuard(BaseModel):
    id: int | None = None
    guard_name: str | None = Field(default=None, alias="guardName")
    scope_type: str | None = Field(default=None, alias="scopeType")
    strategy_id: int | None = Field(default=None, alias="strategyId")
    symbol: str | None = None
    exchange_code: str | None = Field(default=None, alias="exchangeCode")
    stop_loss_pct: float | None = Field(default=None, alias="stopLossPct")
    take_profit_pct: float | None = Field(default=None, alias="takeProfitPct")
    max_holding_minutes: int | None = Field(default=None, alias="maxHoldingMinutes")
    enabled: bool | None = None

    @field_validator("exchange_code", mode="before")
    @classmethod
    def normalize_exchange_code(cls, value):
        return normalize_exchange_code(value)

    model_config = {
        "populate_by_name": True,
    }


class RuntimeBootstrap(BaseModel):
    user_id: int | None = Field(default=None, alias="userId")
    """运行时引导配置
    
    包含所有运行时配置的集合
    """
    # 运行时配置
    runtime_config: RuntimeConfig = Field(default_factory=RuntimeConfig, alias="runtimeConfig")
    # 策略
    strategy: RuntimeStrategy | None = None
    # 策略版本
    strategy_version: RuntimeStrategyVersion | None = Field(default=None, alias="strategyVersion")
    # 交易对范围
    symbol_scope: RuntimeSymbolScope | None = Field(default=None, alias="symbolScope")
    # 交易所账户绑定
    exchange_account_binding: RuntimeExchangeAccountBinding | None = Field(default=None, alias="exchangeAccountBinding")
    # 交易所账户
    exchange_account: RuntimeExchangeAccount | None = Field(default=None, alias="exchangeAccount")
    # AI模型配置
    ai_model_config: RuntimeAiModelConfig | None = Field(default=None, alias="aiModelConfig")
    # 新闻API配置
    news_api_config: RuntimeMarketApiConfig | None = Field(default=None, alias="newsApiConfig")
    # 链上API配置
    onchain_api_config: RuntimeMarketApiConfig | None = Field(default=None, alias="onchainApiConfig")
    # 社交API配置
    social_api_config: RuntimeMarketApiConfig | None = Field(default=None, alias="socialApiConfig")
    # 市场API配置
    market_api_config: RuntimeMarketApiConfig | None = Field(default=None, alias="marketApiConfig")
    # 市场数据配置
    market_data_config: RuntimeMarketDataConfig | None = Field(default=None, alias="marketDataConfig")
    # 运行时账户上下文
    runtime_account_context: RuntimeAccountContext | None = Field(default=None, alias="runtimeAccountContext")
    position_guard: RuntimePositionGuard | None = Field(default=None, alias="positionGuard")
    prompt_bindings: list[RuntimePromptBinding] = Field(default_factory=list, alias="promptBindings")
    agent_profiles: list[RuntimeAgentProfile] = Field(default_factory=list, alias="agentProfiles")
    resolved_agent_configs: list[RuntimeResolvedAgentConfig] = Field(default_factory=list, alias="resolvedAgentConfigs")
    deliberation_policy: dict[str, Any] = Field(default_factory=dict, alias="deliberationPolicy")

    model_config = {
        "populate_by_name": True,
    }
