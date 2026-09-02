package com.ruoyi.dca.service.trade.impl;

/**
 * 运行时配置服务实现类
 *
 * 提供交易运行时配置的管理和启动引导配置组装功能。
 * 这是Java后端与Python Worker交互的核心服务。
 *
 * 核心职责:
 * 1. 运行时配置管理: 获取和保存运行时全局配置
 * 2. 启动配置组装: 为Python Worker组装完整的TradeRuntimeBootstrap对象
 * 3. 策略解析: 解析策略配置和版本
 * 4. Agent配置解析: 解析Agent档案和提示绑定
 * 5. 账户上下文构建: 构建账户权益、盈亏等上下文信息
 * 6. 风控配置解析: 解析持仓守护规则
 *
 * 启动配置组装流程:
 * ┌─────────────────────────────────────────────────────────────────────────────┐
 * │                           启动配置组装流程                                    │
 * ├─────────────────────────────────────────────────────────────────────────────┤
 * │                                                                             │
 * │  getBootstrapConfig(symbol, exchange)                                       │
 * │      │                                                                      │
 * │      ├─► 查询运行时配置(TradeRuntimeConfig)                                  │
 * │      │                                                                      │
 * │      ├─► 查询启用的策略(TradeStrategy)                                       │
 * │      │                                                                      │
 * │      ├─► 查询策略版本(TradeStrategyVersion)                                 │
 * │      │                                                                      │
 * │      ├─► 查询交易对范围(TradeSymbolScope)                                   │
 * │      │                                                                      │
 * │      ├─► 查询交易所账户绑定(ExchangeAccountBinding)                         │
 * │      │                                                                      │
 * │      ├─► 查询AI模型配置(AiModelConfig)                                      │
 * │      │                                                                      │
 * │      ├─► 查询数据源API配置(MarketApiConfig)                                 │
 * │      │     - newsApiConfig: 新闻API                                         │
 * │      │     - onchainApiConfig: 链上API                                     │
 * │      │     - socialApiConfig: 社交API                                      │
 * │      │     - marketApiConfig: 市场API                                      │
 * │      │                                                                      │
 * │      ├─► 查询Agent配置(TradeAgentProfile)                                   │
 * │      │                                                                      │
 * │      ├─► 查询提示绑定(TradePromptBinding)                                  │
 * │      │                                                                      │
 * │      ├─► 构建账户上下文(RuntimeAccountContext)                              │
 * │      │     - accountEquity: 账户权益                                       │
 * │      │     - dailyPnl: 日盈亏                                              │
 * │      │     - currentPositionSide: 当前仓位方向                              │
 * │      │     - recentFailures: 最近失败次数                                   │
 * │      │                                                                      │
 * │      └─► 构建TradeRuntimeBootstrap对象返回                                  │
 * │                                                                             │
 * └─────────────────────────────────────────────────────────────────────────────┘
 *
 * 与Python Worker的交互:
 * Python Worker启动时调用/bootstrap接口，本服务组装完整配置返回。
 * 配置包括运行时参数、策略、账户、Agent、数据源等所有必要信息。
 *
 * @author ruoyi-dca
 */

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.domain.MarketDataConfig;
import com.ruoyi.dca.domain.MarketApiConfig;
import com.ruoyi.dca.domain.enums.TradeRuntimeMode;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.trade.TradeAgentProfile;
import com.ruoyi.dca.domain.trade.ExchangeAccount;
import com.ruoyi.dca.domain.trade.ExchangeAccountBinding;
import com.ruoyi.dca.domain.trade.ResolvedAgentConfig;
import com.ruoyi.dca.domain.trade.TradeDataSourceBinding;
import com.ruoyi.dca.domain.trade.TradePromptBinding;
import com.ruoyi.dca.domain.trade.TradePositionGuard;
import com.ruoyi.dca.domain.trade.TradeRuntimeAccountContext;
import com.ruoyi.dca.domain.trade.TradeRuntimeBootstrap;
import com.ruoyi.dca.domain.trade.TradeRuntimeConfig;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.domain.trade.TradeStrategyVersion;
import com.ruoyi.dca.constants.TradeConstants;
import com.ruoyi.dca.domain.trade.TradeSymbolScope;
import com.ruoyi.dca.mapper.runtime.TradeExecutionMapper;
import com.ruoyi.dca.mapper.runtime.TradePositionGuardMapper;
import com.ruoyi.dca.mapper.trade.TradeDataSourceBindingMapper;
import com.ruoyi.dca.mapper.trade.ExchangeAccountMapper;
import com.ruoyi.dca.mapper.trade.TradeAgentProfileMapper;
import com.ruoyi.dca.mapper.trade.TradePromptBindingMapper;
import com.ruoyi.dca.mapper.trade.TradeRuntimeConfigMapper;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.IAiModelConfigService;
import com.ruoyi.dca.service.IMarketApiConfigService;
import com.ruoyi.dca.service.IMarketDataConfigService;
import com.ruoyi.dca.service.trade.ITradeRuntimeConfigService;
import com.ruoyi.dca.support.TradeRuntimeTimeUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeParseException;
import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.Comparator;

@Service
public class TradeRuntimeConfigServiceImpl implements ITradeRuntimeConfigService {

    private static final BigDecimal DEFAULT_MAX_POSITION_RATIO = new BigDecimal("0.40");
    private static final BigDecimal DEFAULT_MAX_DAILY_LOSS = new BigDecimal("-500.00");
    private static final int DEFAULT_MAX_CONSECUTIVE_FAILURES = 3;
    private static final int DEFAULT_RETENTION_DAYS = 30;
    private static final int DEFAULT_DELIBERATION_MAX_ROUNDS = 0;
    private static final int DEFAULT_ROUTE_MAX_CONCURRENCY = 1;
    private static final String DEFAULT_ROUTE_SCHEDULER_MODE = "SERIAL";
    private static final String DEFAULT_JSON_OBJECT = "{}";
    private static final String NEWS_CATEGORY = "NEWS";
    private static final String ONCHAIN_CATEGORY = "ONCHAIN";
    private static final String SOCIAL_CATEGORY = "SOCIAL";
    private static final String PRICE_CATEGORY = "PRICE";
    private static final String MARKET_TICK_EVENT = "market_tick";
    private static final BigDecimal DEFAULT_ACCOUNT_EQUITY = new BigDecimal("10000.00");
    private static final BigDecimal ZERO_DECIMAL = BigDecimal.ZERO;
    private static final int RECENT_FAILURE_WINDOW = 10;
    private static final String DEFAULT_TRIGGER_MODE = "EVENT_GATED";
    private static final Set<String> ALWAYS_INCLUDED_PROMPT_BINDING_SCOPES = Set.of("SUPERVISOR");
    private static final Map<String, String> BINDING_SCOPE_AGENT_CODE_MAP = Map.of(
        "SUPERVISOR", "supervisor_agent",
        "MARKET_AGENT", "market_agent",
        "NEWS_AGENT", "news_agent",
        "ONCHAIN_AGENT", "onchain_agent",
        "SOCIAL_AGENT", "social_agent",
        "DELIBERATION_REFEREE", "deliberation_referee"
    );

    @Autowired
    private TradeRuntimeConfigMapper tradeRuntimeConfigMapper;

    @Autowired
    private TradeStrategyMapper tradeStrategyMapper;

    @Autowired
    private ExchangeAccountMapper exchangeAccountMapper;

    @Autowired
    private TradeDataSourceBindingMapper tradeDataSourceBindingMapper;

    @Autowired
    private TradeExecutionMapper tradeExecutionMapper;

    @Autowired
    private TradePromptBindingMapper tradePromptBindingMapper;

    @Autowired
    private TradeAgentProfileMapper tradeAgentProfileMapper;

    @Autowired
    private TradePositionGuardMapper tradePositionGuardMapper;

    @Autowired
    private IAiModelConfigService aiModelConfigService;

    @Autowired
    private IMarketApiConfigService marketApiConfigService;

    @Autowired
    private IMarketDataConfigService marketDataConfigService;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    public TradeRuntimeConfig getCurrentConfig() {
        TradeRuntimeConfig config = tradeRuntimeConfigMapper.selectCurrentConfig();
        if (config == null) {
            TradeRuntimeConfig fallback = new TradeRuntimeConfig();
            fallback.setDefaultMode(TradeRuntimeMode.PAPER);
            fallback.setLiveEnabled(Boolean.FALSE);
            return applyRuntimeDefaults(fallback);
        }
        return applyRuntimeDefaults(config);
    }

    @Override
    public TradeRuntimeBootstrap getBootstrapConfig(String symbol, String exchange) {
        for (TradeRuntimeBootstrap bootstrap : selectBootstrapConfigsInternal(symbol, exchange, false)) {
            return bootstrap;
        }
        TradeRuntimeBootstrap bootstrap = new TradeRuntimeBootstrap();
        bootstrap.setUserId(resolveCurrentUserId());
        bootstrap.setRuntimeConfig(getCurrentConfig());
        return applyControlPlaneConfigs(bootstrap, symbol, exchange);
    }

    @Override
    public List<TradeRuntimeBootstrap> listBootstrapConfigs() {
        return selectBootstrapConfigsInternal(null, null, true);
    }

