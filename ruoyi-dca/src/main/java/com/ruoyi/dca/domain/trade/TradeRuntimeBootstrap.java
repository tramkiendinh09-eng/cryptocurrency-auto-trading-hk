package com.ruoyi.dca.domain.trade;

/**
 * 运行时启动引导配置实体
 *
 * 封装Python Worker启动所需的全部配置信息，是Java后端与Python Worker交互的核心数据结构。
 *
 * 数据结构:
 * ```
 * TradeRuntimeBootstrap
 * ├── userId                    # 用户ID
 * ├── runtimeConfig             # 运行时配置(模式、风控参数)
 * ├── strategy                  # 策略信息
 * ├── strategyVersion           # 策略版本
 * ├── symbolScope               # 交易对范围(symbol, exchangeCode)
 * ├── exchangeAccountBinding    # 交易所账户绑定
 * ├── exchangeAccount           # 交易所账户详情
 * ├── aiModelConfig             # AI模型配置
 * ├── newsApiConfig             # 新闻API配置
 * ├── onchainApiConfig          # 链上API配置
 * ├── socialApiConfig           # 社交API配置
 * ├── marketApiConfig           # 市场API配置
 * ├── marketDataConfig          # 市场数据配置
 * ├── runtimeAccountContext     # 账户上下文(权益、盈亏、仓位)
 * ├── positionGuard             # 持仓守护规则
 * ├── promptBindings            # 提示词绑定列表
 * ├── agentProfiles             # Agent档案列表
 * ├── resolvedAgentConfigs      # 解析后的Agent配置
 * └── deliberationPolicy        # 多轮协商策略
 * ```
 *
 * 使用场景:
 * 1. Python Worker启动时调用/bootstrap接口获取此配置
 * 2. 前端/routes接口展示所有路由配置
 * 3. 策略回放时提供完整的上下文信息
 *
 * 与Python Worker的交互:
 * ```
 * Python Worker启动
 *     │
 *     ▼
 * GET /dca/trade/runtime/bootstrap?symbol=BTCUSDT&exchange=binance
 *     │
 *     ▼
 * TradeRuntimeConfigServiceImpl.getBootstrapConfig()
 *     │
 *     ▼
 * 返回TradeRuntimeBootstrap JSON
 *     │
 *     ▼
 * Python Worker解析配置并初始化运行时
 * ```
 *
 * @author ruoyi-dca
 */

import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.domain.MarketDataConfig;
import com.ruoyi.dca.domain.MarketApiConfig;

import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;

public class TradeRuntimeBootstrap {
    private Long userId;
    private TradeRuntimeConfig runtimeConfig;
    private TradeStrategy strategy;
    private TradeStrategyVersion strategyVersion;
    private TradeSymbolScope symbolScope;
    private ExchangeAccountBinding exchangeAccountBinding;
    private ExchangeAccount exchangeAccount;
    private AiModelConfig aiModelConfig;
    private MarketApiConfig newsApiConfig;
    private MarketApiConfig onchainApiConfig;
    private MarketApiConfig socialApiConfig;
    private MarketApiConfig marketApiConfig;
    private MarketDataConfig marketDataConfig;
    private TradeRuntimeAccountContext runtimeAccountContext;
    private TradePositionGuard positionGuard;
    private List<TradePromptBinding> promptBindings = List.of();
    private List<TradeAgentProfile> agentProfiles = List.of();
    private List<ResolvedAgentConfig> resolvedAgentConfigs = List.of();
    private Map<String, Object> deliberationPolicy = new LinkedHashMap<>();

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public TradeRuntimeConfig getRuntimeConfig() {
        return runtimeConfig;
    }

    public void setRuntimeConfig(TradeRuntimeConfig runtimeConfig) {
        this.runtimeConfig = runtimeConfig;
    }

    public TradeStrategy getStrategy() {
        return strategy;
    }

    public void setStrategy(TradeStrategy strategy) {
        this.strategy = strategy;
    }

    public TradeStrategyVersion getStrategyVersion() {
        return strategyVersion;
    }

    public void setStrategyVersion(TradeStrategyVersion strategyVersion) {
        this.strategyVersion = strategyVersion;
    }

    public TradeSymbolScope getSymbolScope() {
        return symbolScope;
    }

    public void setSymbolScope(TradeSymbolScope symbolScope) {
        this.symbolScope = symbolScope;
    }

    public ExchangeAccountBinding getExchangeAccountBinding() {
        return exchangeAccountBinding;
    }

    public void setExchangeAccountBinding(ExchangeAccountBinding exchangeAccountBinding) {
        this.exchangeAccountBinding = exchangeAccountBinding;
    }

    public ExchangeAccount getExchangeAccount() {
        return exchangeAccount;
    }

    public void setExchangeAccount(ExchangeAccount exchangeAccount) {
        this.exchangeAccount = exchangeAccount;
    }

    public AiModelConfig getAiModelConfig() {
        return aiModelConfig;
    }

    public void setAiModelConfig(AiModelConfig aiModelConfig) {
        this.aiModelConfig = aiModelConfig;
    }

    public MarketApiConfig getNewsApiConfig() {
        return newsApiConfig;
    }

    public void setNewsApiConfig(MarketApiConfig newsApiConfig) {
        this.newsApiConfig = newsApiConfig;
    }

    public MarketApiConfig getOnchainApiConfig() {
        return onchainApiConfig;
    }

    public void setOnchainApiConfig(MarketApiConfig onchainApiConfig) {
        this.onchainApiConfig = onchainApiConfig;
    }

    public MarketApiConfig getSocialApiConfig() {
        return socialApiConfig;
    }

    public void setSocialApiConfig(MarketApiConfig socialApiConfig) {
        this.socialApiConfig = socialApiConfig;
    }

    public MarketApiConfig getMarketApiConfig() {
        return marketApiConfig;
    }

    public void setMarketApiConfig(MarketApiConfig marketApiConfig) {
        this.marketApiConfig = marketApiConfig;
    }

    public MarketDataConfig getMarketDataConfig() {
        return marketDataConfig;
    }

    public void setMarketDataConfig(MarketDataConfig marketDataConfig) {
        this.marketDataConfig = marketDataConfig;
    }

    public TradeRuntimeAccountContext getRuntimeAccountContext() {
        return runtimeAccountContext;
    }

    public void setRuntimeAccountContext(TradeRuntimeAccountContext runtimeAccountContext) {
        this.runtimeAccountContext = runtimeAccountContext;
    }

    public TradePositionGuard getPositionGuard() {
        return positionGuard;
    }

    public void setPositionGuard(TradePositionGuard positionGuard) {
        this.positionGuard = positionGuard;
    }

    public List<TradePromptBinding> getPromptBindings() {
        return promptBindings;
    }

    public void setPromptBindings(List<TradePromptBinding> promptBindings) {
        this.promptBindings = promptBindings == null ? List.of() : promptBindings;
    }

    public List<TradeAgentProfile> getAgentProfiles() {
        return agentProfiles;
    }

    public void setAgentProfiles(List<TradeAgentProfile> agentProfiles) {
        this.agentProfiles = agentProfiles == null ? List.of() : agentProfiles;
    }

    public List<ResolvedAgentConfig> getResolvedAgentConfigs() {
        return resolvedAgentConfigs;
    }

    public void setResolvedAgentConfigs(List<ResolvedAgentConfig> resolvedAgentConfigs) {
        this.resolvedAgentConfigs = resolvedAgentConfigs == null ? List.of() : resolvedAgentConfigs;
    }

    public Map<String, Object> getDeliberationPolicy() {
        return deliberationPolicy;
    }

    public void setDeliberationPolicy(Map<String, Object> deliberationPolicy) {
        this.deliberationPolicy = deliberationPolicy == null ? new LinkedHashMap<>() : new LinkedHashMap<>(deliberationPolicy);
    }
}