    @Override
    public int saveCurrentConfig(TradeRuntimeConfig tradeRuntimeConfig) {
        TradeRuntimeConfig currentConfig = tradeRuntimeConfigMapper.selectCurrentConfig();
        if (tradeRuntimeConfig.getDefaultMode() == null) {
            tradeRuntimeConfig.setDefaultMode(TradeRuntimeMode.PAPER);
        }
        if (tradeRuntimeConfig.getLiveEnabled() == null) {
            tradeRuntimeConfig.setLiveEnabled(Boolean.FALSE);
        }
        applyRuntimeDefaults(tradeRuntimeConfig);
        if (currentConfig == null) {
            return tradeRuntimeConfigMapper.insertTradeRuntimeConfig(tradeRuntimeConfig);
        }
        tradeRuntimeConfig.setId(currentConfig.getId());
        return tradeRuntimeConfigMapper.updateTradeRuntimeConfig(tradeRuntimeConfig);
    }

    private TradeSymbolScope selectPreferredScope(Long strategyId, String preferredSymbol, String preferredExchange) {
        List<TradeSymbolScope> scopes = tradeStrategyMapper.selectTradeSymbolScopes(strategyId);
        if (scopes == null || scopes.isEmpty()) {
            return null;
        }
        for (TradeSymbolScope scope : scopes) {
            if (scopeMatches(scope, preferredSymbol, preferredExchange)) {
                return scope;
            }
        }
        return isBlank(preferredSymbol) && isBlank(preferredExchange) ? scopes.get(0) : null;
    }

    private List<TradeRuntimeBootstrap> selectBootstrapConfigsInternal(String symbol, String exchange, boolean includeAllScopes) {
        TradeRuntimeConfig runtimeConfig = getCurrentConfig();
        AiModelConfig aiModelConfig = sanitizeAiModelConfig(aiModelConfigService.getDefaultModel());
        MarketApiConfig newsApiConfig = sanitizeMarketApiConfig(selectFirstEnabledApi(NEWS_CATEGORY));
        MarketApiConfig onchainApiConfig = sanitizeMarketApiConfig(selectFirstEnabledApi(ONCHAIN_CATEGORY));
        MarketApiConfig socialApiConfig = sanitizeMarketApiConfig(selectFirstEnabledApi(SOCIAL_CATEGORY));
        TradeStrategy query = new TradeStrategy();
        query.setEnabled(Boolean.TRUE);
        List<TradeStrategy> strategies = tradeStrategyMapper.selectTradeStrategyList(query);
        if (strategies == null || strategies.isEmpty()) {
            return java.util.List.of();
        }

        List<TradeRuntimeBootstrap> bootstraps = new java.util.ArrayList<>();
        for (TradeStrategy strategy : strategies) {
            List<TradeSymbolScope> scopes = tradeStrategyMapper.selectTradeSymbolScopes(strategy.getId());
            if (scopes == null || scopes.isEmpty()) {
                continue;
            }
            TradeStrategyVersion version = tradeStrategyMapper.selectLatestTradeStrategyVersion(strategy.getId());
            if (includeAllScopes) {
                for (TradeSymbolScope scope : scopes) {
                    bootstraps.add(buildBootstrap(runtimeConfig, strategy, version, scope, aiModelConfig, newsApiConfig, onchainApiConfig, socialApiConfig));
                }
                continue;
            }
            TradeSymbolScope scope = selectPreferredScope(strategy.getId(), symbol, exchange);
            if (scope != null) {
                bootstraps.add(buildBootstrap(runtimeConfig, strategy, version, scope, aiModelConfig, newsApiConfig, onchainApiConfig, socialApiConfig));
            }
        }
        return bootstraps;
    }

    private TradeRuntimeBootstrap buildBootstrap(
        TradeRuntimeConfig runtimeConfig,
        TradeStrategy strategy,
        TradeStrategyVersion strategyVersion,
        TradeSymbolScope scope,
        AiModelConfig defaultAiModelConfig,
        MarketApiConfig defaultNewsApiConfig,
        MarketApiConfig defaultOnchainApiConfig,
        MarketApiConfig defaultSocialApiConfig
    ) {
        Map<String, Object> strategyConfig = parseStrategyConfig(strategyVersion);
        TradeRuntimeBootstrap bootstrap = new TradeRuntimeBootstrap();
        bootstrap.setUserId(resolveCurrentUserId());
        bootstrap.setRuntimeConfig(resolveRuntimeConfig(runtimeConfig, strategy, strategyConfig));
        bootstrap.setStrategy(strategy);
        bootstrap.setStrategyVersion(strategyVersion);
        bootstrap.setSymbolScope(scope);
        bootstrap.setAiModelConfig(resolveAiModelConfig(strategyConfig, defaultAiModelConfig));
        bootstrap.setNewsApiConfig(resolveMarketApiConfig(strategyConfig, defaultNewsApiConfig, NEWS_CATEGORY, "newsApiConfigId", "news_api_config_id"));
        bootstrap.setOnchainApiConfig(resolveMarketApiConfig(strategyConfig, defaultOnchainApiConfig, ONCHAIN_CATEGORY, "onchainApiConfigId", "onchain_api_config_id"));
        bootstrap.setSocialApiConfig(resolveMarketApiConfig(strategyConfig, defaultSocialApiConfig, SOCIAL_CATEGORY, "socialApiConfigId", "social_api_config_id"));
        bootstrap.setMarketApiConfig(resolveMarketSourceConfig(strategy.getId(), scope, bootstrap.getRuntimeConfig(), strategyConfig));
        bootstrap.setMarketDataConfig(resolveMarketDataConfig(scope.getSymbol(), strategyConfig));
        bootstrap.setRuntimeAccountContext(buildRuntimeAccountContext(scope, bootstrap.getRuntimeConfig()));
        bootstrap.setPositionGuard(resolvePositionGuard(strategy == null ? null : strategy.getId(), scope));
        ExchangeAccountBinding binding = selectPreferredBinding(strategy.getId(), scope.getExchangeCode(), bootstrap.getRuntimeConfig());
        if (binding != null) {
            bootstrap.setExchangeAccountBinding(binding);
            bootstrap.setExchangeAccount(exchangeAccountMapper.selectExchangeAccountById(binding.getAccountId()));
        }
        List<TradePromptBinding> promptBindings = resolvePromptBindings(strategy, strategyVersion, scope, bootstrap.getRuntimeConfig());
        List<TradeAgentProfile> agentProfiles = resolveAgentProfiles();
        List<TradePromptBinding> filteredPromptBindings = filterPromptBindingsWithResolvedProfiles(promptBindings, agentProfiles);
        bootstrap.setAgentProfiles(agentProfiles);
        bootstrap.setPromptBindings(filteredPromptBindings);
        bootstrap.setResolvedAgentConfigs(resolveAgentConfigs(agentProfiles, filteredPromptBindings));
        bootstrap.setDeliberationPolicy(buildDeliberationPolicy(bootstrap.getRuntimeConfig()));
        return bootstrap;
    }

    private ExchangeAccountBinding selectPreferredBinding(Long strategyId, String exchangeCode, TradeRuntimeConfig runtimeConfig) {
        List<ExchangeAccountBinding> bindings = tradeStrategyMapper.selectExchangeAccountBindings(strategyId);
        if (bindings == null || bindings.isEmpty()) {
            return null;
        }
        for (ExchangeAccountBinding binding : bindings) {
            if (!isEnabled(binding.getEnabled())) {
                continue;
            }
            if (!isBlank(exchangeCode) && !equalsIgnoreCase(exchangeCode, binding.getExchangeCode())) {
                continue;
            }
            ExchangeAccount account = exchangeAccountMapper.selectExchangeAccountById(binding.getAccountId());
            if (account != null && isEnabled(account.getEnabled()) && isAccountAllowedForRuntime(account, runtimeConfig)) {
                return binding;
            }
        }
        return null;
    }

    private boolean isAccountAllowedForRuntime(ExchangeAccount account, TradeRuntimeConfig runtimeConfig) {
        if (account == null) {
            return false;
        }
        if (!isEnabled(account.getEnabled())) {
            return false;
        }
        if (runtimeConfig == null) {
            return true;
        }
        boolean requiresHealthyAccount = Boolean.TRUE.equals(runtimeConfig.getLiveOrderRequiresHealthyAccount());
        boolean liveMode = TradeRuntimeMode.LIVE.equals(runtimeConfig.getDefaultMode()) && Boolean.TRUE.equals(runtimeConfig.getLiveEnabled());
        if (!requiresHealthyAccount || !liveMode) {
            return true;
        }
        return !isBlank(account.getHealthStatus())
            && "healthy".equalsIgnoreCase(account.getHealthStatus().trim())
            && account.getLastValidatedAt() != null;
    }

    private boolean scopeMatches(TradeSymbolScope scope, String preferredSymbol, String preferredExchange) {
        if (!isBlank(preferredSymbol) && !equalsIgnoreCase(preferredSymbol, scope.getSymbol())) {
            return false;
        }
        if (!isBlank(preferredExchange) && !equalsIgnoreCase(preferredExchange, scope.getExchangeCode())) {
            return false;
        }
        return true;
    }

    private boolean equalsIgnoreCase(String left, String right) {
        return left != null && right != null && left.trim().equalsIgnoreCase(right.trim());
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private TradeRuntimeConfig resolveRuntimeConfig(TradeRuntimeConfig source, TradeStrategy strategy, Map<String, Object> strategyConfig) {
        TradeRuntimeConfig resolved = new TradeRuntimeConfig();
        if (source != null) {
            resolved.setId(source.getId());
            resolved.setLiveEnabled(source.getLiveEnabled());
            resolved.setDefaultMode(source.getDefaultMode());
            resolved.setMaxPositionRatio(source.getMaxPositionRatio());
            resolved.setMaxDailyLoss(source.getMaxDailyLoss());
            resolved.setMaxConsecutiveFailures(source.getMaxConsecutiveFailures());
            resolved.setAllowedSymbolsJson(source.getAllowedSymbolsJson());
            resolved.setAllowedExchangesJson(source.getAllowedExchangesJson());
            resolved.setRequireAccountBinding(source.getRequireAccountBinding());
            resolved.setLiveOrderRequiresHealthyAccount(source.getLiveOrderRequiresHealthyAccount());
            resolved.setRuntimeFlagsJson(source.getRuntimeFlagsJson());
            resolved.setNotifyDefaultsJson(source.getNotifyDefaultsJson());
            resolved.setEventRetentionDays(source.getEventRetentionDays());
            resolved.setReplayRetentionDays(source.getReplayRetentionDays());
            resolved.setDeliberationEnabled(source.getDeliberationEnabled());
            resolved.setDeliberationMaxRounds(source.getDeliberationMaxRounds());
            resolved.setDeliberationFailOpen(source.getDeliberationFailOpen());
            resolved.setRouteMaxConcurrency(source.getRouteMaxConcurrency());
            resolved.setRouteSchedulerMode(source.getRouteSchedulerMode());
        }
        // 注意：不在此处调用 applyRuntimeDefaults，因为 source 已经是经过默认值处理的
        // 只有当 source 为 null 时才需要应用默认值
        if (source == null) {
            applyRuntimeDefaults(resolved);
        }
        if (strategy != null && strategy.getRuntimeMode() != null) {
            resolved.setDefaultMode(strategy.getRuntimeMode());
        }
        BigDecimal maxPositionRatio = resolveBigDecimal(strategyConfig, "maxPositionRatio", "max_position_ratio");
        if (maxPositionRatio != null && resolved.getMaxPositionRatio() == null) {
            resolved.setMaxPositionRatio(maxPositionRatio);
        }
        BigDecimal maxDailyLoss = resolveBigDecimal(strategyConfig, "maxDailyLoss", "max_daily_loss");
        if (maxDailyLoss != null && resolved.getMaxDailyLoss() == null) {
            resolved.setMaxDailyLoss(maxDailyLoss);
        }
        Integer maxConsecutiveFailures = resolveInteger(strategyConfig, "maxConsecutiveFailures", "max_consecutive_failures");
        if (maxConsecutiveFailures != null && resolved.getMaxConsecutiveFailures() == null) {
            resolved.setMaxConsecutiveFailures(maxConsecutiveFailures);
        }
        return resolved;
    }

    private TradeRuntimeConfig applyRuntimeDefaults(TradeRuntimeConfig config) {
        if (config.getMaxPositionRatio() == null) {
            config.setMaxPositionRatio(DEFAULT_MAX_POSITION_RATIO);
        }
        if (config.getMaxDailyLoss() == null) {
            config.setMaxDailyLoss(DEFAULT_MAX_DAILY_LOSS);
        }
        if (config.getMaxConsecutiveFailures() == null) {
            config.setMaxConsecutiveFailures(DEFAULT_MAX_CONSECUTIVE_FAILURES);
        }
        if (config.getRequireAccountBinding() == null) {
            config.setRequireAccountBinding(Boolean.TRUE);
        }
        if (config.getLiveOrderRequiresHealthyAccount() == null) {
            config.setLiveOrderRequiresHealthyAccount(Boolean.TRUE);
        }
        if (config.getEventRetentionDays() == null || config.getEventRetentionDays() < 1) {
            config.setEventRetentionDays(DEFAULT_RETENTION_DAYS);
        }
        if (config.getReplayRetentionDays() == null || config.getReplayRetentionDays() < 1) {
            config.setReplayRetentionDays(DEFAULT_RETENTION_DAYS);
        }
        if (config.getDeliberationEnabled() == null) {
            config.setDeliberationEnabled(Boolean.FALSE);
        }
        if (config.getDeliberationMaxRounds() == null || config.getDeliberationMaxRounds() < 0) {
            config.setDeliberationMaxRounds(DEFAULT_DELIBERATION_MAX_ROUNDS);
        }
        if (config.getDeliberationFailOpen() == null) {
            config.setDeliberationFailOpen(Boolean.TRUE);
        }
        if (config.getRouteMaxConcurrency() == null || config.getRouteMaxConcurrency() < 1) {
            config.setRouteMaxConcurrency(DEFAULT_ROUTE_MAX_CONCURRENCY);
        }
        config.setRouteSchedulerMode(normalizeRouteSchedulerMode(config.getRouteSchedulerMode()));
        config.setAllowedSymbolsJson(normalizeArrayJson(config.getAllowedSymbolsJson(), resolveSymbolUniverse(config), "allowedSymbolsJson"));
        config.setAllowedExchangesJson(normalizeArrayJson(config.getAllowedExchangesJson(), TradeConstants.V1_ALLOWED_EXCHANGES, "allowedExchangesJson"));
        config.setRuntimeFlagsJson(normalizeRuntimeFlagsJson(config.getRuntimeFlagsJson()));
        config.setNotifyDefaultsJson(normalizeObjectJson(config.getNotifyDefaultsJson(), "notifyDefaultsJson"));
        return config;
    }

    private TradeRuntimeBootstrap applyControlPlaneConfigs(TradeRuntimeBootstrap bootstrap, String symbol, String exchange) {
        TradeSymbolScope fallbackScope = buildFallbackScope(symbol, exchange, bootstrap.getRuntimeConfig());
        bootstrap.setAiModelConfig(sanitizeAiModelConfig(aiModelConfigService.getDefaultModel()));
        bootstrap.setNewsApiConfig(sanitizeMarketApiConfig(selectFirstEnabledApi(NEWS_CATEGORY)));
        bootstrap.setOnchainApiConfig(sanitizeMarketApiConfig(selectFirstEnabledApi(ONCHAIN_CATEGORY)));
        bootstrap.setSocialApiConfig(sanitizeMarketApiConfig(selectFirstEnabledApi(SOCIAL_CATEGORY)));
        bootstrap.setMarketApiConfig(sanitizeMarketApiConfig(selectFirstEnabledApi(PRICE_CATEGORY)));
        bootstrap.setMarketDataConfig(sanitizeMarketDataConfig(selectMarketDataConfig(fallbackScope == null ? null : fallbackScope.getSymbol())));
        bootstrap.setRuntimeAccountContext(buildRuntimeAccountContext(fallbackScope, bootstrap.getRuntimeConfig()));
        bootstrap.setPositionGuard(resolvePositionGuard(null, fallbackScope));
        List<TradePromptBinding> promptBindings = resolvePromptBindings(null, null, fallbackScope, bootstrap.getRuntimeConfig());
        List<TradeAgentProfile> agentProfiles = resolveAgentProfiles();
        List<TradePromptBinding> filteredPromptBindings = filterPromptBindingsWithResolvedProfiles(promptBindings, agentProfiles);
        bootstrap.setAgentProfiles(agentProfiles);
        bootstrap.setPromptBindings(filteredPromptBindings);
        bootstrap.setResolvedAgentConfigs(resolveAgentConfigs(agentProfiles, filteredPromptBindings));
        bootstrap.setDeliberationPolicy(buildDeliberationPolicy(bootstrap.getRuntimeConfig()));
        return bootstrap;
    }

    private Map<String, Object> buildDeliberationPolicy(TradeRuntimeConfig runtimeConfig) {
        Map<String, Object> payload = new LinkedHashMap<>();
        if (runtimeConfig == null) {
            return payload;
        }
        payload.put("enabled", Boolean.TRUE.equals(runtimeConfig.getDeliberationEnabled()));
        payload.put("maxRounds", runtimeConfig.getDeliberationMaxRounds() == null ? DEFAULT_DELIBERATION_MAX_ROUNDS : runtimeConfig.getDeliberationMaxRounds());
        payload.put("failOpen", runtimeConfig.getDeliberationFailOpen() == null || Boolean.TRUE.equals(runtimeConfig.getDeliberationFailOpen()));
        return payload;
    }

    private TradeSymbolScope buildFallbackScope(String symbol, String exchange, TradeRuntimeConfig runtimeConfig) {
        String sanitizedSymbol = sanitizeRequestedSymbol(symbol, runtimeConfig);
        String sanitizedExchange = sanitizeRequestedExchange(exchange, runtimeConfig);
        if (isBlank(sanitizedSymbol) && isBlank(sanitizedExchange)) {
            return null;
        }
        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setSymbol(sanitizedSymbol);
        scope.setExchangeCode(sanitizedExchange);
        return scope;
    }

    private String sanitizeRequestedSymbol(String symbol, TradeRuntimeConfig runtimeConfig) {
        return sanitizeRequestedScopeValue(symbol, runtimeConfig == null ? null : runtimeConfig.getAllowedSymbolsJson(), TradeConstants.V1_ALLOWED_SYMBOLS, true);
    }

    private String sanitizeRequestedExchange(String exchange, TradeRuntimeConfig runtimeConfig) {
        String sanitized = sanitizeRequestedScopeValue(
            exchange,
            runtimeConfig == null ? null : runtimeConfig.getAllowedExchangesJson(),
            TradeConstants.V1_ALLOWED_EXCHANGES,
            false
        );
        return sanitized == null ? null : sanitized.toLowerCase(Locale.ROOT);
    }

    private String sanitizeRequestedScopeValue(String value, String allowedJson, List<String> fallbackAllowedValues, boolean uppercaseResult) {
        if (isBlank(value)) {
            return null;
        }
        String normalized = value.trim().toUpperCase(Locale.ROOT);
        List<String> allowedValues = parseJsonArray(allowedJson);
        if (allowedValues.isEmpty()) {
            allowedValues = fallbackAllowedValues;
        }
        for (String allowedValue : allowedValues) {
            if (normalized.equals(String.valueOf(allowedValue).trim().toUpperCase(Locale.ROOT))) {
                return uppercaseResult ? normalized : value.trim();
            }
        }
        return null;
    }

    private MarketApiConfig selectFirstEnabledApi(String category) {
        List<MarketApiConfig> configs = marketApiConfigService.selectEnabledApis(category);
        return configs == null || configs.isEmpty() ? null : configs.get(0);
    }

    private AiModelConfig resolveAiModelConfig(Map<String, Object> strategyConfig, AiModelConfig fallback) {
        Long configId = resolveLong(strategyConfig, "aiModelId", "modelId", "ai_model_id", "model_id");
        if (configId == null) {
            return fallback;
        }
        AiModelConfig config = aiModelConfigService.selectAiModelConfigById(configId);
        if (config == null || !Integer.valueOf(1).equals(config.getIsEnabled())) {
            return fallback;
        }
        return sanitizeAiModelConfig(config);
    }

    private MarketApiConfig resolveMarketApiConfig(
        Map<String, Object> strategyConfig,
        MarketApiConfig fallback,
        String category,
        String... keys
    ) {
        Long configId = resolveLong(strategyConfig, keys);
        if (configId == null) {
            return fallback;
        }
        MarketApiConfig config = marketApiConfigService.selectApiConfigById(configId);
        if (config == null || !matchesEnabledFlag(config.getEnabled()) || !category.equalsIgnoreCase(String.valueOf(config.getDataCategory()))) {
            return fallback;
        }
        return sanitizeMarketApiConfig(config);
    }

    private MarketApiConfig resolveMarketSourceConfig(
        Long strategyId,
        TradeSymbolScope scope,
        TradeRuntimeConfig runtimeConfig,
        Map<String, Object> strategyConfig
    ) {
        MarketApiConfig configured = resolveMarketApiConfig(strategyConfig, null, PRICE_CATEGORY, "marketApiConfigId", "market_api_config_id");
        if (configured != null) {
            return configured;
        }
        MarketApiConfig bound = selectMarketSourceConfigFromBindings(strategyId, scope, runtimeConfig);
        if (bound != null) {
            return bound;
        }
        return sanitizeMarketApiConfig(selectFirstEnabledApi(PRICE_CATEGORY));
    }

    private MarketApiConfig selectMarketSourceConfigFromBindings(
        Long strategyId,
        TradeSymbolScope scope,
        TradeRuntimeConfig runtimeConfig
    ) {
        TradeDataSourceBinding query = new TradeDataSourceBinding();
        query.setEnabled(Boolean.TRUE);
        List<TradeDataSourceBinding> bindings = tradeDataSourceBindingMapper.selectTradeDataSourceBindingList(query);
        if (bindings == null || bindings.isEmpty()) {
            return null;
        }
        MarketApiConfig globalMatch = null;
        String symbol = scope == null ? null : scope.getSymbol();
        String exchangeCode = scope == null ? null : scope.getExchangeCode();
        String runtimeMode = resolveEffectiveRuntimeMode(runtimeConfig);
        for (TradeDataSourceBinding binding : bindings) {
            if (!isEnabled(binding.getEnabled())) {
                continue;
            }
            if (!MARKET_TICK_EVENT.equalsIgnoreCase(String.valueOf(binding.getEventType()))) {
                continue;
            }
            if (binding.getStrategyId() != null && !binding.getStrategyId().equals(strategyId)) {
                continue;
            }
            if (!matchesScopeJson(binding.getSymbolScopeJson(), normalizeUpper(symbol))) {
                continue;
            }
            if (!matchesScopeJson(binding.getExchangeScopeJson(), normalizeUpper(exchangeCode))) {
                continue;
            }
            if (!matchesScopeJson(binding.getModeScopeJson(), runtimeMode)) {
                continue;
            }
            MarketApiConfig sourceConfig = marketApiConfigService.selectApiConfigById(binding.getSourceId());
            if (sourceConfig == null || !matchesEnabledFlag(sourceConfig.getEnabled())) {
                continue;
            }
            MarketApiConfig sanitized = sanitizeMarketApiConfig(sourceConfig);
            if (binding.getStrategyId() != null) {
                return sanitized;
            }
            if (globalMatch == null) {
                globalMatch = sanitized;
            }
        }
        return globalMatch;
    }

    private List<TradePromptBinding> resolvePromptBindings(
        TradeStrategy strategy,
        TradeStrategyVersion strategyVersion,
        TradeSymbolScope scope,
        TradeRuntimeConfig runtimeConfig
    ) {
        TradePromptBinding query = new TradePromptBinding();
        query.setEnabled(Boolean.TRUE);
        List<TradePromptBinding> bindings = tradePromptBindingMapper.selectTradePromptBindingList(query);
        if (bindings == null || bindings.isEmpty()) {
            return List.of();
        }
        Long strategyId = strategy == null ? null : strategy.getId();
        Long strategyVersionId = strategyVersion == null ? null : strategyVersion.getId();
        String symbol = scope == null ? null : scope.getSymbol();
        String exchangeCode = scope == null ? null : scope.getExchangeCode();
        String runtimeMode = resolveEffectiveRuntimeMode(runtimeConfig);
        List<TradePromptBinding> matched = new ArrayList<>();
        for (TradePromptBinding binding : bindings) {
            if (!matchesPromptBinding(binding, strategyId, symbol, exchangeCode, runtimeMode)) {
                continue;
            }
            matched.add(binding);
        }
        return filterPromptBindingsByStrategyVersion(matched, strategyVersionId);
    }

    private boolean matchesPromptBinding(
        TradePromptBinding binding,
        Long strategyId,
        String symbol,
        String exchangeCode,
        String runtimeMode
    ) {
        if (binding == null || !isEnabled(binding.getEnabled())) {
            return false;
        }
        if (binding.getStrategyId() != null && !binding.getStrategyId().equals(strategyId)) {
            return false;
        }
        if (!isBlank(binding.getSymbol()) && !equalsIgnoreCase(binding.getSymbol(), symbol)) {
            return false;
        }
        if (!isBlank(binding.getExchangeCode()) && !equalsIgnoreCase(binding.getExchangeCode(), exchangeCode)) {
            return false;
        }
        return matchesScopeJson(binding.getModeScopeJson(), runtimeMode);
    }

    private List<TradePromptBinding> filterPromptBindingsByStrategyVersion(
        List<TradePromptBinding> promptBindings,
        Long strategyVersionId
    ) {
        if (promptBindings == null || promptBindings.isEmpty() || strategyVersionId == null) {
            return promptBindings == null ? List.of() : promptBindings;
        }
        Map<String, Boolean> scopeHasExactVersionBinding = new LinkedHashMap<>();
        Map<String, Boolean> scopeHasVersionAgnosticBinding = new LinkedHashMap<>();
        for (TradePromptBinding binding : promptBindings) {
            String scopeKey = isBlank(binding == null ? null : binding.getBindingScope())
                ? ""
                : binding.getBindingScope().trim().toUpperCase(Locale.ROOT);
            if (binding != null && strategyVersionId.equals(binding.getStrategyVersionId())) {
                scopeHasExactVersionBinding.put(scopeKey, Boolean.TRUE);
            }
            if (binding != null && binding.getStrategyVersionId() == null) {
                scopeHasVersionAgnosticBinding.put(scopeKey, Boolean.TRUE);
            }
        }

        List<TradePromptBinding> filtered = new ArrayList<>();
        for (TradePromptBinding binding : promptBindings) {
            if (binding == null) {
                continue;
            }
            String scopeKey = isBlank(binding.getBindingScope()) ? "" : binding.getBindingScope().trim().toUpperCase(Locale.ROOT);
            boolean hasExactVersionBinding = Boolean.TRUE.equals(scopeHasExactVersionBinding.get(scopeKey));
            boolean hasVersionAgnosticBinding = Boolean.TRUE.equals(scopeHasVersionAgnosticBinding.get(scopeKey));
            Long bindingStrategyVersionId = binding.getStrategyVersionId();
            if (bindingStrategyVersionId == null || strategyVersionId.equals(bindingStrategyVersionId)) {
                filtered.add(binding);
                continue;
            }
            if (!hasExactVersionBinding && !hasVersionAgnosticBinding) {
                filtered.add(binding);
            }
        }
        return filtered;
    }

    private List<TradeAgentProfile> resolveAgentProfiles() {
        TradeAgentProfile query = new TradeAgentProfile();
        query.setEnabled(Boolean.TRUE);
        List<TradeAgentProfile> profiles = tradeAgentProfileMapper.selectTradeAgentProfileList(query);
        if (profiles == null || profiles.isEmpty()) {
            return List.of();
        }
        List<TradeAgentProfile> matched = new ArrayList<>();
        for (TradeAgentProfile profile : profiles) {
            if (!isEnabled(profile.getEnabled())) {
                continue;
            }
            if (isBlank(profile.getAgentCode())) {
                continue;
            }
            matched.add(profile);
        }
        matched.sort(
            Comparator.comparing(TradeAgentProfile::getSpeakOrder, Comparator.nullsLast(Integer::compareTo))
                .thenComparing(TradeAgentProfile::getId, Comparator.nullsLast(Long::compareTo))
        );
        return matched;
    }

    private List<TradePromptBinding> filterPromptBindingsWithResolvedProfiles(
        List<TradePromptBinding> promptBindings,
        List<TradeAgentProfile> agentProfiles
    ) {
        if (promptBindings == null || promptBindings.isEmpty()) {
            return List.of();
        }
        Set<String> availableAgentCodes = new LinkedHashSet<>();
        for (TradeAgentProfile profile : agentProfiles) {
            if (profile != null && !isBlank(profile.getAgentCode())) {
                availableAgentCodes.add(profile.getAgentCode().trim().toLowerCase(Locale.ROOT));
            }
        }
        List<TradePromptBinding> filtered = new ArrayList<>();
        for (TradePromptBinding binding : promptBindings) {
            if (shouldKeepPromptBindingWithoutProfile(binding)) {
                filtered.add(binding);
                continue;
            }
            String agentCode = resolveAgentCode(binding.getBindingScope());
            if (isBlank(agentCode) || availableAgentCodes.contains(agentCode)) {
                filtered.add(binding);
            }
        }
        return filtered;
    }

    private List<ResolvedAgentConfig> resolveAgentConfigs(
        List<TradeAgentProfile> agentProfiles,
        List<TradePromptBinding> promptBindings
    ) {
        if (agentProfiles == null || agentProfiles.isEmpty()) {
            return List.of();
        }
        List<ResolvedAgentConfig> resolved = new ArrayList<>();
        for (TradeAgentProfile profile : agentProfiles) {
            if (profile == null || !isEnabled(profile.getEnabled()) || isBlank(profile.getAgentCode())) {
                continue;
            }
            ResolvedAgentConfig config = new ResolvedAgentConfig();
            config.setAgentCode(profile.getAgentCode().trim().toLowerCase(Locale.ROOT));
            config.setAgentType(profile.getAgentType());
            config.setEnabled(profile.getEnabled());
            config.setLlmEnabled(profile.getLlmEnabled());
            config.setModelId(profile.getDefaultModelId());
            config.setTemplateCode(trimToNull(profile.getDefaultTemplateCode()));
            config.setFallbackTemplateCode(trimToNull(profile.getDefaultFallbackTemplateCode()));
            config.setOutputSchemaCode(trimToNull(profile.getDefaultOutputSchemaCode()));
            config.setSourceProfileId(profile.getId());
            config.setResolutionSource("PROFILE_DEFAULT");

            TradePromptBinding override = findPromptBindingOverride(config.getAgentCode(), promptBindings);
            if (override != null) {
                if (override.getModelId() != null) {
                    config.setModelId(override.getModelId());
                }
                if (!isBlank(override.getTemplateCode())) {
                    config.setTemplateCode(override.getTemplateCode().trim());
                }
                if (!isBlank(override.getFallbackTemplateCode())) {
                    config.setFallbackTemplateCode(override.getFallbackTemplateCode().trim());
                }
                if (!isBlank(override.getOutputSchemaCode())) {
                    config.setOutputSchemaCode(override.getOutputSchemaCode().trim());
                }
                config.setSourceBindingId(override.getId());
                config.setResolutionSource("BINDING_OVERRIDE");
            }
            attachResolvedModel(config);
            resolved.add(config);
        }
        return resolved;
    }

    private TradePromptBinding findPromptBindingOverride(String agentCode, List<TradePromptBinding> promptBindings) {
        if (isBlank(agentCode) || promptBindings == null || promptBindings.isEmpty()) {
            return null;
        }
        TradePromptBinding best = null;
        for (TradePromptBinding binding : promptBindings) {
            if (binding == null || !isEnabled(binding.getEnabled())) {
                continue;
            }
            String bindingAgentCode = resolveAgentCode(binding.getBindingScope());
            if (!agentCode.equals(bindingAgentCode)) {
                continue;
            }
            if (best == null || comparePromptBindingPriority(binding, best) < 0) {
                best = binding;
            }
        }
        return best;
    }

    private int comparePromptBindingPriority(TradePromptBinding left, TradePromptBinding right) {
        int leftScore = promptBindingSpecificity(left);
        int rightScore = promptBindingSpecificity(right);
        if (leftScore != rightScore) {
            return Integer.compare(rightScore, leftScore);
        }
        int leftPriority = left.getPriority() == null ? 0 : left.getPriority();
        int rightPriority = right.getPriority() == null ? 0 : right.getPriority();
        if (leftPriority != rightPriority) {
            return Integer.compare(leftPriority, rightPriority);
        }
        Long leftId = left.getId() == null ? Long.MAX_VALUE : left.getId();
        Long rightId = right.getId() == null ? Long.MAX_VALUE : right.getId();
        return leftId.compareTo(rightId);
    }

    private int promptBindingSpecificity(TradePromptBinding binding) {
        if (binding == null) {
            return 0;
        }
        int score = 0;
        if (binding.getStrategyVersionId() != null) {
            score += 100;
        } else if (binding.getStrategyId() != null) {
            score += 50;
        }
        if (!isBlank(binding.getSymbol())) {
            score += 10;
        }
        if (!isBlank(binding.getExchangeCode())) {
            score += 5;
        }
        if (!isBlank(binding.getModeScopeJson())) {
            score += 1;
        }
        if (!isBlank(binding.getEventStrengthScopeJson())) {
            score += 1;
        }
        return score;
    }

    private void attachResolvedModel(ResolvedAgentConfig config) {
        if (config == null || config.getModelId() == null) {
            return;
        }
        AiModelConfig modelConfig = aiModelConfigService.selectAiModelConfigById(config.getModelId());
        if (modelConfig == null || !Integer.valueOf(1).equals(modelConfig.getIsEnabled())) {
            return;
        }
        config.setModelCode(modelConfig.getModelCode());
        config.setModelProvider(modelConfig.getProvider());
    }

    private String trimToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private boolean shouldKeepPromptBindingWithoutProfile(TradePromptBinding binding) {
        if (binding == null || isBlank(binding.getBindingScope())) {
            return false;
        }
        return ALWAYS_INCLUDED_PROMPT_BINDING_SCOPES.contains(binding.getBindingScope().trim().toUpperCase(Locale.ROOT));
    }

    private String resolveAgentCode(String bindingScope) {
        if (isBlank(bindingScope)) {
            return null;
        }
        return BINDING_SCOPE_AGENT_CODE_MAP.get(bindingScope.trim().toUpperCase(Locale.ROOT));
    }

    private MarketDataConfig resolveMarketDataConfig(String symbol, Map<String, Object> strategyConfig) {
        Long configId = resolveLong(strategyConfig, "marketDataConfigId", "market_data_config_id");
        if (configId != null) {
            MarketDataConfig config = marketDataConfigService.selectConfigById(configId);
            if (config != null && matchesEnabledFlag(config.getEnabled())) {
                return sanitizeMarketDataConfig(config);
            }
        }
        return sanitizeMarketDataConfig(selectMarketDataConfig(symbol));
    }

    private MarketDataConfig selectMarketDataConfig(String symbol) {
        if (!isBlank(symbol)) {
            MarketDataConfig config = marketDataConfigService.selectConfigBySymbol(symbol.trim());
            if (config != null) {
                return config;
            }
        }
        List<MarketDataConfig> configs = marketDataConfigService.selectEnabledConfigs();
        return configs == null || configs.isEmpty() ? null : configs.get(0);
    }

    private TradeRuntimeAccountContext buildRuntimeAccountContext(TradeSymbolScope scope, TradeRuntimeConfig runtimeConfig) {
        TradeRuntimeAccountContext context = new TradeRuntimeAccountContext();
        LocalDateTime currentTime = TradeRuntimeTimeUtils.nowDatabaseLocalDateTime();
        context.setAccountEquity(DEFAULT_ACCOUNT_EQUITY);
        context.setDailyPnl(ZERO_DECIMAL);
        context.setRealizedPnl(ZERO_DECIMAL);
        context.setUnrealizedPnl(ZERO_DECIMAL);
        context.setCurrentPositionSide("flat");
        context.setCurrentPositionQuantity(ZERO_DECIMAL);
        context.setCurrentPositionNotional(ZERO_DECIMAL);
        context.setEntryPrice(ZERO_DECIMAL);
        context.setMaxDrawdownPct(ZERO_DECIMAL);
        context.setPeakAccountEquity(ZERO_DECIMAL);
        context.setCurrentPositionOpenedAt(null);
        context.setCurrentTime(TradeRuntimeTimeUtils.formatSqlDateTime(currentTime));
        context.setCurrentPositionHoldingMinutes(null);
        context.setConsecutiveFailures(0);

        String runtimeMode = resolveEffectiveRuntimeMode(runtimeConfig);
        PnlSnapshot pnlSnapshot = tradeExecutionMapper.selectLatestPnlSnapshotByMode(runtimeMode);
        if (pnlSnapshot == null) {
            pnlSnapshot = tradeExecutionMapper.selectLatestPnlSnapshot();
        }
        if (pnlSnapshot != null) {
            boolean preserveDailyPnl = shouldPreserveDailyPnlForCurrentUtcDay(pnlSnapshot.getCreatedAt());
            if (pnlSnapshot.getAccountEquity() != null) {
                context.setAccountEquity(pnlSnapshot.getAccountEquity());
            }
            if (pnlSnapshot.getDailyPnl() != null && preserveDailyPnl) {
                context.setDailyPnl(pnlSnapshot.getDailyPnl());
            }
            if (pnlSnapshot.getRealizedPnl() != null) {
                context.setRealizedPnl(pnlSnapshot.getRealizedPnl());
            }
            if (pnlSnapshot.getUnrealizedPnl() != null) {
                context.setUnrealizedPnl(pnlSnapshot.getUnrealizedPnl());
            }
            if (pnlSnapshot.getMaxDrawdownPct() != null) {
                context.setMaxDrawdownPct(pnlSnapshot.getMaxDrawdownPct());
            }
            if (pnlSnapshot.getPeakAccountEquity() != null) {
                context.setPeakAccountEquity(pnlSnapshot.getPeakAccountEquity());
            }
        }

        if (scope == null || isBlank(scope.getExchangeCode()) || isBlank(scope.getSymbol())) {
            return context;
        }

        PositionSnapshot positionSnapshot = tradeExecutionMapper.selectLatestActivePositionSnapshotByScope(
            scope.getExchangeCode(),
            scope.getSymbol()
        );
        if (positionSnapshot != null) {
            BigDecimal positionQuantity = positionSnapshot.getPositionQuantity() == null ? ZERO_DECIMAL : positionSnapshot.getPositionQuantity();
            BigDecimal entryPrice = positionSnapshot.getEntryPrice() == null ? ZERO_DECIMAL : positionSnapshot.getEntryPrice();
            String positionSide = positionSnapshot.getSide() == null ? "flat" : positionSnapshot.getSide().trim().toLowerCase(Locale.ROOT);
            if (positionQuantity.compareTo(ZERO_DECIMAL) <= 0) {
                positionSide = "flat";
                entryPrice = ZERO_DECIMAL;
            }
            context.setCurrentPositionSide(positionSide);
            context.setCurrentPositionQuantity(positionQuantity);
            context.setCurrentPositionNotional(positionQuantity.multiply(entryPrice));
            context.setEntryPrice(entryPrice);
            if (positionSnapshot.getUnrealizedPnl() != null) {
                context.setUnrealizedPnl(positionSnapshot.getUnrealizedPnl());
            }
            // 设置entry_trace_id，用于平仓时关联开仓记录
            String entryTraceId = positionSnapshot.getEntryTraceId();
            if (isBlank(entryTraceId)) {
                entryTraceId = positionSnapshot.getTraceId();
            }
            if (!isBlank(entryTraceId) && !"flat".equals(positionSide)) {
                context.setEntryTraceId(entryTraceId);
            }
            if (positionQuantity.compareTo(ZERO_DECIMAL) > 0 && !"flat".equals(positionSide)) {
                String currentPositionOpenedAt = tradePositionGuardMapper.selectCurrentPositionOpenedAt(
                    scope.getExchangeCode(),
                    scope.getSymbol(),
                    positionSide
                );
                if (isBlank(currentPositionOpenedAt)) {
                    currentPositionOpenedAt = positionSnapshot.getCreatedAt();
                }
                if (!isBlank(currentPositionOpenedAt)) {
                    context.setCurrentPositionOpenedAt(currentPositionOpenedAt);
                    context.setCurrentPositionHoldingMinutes(calculateHoldingMinutes(currentPositionOpenedAt, currentTime));
                }
            }
        }

        List<ExchangeOrder> recentOrders = tradeExecutionMapper.selectRecentExchangeOrdersByScope(
            scope.getExchangeCode(),
            scope.getSymbol(),
            RECENT_FAILURE_WINDOW
        );
        context.setConsecutiveFailures(countConsecutiveFailures(recentOrders));
        return context;
    }

    private Integer calculateHoldingMinutes(String openedAt, LocalDateTime currentTime) {
        if (isBlank(openedAt) || currentTime == null) {
            return null;
        }
        try {
            LocalDateTime openedTime = TradeRuntimeTimeUtils.parseDatabaseDateTime(openedAt);
            if (openedTime == null) {
                return null;
            }
            long minutes = Duration.between(openedTime, currentTime).toMinutes();
            return Math.toIntExact(Math.max(minutes, 0));
        } catch (DateTimeParseException | ArithmeticException ignored) {
            return null;
        }
    }

    private TradePositionGuard resolvePositionGuard(Long strategyId, TradeSymbolScope scope) {
        if (scope == null || isBlank(scope.getSymbol()) || isBlank(scope.getExchangeCode())) {
            return null;
        }
        return tradePositionGuardMapper.selectEffectiveGuard(strategyId, scope.getSymbol(), scope.getExchangeCode());
    }

    private int countConsecutiveFailures(List<ExchangeOrder> recentOrders) {
        if (recentOrders == null || recentOrders.isEmpty()) {
            return 0;
        }
        int failures = 0;
        for (ExchangeOrder order : recentOrders) {
            if (!isFailedExecution(order)) {
                break;
            }
            failures++;
        }
        return failures;
    }

    private boolean shouldPreserveDailyPnlForCurrentUtcDay(String createdAt) {
        if (isBlank(createdAt)) {
            return true;
        }
        LocalDate snapshotUtcDate = resolveSnapshotUtcDate(createdAt);
        if (snapshotUtcDate == null) {
            return true;
        }
        return snapshotUtcDate.equals(LocalDate.now(ZoneOffset.UTC));
    }

    private LocalDate resolveSnapshotUtcDate(String createdAt) {
        String normalized = createdAt == null ? null : createdAt.trim();
        if (isBlank(normalized)) {
            return null;
        }
        try {
            return LocalDateTime.parse(normalized, TradeRuntimeTimeUtils.SQL_DATETIME_FORMATTER)
                .atZone(TradeRuntimeTimeUtils.DATABASE_ZONE)
                .withZoneSameInstant(ZoneOffset.UTC)
                .toLocalDate();
        } catch (DateTimeParseException ignored) {
            // Fall through to ISO-8601 parsers.
        }
        try {
            return OffsetDateTime.parse(normalized).withOffsetSameInstant(ZoneOffset.UTC).toLocalDate();
        } catch (DateTimeParseException ignored) {
            // Fall through to Instant parser.
        }
        try {
            return Instant.parse(normalized).atZone(ZoneOffset.UTC).toLocalDate();
        } catch (DateTimeParseException ignored) {
            return null;
        }
    }

    private boolean isFailedExecution(ExchangeOrder order) {
        if (order == null) {
            return false;
        }
        String executionStatus = order.getExecutionStatus();
        if (!isBlank(executionStatus)) {
            return "failed".equalsIgnoreCase(executionStatus) || "rejected".equalsIgnoreCase(executionStatus);
        }
        String status = order.getStatus();
        if (!isBlank(status)) {
            return "failed".equalsIgnoreCase(status) || "rejected".equalsIgnoreCase(status);
        }
        String orderStatus = order.getOrderStatus();
        return !isBlank(orderStatus) && "REJECTED".equalsIgnoreCase(orderStatus);
    }

    private Map<String, Object> parseStrategyConfig(TradeStrategyVersion strategyVersion) {
        if (strategyVersion == null || isBlank(strategyVersion.getConfigJson())) {
            return Map.of();
        }
        try {
            Map<String, Object> parsed = objectMapper.readValue(strategyVersion.getConfigJson(), new TypeReference<Map<String, Object>>() {});
            return parsed == null ? Map.of() : parsed;
        } catch (IOException e) {
            throw new IllegalStateException("Failed to parse trade strategy version config", e);
        }
    }

    private Long resolveLong(Map<String, Object> strategyConfig, String... keys) {
        Object rawValue = resolveConfigValue(strategyConfig, keys);
        if (rawValue == null) {
            return null;
        }
        if (rawValue instanceof Number number) {
            return number.longValue();
        }
        try {
            String normalized = String.valueOf(rawValue).trim();
            return normalized.isEmpty() ? null : Long.parseLong(normalized);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private Integer resolveInteger(Map<String, Object> strategyConfig, String... keys) {
        Object rawValue = resolveConfigValue(strategyConfig, keys);
        if (rawValue == null) {
            return null;
        }
        if (rawValue instanceof Number number) {
            return number.intValue();
        }
        try {
            String normalized = String.valueOf(rawValue).trim();
            return normalized.isEmpty() ? null : Integer.parseInt(normalized);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private BigDecimal resolveBigDecimal(Map<String, Object> strategyConfig, String... keys) {
        Object rawValue = resolveConfigValue(strategyConfig, keys);
        if (rawValue == null) {
            return null;
        }
        try {
            String normalized = String.valueOf(rawValue).trim();
            return normalized.isEmpty() ? null : new BigDecimal(normalized);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private Object resolveConfigValue(Map<String, Object> strategyConfig, String... keys) {
        if (strategyConfig == null || strategyConfig.isEmpty()) {
            return null;
        }
        Object direct = resolveFromMap(strategyConfig, keys);
        if (direct != null) {
            return direct;
        }
        for (String nestedKey : List.of("runtimeConfig", "riskConfig", "riskControl", "controlPlane", "dataSourceConfig", "agentConfig")) {
            Object nested = strategyConfig.get(nestedKey);
            if (nested instanceof Map<?, ?> nestedMap) {
                Object resolved = resolveFromMap(new LinkedHashMap<>((Map<String, Object>) nestedMap), keys);
                if (resolved != null) {
                    return resolved;
                }
            }
        }
        return null;
    }

    private Object resolveFromMap(Map<String, Object> source, String... keys) {
        for (String key : keys) {
            if (source.containsKey(key) && source.get(key) != null) {
                return source.get(key);
            }
        }
        return null;
    }

    private boolean matchesEnabledFlag(Object value) {
        return value != null && "1".equals(String.valueOf(value).trim());
    }

    private String normalizeRouteSchedulerMode(String routeSchedulerMode) {
        if (isBlank(routeSchedulerMode)) {
            return DEFAULT_ROUTE_SCHEDULER_MODE;
        }
        String normalized = routeSchedulerMode.trim().toUpperCase(Locale.ROOT);
        return ("THREAD_POOL".equals(normalized) || "SERIAL".equals(normalized))
            ? normalized
            : DEFAULT_ROUTE_SCHEDULER_MODE;
    }

    /**
     * 可交易品种域。
     *
     * <p>此前直接以 {@link TradeConstants#V1_ALLOWED_SYMBOLS} 作为白名单，等于把系统
     * 永久限制在 BTCUSDT/ETHUSDT/SOLUSDT 三个品种上，配置任何其他标的都会以
     * {@code unsupported scope} 拒绝并使 bootstrap 返回 500。而交易所实际提供 569 个
     * 币本位永续和 188 个 TRADIFI_PERPETUAL（股票/商品）标的。
     *
     * <p>白名单本身是有价值的护栏——它能挡住手滑写错的代码——所以这里保留校验，
     * 只是把品种域改为可由运行时标志 {@code symbolUniverse} 覆盖；未配置时仍回落到
     * 原有常量，行为与改动前一致。
     */
    private List<String> resolveSymbolUniverse(TradeRuntimeConfig config) {
        // 注意：allowedSymbolsJson 的归一化发生在 runtimeFlagsJson 归一化之前，
        // 因此这里读取的是尚未合并默认值的原始 JSON。
        String rawFlags = config == null ? null : config.getRuntimeFlagsJson();
        if (isBlank(rawFlags)) {
            return TradeConstants.V1_ALLOWED_SYMBOLS;
        }
        try {
            Map<String, Object> parsed = objectMapper.readValue(rawFlags, new TypeReference<Map<String, Object>>() {});
            Object universe = parsed == null ? null : parsed.get("symbolUniverse");
            if (!(universe instanceof List<?> listValue) || listValue.isEmpty()) {
                return TradeConstants.V1_ALLOWED_SYMBOLS;
            }
            LinkedHashSet<String> resolved = new LinkedHashSet<>(TradeConstants.V1_ALLOWED_SYMBOLS);
            for (Object item : listValue) {
                String candidate = item == null ? "" : String.valueOf(item).trim().toUpperCase();
                if (!candidate.isEmpty()) {
                    resolved.add(candidate);
                }
            }
            return new ArrayList<>(resolved);
        } catch (IOException e) {
            // 标志本身的格式错误交由 normalizeRuntimeFlagsJson 报告，这里不抢先抛出。
            return TradeConstants.V1_ALLOWED_SYMBOLS;
        }
    }

    private String normalizeArrayJson(String rawJson, List<String> allowedValues, String fieldName) {
        List<String> candidateValues = new ArrayList<>();
        if (!isBlank(rawJson)) {
            try {
                List<String> parsed = objectMapper.readValue(rawJson, new TypeReference<List<String>>() {});
                if (parsed != null) {
                    candidateValues.addAll(parsed);
                }
            } catch (IOException e) {
                throw new ServiceException(fieldName + " must be a JSON string array");
            }
        }
        if (candidateValues.isEmpty()) {
            candidateValues.addAll(allowedValues);
        }
        LinkedHashSet<String> normalized = new LinkedHashSet<>();
        for (String value : candidateValues) {
            if (isBlank(value)) {
                continue;
            }
            String canonical = value.trim().toUpperCase();
            if (!allowedValues.contains(canonical)) {
                throw new ServiceException(fieldName + " contains unsupported scope: " + canonical);
            }
            normalized.add(canonical);
        }
        if (normalized.isEmpty()) {
            normalized.addAll(allowedValues);
        }
        try {
            return objectMapper.writeValueAsString(new ArrayList<>(normalized));
        } catch (IOException e) {
            throw new ServiceException("Failed to normalize " + fieldName);
        }
    }

    private String normalizeObjectJson(String rawJson, String fieldName) {
        if (isBlank(rawJson)) {
            return DEFAULT_JSON_OBJECT;
        }
        try {
            Map<String, Object> parsed = objectMapper.readValue(rawJson, new TypeReference<Map<String, Object>>() {});
            return objectMapper.writeValueAsString(parsed == null ? Map.of() : parsed);
        } catch (IOException e) {
            throw new ServiceException(fieldName + " must be a JSON object");
        }
    }

    private String normalizeRuntimeFlagsJson(String rawJson) {
        Map<String, Object> candidate = new LinkedHashMap<>();
        if (!isBlank(rawJson)) {
            try {
                Map<String, Object> parsed = objectMapper.readValue(rawJson, new TypeReference<Map<String, Object>>() {});
                if (parsed != null) {
                    candidate.putAll(parsed);
                }
            } catch (IOException e) {
                throw new ServiceException("runtimeFlagsJson must be a JSON object");
            }
        }
        Map<String, Object> normalized = deepMerge(buildDefaultRuntimeFlags(), candidate);
        try {
            return objectMapper.writeValueAsString(normalized);
        } catch (IOException e) {
            throw new ServiceException("Failed to normalize runtimeFlagsJson");
        }
    }

    private Map<String, Object> buildDefaultRuntimeFlags() {
        Map<String, Object> defaults = new LinkedHashMap<>();
        defaults.put("triggerMode", DEFAULT_TRIGGER_MODE);

        Map<String, Object> marketTrigger = new LinkedHashMap<>();
        marketTrigger.put("priceChangePct", new BigDecimal("2.5"));
        marketTrigger.put("priceAccelerationPct", new BigDecimal("1.2"));
        marketTrigger.put("liquidationNotionalUsd", 250000);
        defaults.put("marketTrigger", marketTrigger);

        Map<String, Object> newsTrigger = new LinkedHashMap<>();
        newsTrigger.put("scoreThreshold", new BigDecimal("0.80"));
        newsTrigger.put("severityThreshold", "high");
        defaults.put("newsTrigger", newsTrigger);

        Map<String, Object> onchainTrigger = new LinkedHashMap<>();
        onchainTrigger.put("flowUsdThreshold", 500000);
        onchainTrigger.put("exchangeNetflowBias", new BigDecimal("0.65"));
        defaults.put("onchainTrigger", onchainTrigger);

        Map<String, Object> socialTrigger = new LinkedHashMap<>();
        socialTrigger.put("scoreThreshold", new BigDecimal("0.75"));
        socialTrigger.put("burstCount", 3);
        defaults.put("socialTrigger", socialTrigger);

        Map<String, Object> signalMemoryPolicy = new LinkedHashMap<>();
        signalMemoryPolicy.put("market", buildSignalMemoryWindow(180, "linear", 120));
        signalMemoryPolicy.put("news", buildSignalMemoryWindow(900, "linear", 900));
        signalMemoryPolicy.put("onchain", buildSignalMemoryWindow(3600, "step", 2400));
        signalMemoryPolicy.put("social", buildSignalMemoryWindow(600, "linear", 600));
        defaults.put("signalMemoryPolicy", signalMemoryPolicy);

        List<Map<String, Object>> triggerMatrix = new ArrayList<>();
        triggerMatrix.add(buildTriggerMatrixRule("strong_news_then_break", List.of("news", "market"), "LLM_ALLOWED"));
        triggerMatrix.add(buildTriggerMatrixRule("onchain_flow_then_market_weakness", List.of("onchain", "market"), "LLM_ALLOWED"));
        triggerMatrix.add(buildTriggerMatrixRule("social_then_news_confirmation", List.of("social", "news"), "RULE_ONLY"));
        defaults.put("triggerMatrix", triggerMatrix);

        Map<String, Object> cooldownPolicy = new LinkedHashMap<>();
        cooldownPolicy.put("globalSeconds", 300);
        cooldownPolicy.put("sameSourceSeconds", 180);
        cooldownPolicy.put("replayBypass", Boolean.TRUE);
        defaults.put("cooldownPolicy", cooldownPolicy);

        Map<String, Object> llmBudgetPolicy = new LinkedHashMap<>();
        llmBudgetPolicy.put("perSymbolDailyLimit", 6);
        llmBudgetPolicy.put("rollingWindowMinutes", 60);
        llmBudgetPolicy.put("rollingWindowLimit", 2);
        llmBudgetPolicy.put("exhaustToRuleOnly", Boolean.TRUE);
        defaults.put("llmBudgetPolicy", llmBudgetPolicy);

        Map<String, Object> dedupePolicy = new LinkedHashMap<>();
        dedupePolicy.put("sameDirectionOnly", Boolean.TRUE);
        dedupePolicy.put("dedupeWindowSeconds", 300);
        dedupePolicy.put("preferHigherStrength", Boolean.TRUE);
        defaults.put("dedupePolicy", dedupePolicy);
        return defaults;
    }

    private Map<String, Object> buildSignalMemoryWindow(int ttlSeconds, String decayMode, int combineWithinSeconds) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("ttlSeconds", ttlSeconds);
        payload.put("decayMode", decayMode);
        payload.put("combineWithinSeconds", combineWithinSeconds);
        return payload;
    }

    private Map<String, Object> buildTriggerMatrixRule(String code, List<String> sources, String upgradeTo) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("code", code);
        payload.put("sources", new ArrayList<>(sources));
        payload.put("upgradeTo", upgradeTo);
        return payload;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> deepMerge(Map<String, Object> defaults, Map<String, Object> overrides) {
        Map<String, Object> merged = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : defaults.entrySet()) {
            Object value = entry.getValue();
            if (value instanceof Map<?, ?> mapValue) {
                merged.put(entry.getKey(), deepMerge((Map<String, Object>) mapValue, Map.of()));
            } else if (value instanceof List<?> listValue) {
                merged.put(entry.getKey(), new ArrayList<>(listValue));
            } else {
                merged.put(entry.getKey(), value);
            }
        }
        if (overrides == null || overrides.isEmpty()) {
            return merged;
        }
        for (Map.Entry<String, Object> entry : overrides.entrySet()) {
            Object existing = merged.get(entry.getKey());
            Object overrideValue = entry.getValue();
            if (existing instanceof Map<?, ?> existingMap && overrideValue instanceof Map<?, ?> overrideMap) {
                merged.put(
                    entry.getKey(),
                    deepMerge(new LinkedHashMap<>((Map<String, Object>) existingMap), new LinkedHashMap<>((Map<String, Object>) overrideMap))
                );
                continue;
            }
            if (overrideValue instanceof List<?> overrideList) {
                merged.put(entry.getKey(), new ArrayList<>(overrideList));
                continue;
            }
            merged.put(entry.getKey(), overrideValue);
        }
        return merged;
    }

    private AiModelConfig sanitizeAiModelConfig(AiModelConfig source) {
        if (source == null) {
            return null;
        }
        AiModelConfig sanitized = new AiModelConfig();
        sanitized.setId(source.getId());
        sanitized.setModelKey(source.getModelKey());
        sanitized.setModelCode(source.getModelCode());
        sanitized.setModelName(source.getModelName());
        sanitized.setProvider(source.getProvider());
        sanitized.setApiEndpoint(source.getApiEndpoint());
        sanitized.setApiBaseUrl(source.getApiBaseUrl());
        sanitized.setApiVersion(source.getApiVersion());
        sanitized.setModelVersion(source.getModelVersion());
        sanitized.setTimeoutSeconds(source.getTimeoutSeconds());
        sanitized.setRetryTimes(source.getRetryTimes());
        sanitized.setPriority(source.getPriority());
        sanitized.setMaxTemperature(source.getMaxTemperature());
        sanitized.setTemperature(source.getTemperature());
        sanitized.setTopP(source.getTopP());
        sanitized.setMaxTokens(source.getMaxTokens());
        sanitized.setIsEnabled(source.getIsEnabled());
        sanitized.setIsDefault(source.getIsDefault());
        sanitized.setDescription(source.getDescription());
        sanitized.setUsageCount(source.getUsageCount());
        sanitized.setRemark(source.getRemark());
        sanitized.setApiKey(null);
        sanitized.setApiKeyEncrypted(null);
        return sanitized;
    }

    private MarketApiConfig sanitizeMarketApiConfig(MarketApiConfig source) {
        if (source == null) {
            return null;
        }
        MarketApiConfig sanitized = new MarketApiConfig();
        sanitized.setId(source.getId());
        sanitized.setVersionNo(source.getVersionNo());
        sanitized.setConfigName(source.getConfigName());
        sanitized.setDataCategory(source.getDataCategory());
        sanitized.setDataSubType(source.getDataSubType());
        sanitized.setTransportType(source.getTransportType());
        sanitized.setVendorCode(source.getVendorCode());
        sanitized.setMarketScope(source.getMarketScope());
        sanitized.setApiName(source.getApiName());
        sanitized.setApiUrl(source.getApiUrl());
        sanitized.setWsBaseUrl(source.getWsBaseUrl());
        sanitized.setWsPath(source.getWsPath());
        sanitized.setWsStreamNameTemplate(source.getWsStreamNameTemplate());
        sanitized.setWsCombinedEnabled(source.getWsCombinedEnabled());
        sanitized.setWsSymbolLowercase(source.getWsSymbolLowercase());
        sanitized.setWsPingIntervalSeconds(source.getWsPingIntervalSeconds());
        sanitized.setWsPongTimeoutSeconds(source.getWsPongTimeoutSeconds());
        sanitized.setWsConnectionTtlHours(source.getWsConnectionTtlHours());
        sanitized.setWsMaxStreamsPerConnection(source.getWsMaxStreamsPerConnection());
        sanitized.setWsControlMessagesPerSecond(source.getWsControlMessagesPerSecond());
        sanitized.setDocReferenceUrl(source.getDocReferenceUrl());
        sanitized.setHttpMethod(source.getHttpMethod());
        sanitized.setResponsePath(source.getResponsePath());
        sanitized.setFieldMapping(source.getFieldMapping());
        sanitized.setTimeout(source.getTimeout());
        sanitized.setEnabled(source.getEnabled());
        sanitized.setPriority(source.getPriority());
        sanitized.setDataTransform(source.getDataTransform());
        sanitized.setUseProxy(source.getUseProxy());
        sanitized.setProxyUrl(source.getProxyUrl());
        sanitized.setApplySymbols(source.getApplySymbols());
        sanitized.setRemark(source.getRemark());
        sanitized.setCreateTime(source.getCreateTime());
        sanitized.setUpdateTime(source.getUpdateTime());
        return sanitized;
    }

    private boolean matchesScopeJson(String json, String expectedValue) {
        List<String> values = parseJsonArray(json);
        if (values.isEmpty()) {
            return true;
        }
        if (expectedValue == null || expectedValue.isBlank()) {
            return false;
        }
        for (String value : values) {
            if (expectedValue.equalsIgnoreCase(String.valueOf(value).trim())) {
                return true;
            }
        }
        return false;
    }

    private List<String> parseJsonArray(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<String> parsed = objectMapper.readValue(json, new TypeReference<List<String>>() {});
            return parsed == null ? List.of() : parsed;
        } catch (IOException e) {
            throw new ServiceException("Invalid scope json payload");
        }
    }

    private String resolveEffectiveRuntimeMode(TradeRuntimeConfig config) {
        TradeRuntimeMode mode = config == null || config.getDefaultMode() == null ? TradeRuntimeMode.PAPER : config.getDefaultMode();
        if (TradeRuntimeMode.LIVE.equals(mode) && (config == null || !Boolean.TRUE.equals(config.getLiveEnabled()))) {
            return TradeRuntimeMode.SHADOW.name().toLowerCase(Locale.ROOT);
        }
        return mode.name().toLowerCase(Locale.ROOT);
    }

    private String normalizeUpper(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim().toUpperCase(Locale.ROOT);
    }

    private Long resolveCurrentUserId() {
        try {
            return SecurityUtils.getUserId();
        } catch (Exception ignored) {
            return null;
        }
    }

    private MarketDataConfig sanitizeMarketDataConfig(MarketDataConfig source) {
        if (source == null) {
            return null;
        }
        MarketDataConfig sanitized = new MarketDataConfig();
        sanitized.setId(source.getId());
        sanitized.setConfigName(source.getConfigName());
        sanitized.setSymbol(source.getSymbol());
        sanitized.setEnabled(source.getEnabled());
        sanitized.setCollectInterval(source.getCollectInterval());
        sanitized.setDataSources(source.getDataSources());
        sanitized.setCollectKline(source.getCollectKline());
        sanitized.setKlinePeriods(source.getKlinePeriods());
        sanitized.setCollectFearGreed(source.getCollectFearGreed());
        sanitized.setCollectOnchain(source.getCollectOnchain());
        sanitized.setApiKeyConfig(null);
        sanitized.setRemark(source.getRemark());
        return sanitized;
    }

    /**
     * 检查布尔启用标志是否为 true
     */
    private static boolean isEnabled(Boolean enabled) {
        return Boolean.TRUE.equals(enabled);
    }
}
