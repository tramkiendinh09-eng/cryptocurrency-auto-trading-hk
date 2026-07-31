package com.ruoyi.dca.trade.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.domain.MarketDataConfig;
import com.ruoyi.dca.domain.MarketApiConfig;
import com.ruoyi.dca.domain.enums.TradeRuntimeMode;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.trade.ExchangeAccount;
import com.ruoyi.dca.domain.trade.ExchangeAccountBinding;
import com.ruoyi.dca.domain.trade.ResolvedAgentConfig;
import com.ruoyi.dca.domain.trade.TradePositionGuard;
import com.ruoyi.dca.domain.trade.TradeAgentProfile;
import com.ruoyi.dca.domain.trade.TradeDataSourceBinding;
import com.ruoyi.dca.domain.trade.TradePromptBinding;
import com.ruoyi.dca.domain.trade.TradeRuntimeAccountContext;
import com.ruoyi.dca.domain.trade.TradeRuntimeBootstrap;
import com.ruoyi.dca.domain.trade.TradeRuntimeConfig;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.domain.trade.TradeStrategyVersion;
import com.ruoyi.dca.domain.trade.TradeSymbolScope;
import com.ruoyi.dca.mapper.runtime.TradeExecutionMapper;
import com.ruoyi.dca.mapper.runtime.TradePositionGuardMapper;
import com.ruoyi.dca.mapper.trade.ExchangeAccountMapper;
import com.ruoyi.dca.mapper.trade.TradeAgentProfileMapper;
import com.ruoyi.dca.mapper.trade.TradeDataSourceBindingMapper;
import com.ruoyi.dca.mapper.trade.TradePromptBindingMapper;
import com.ruoyi.dca.mapper.trade.TradeRuntimeConfigMapper;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.IAiModelConfigService;
import com.ruoyi.dca.service.IMarketApiConfigService;
import com.ruoyi.dca.service.IMarketDataConfigService;
import com.ruoyi.dca.service.trade.impl.TradeRuntimeConfigServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Date;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TradeRuntimeConfigServiceImplTest {

    @Mock
    private TradeRuntimeConfigMapper tradeRuntimeConfigMapper;

    @Mock
    private TradeStrategyMapper tradeStrategyMapper;

    @Mock
    private ExchangeAccountMapper exchangeAccountMapper;

    @Mock
    private IAiModelConfigService aiModelConfigService;

    @Mock
    private IMarketApiConfigService marketApiConfigService;

    @Mock
    private IMarketDataConfigService marketDataConfigService;

    @Mock
    private TradeDataSourceBindingMapper tradeDataSourceBindingMapper;

    @Mock
    private TradeExecutionMapper tradeExecutionMapper;

    @Mock
    private TradePromptBindingMapper tradePromptBindingMapper;

    @Mock
    private TradeAgentProfileMapper tradeAgentProfileMapper;

    @Mock
    private TradePositionGuardMapper tradePositionGuardMapper;

    @Spy
    private ObjectMapper objectMapper;

    @InjectMocks
    private TradeRuntimeConfigServiceImpl tradeRuntimeConfigService;

    @Test
    void getBootstrapConfigReturnsRuntimeOnlyWhenNoEnabledStrategies() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.PAPER);
        config.setLiveEnabled(Boolean.FALSE);
        config.setMaxPositionRatio(new java.math.BigDecimal("0.40"));
        config.setMaxDailyLoss(new java.math.BigDecimal("-500.00"));
        config.setMaxConsecutiveFailures(3);
        config.setAllowedSymbolsJson("[\"BTCUSDT\",\"ETHUSDT\",\"SOLUSDT\"]");
        config.setAllowedExchangesJson("[\"BINANCE\",\"OKX\"]");
        config.setRequireAccountBinding(Boolean.TRUE);
        config.setLiveOrderRequiresHealthyAccount(Boolean.TRUE);
        config.setRuntimeFlagsJson("{\"haltOnDataGap\":true}");
        config.setNotifyDefaultsJson("{\"severities\":[\"ERROR\"]}");
        config.setEventRetentionDays(30);
        config.setReplayRetentionDays(30);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of());

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getRuntimeConfig().getDefaultMode()).isEqualTo(TradeRuntimeMode.PAPER);
        assertThat(bootstrap.getRuntimeConfig().getLiveEnabled()).isFalse();
        assertThat(bootstrap.getRuntimeConfig().getMaxPositionRatio()).isEqualByComparingTo("0.40");
        assertThat(bootstrap.getRuntimeConfig().getMaxDailyLoss()).isEqualByComparingTo("-500.00");
        assertThat(bootstrap.getRuntimeConfig().getMaxConsecutiveFailures()).isEqualTo(3);
        assertThat(bootstrap.getRuntimeConfig().getAllowedSymbolsJson()).isEqualTo("[\"BTCUSDT\",\"ETHUSDT\",\"SOLUSDT\"]");
        assertThat(bootstrap.getRuntimeConfig().getAllowedExchangesJson()).isEqualTo("[\"BINANCE\",\"OKX\"]");
        assertThat(bootstrap.getRuntimeConfig().getRequireAccountBinding()).isTrue();
        assertThat(bootstrap.getRuntimeConfig().getLiveOrderRequiresHealthyAccount()).isTrue();
        assertThat(bootstrap.getRuntimeConfig().getRuntimeFlagsJson()).contains("\"haltOnDataGap\":true");
        assertThat(bootstrap.getRuntimeConfig().getRuntimeFlagsJson()).contains("\"triggerMode\":\"EVENT_GATED\"");
        assertThat(bootstrap.getRuntimeConfig().getTriggerMode()).isEqualTo("EVENT_GATED");
        assertThat(bootstrap.getRuntimeConfig().getSignalMemoryPolicy()).containsKeys("market", "news", "onchain", "social");
        assertThat(bootstrap.getRuntimeConfig().getNotifyDefaultsJson()).isEqualTo("{\"severities\":[\"ERROR\"]}");
        assertThat(bootstrap.getRuntimeConfig().getEventRetentionDays()).isEqualTo(30);
        assertThat(bootstrap.getRuntimeConfig().getReplayRetentionDays()).isEqualTo(30);
        assertThat(bootstrap.getStrategy()).isNull();
        assertThat(bootstrap.getStrategyVersion()).isNull();
        assertThat(bootstrap.getSymbolScope()).isNull();
        assertThat(bootstrap.getExchangeAccountBinding()).isNull();
        assertThat(bootstrap.getExchangeAccount()).isNull();
    }

    @Test
    void getBootstrapConfigIncludesDbManagedModelAndFeedApiConfigs() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.PAPER);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of());

        AiModelConfig modelConfig = new AiModelConfig();
        modelConfig.setId(101L);
        modelConfig.setModelCode("gpt-4.1");
        modelConfig.setModelName("Primary Runtime Model");
        modelConfig.setProvider("openai");
        when(aiModelConfigService.getDefaultModel()).thenReturn(modelConfig);

        MarketApiConfig newsApiConfig = new MarketApiConfig();
        newsApiConfig.setId(201L);
        newsApiConfig.setDataCategory("NEWS");
        newsApiConfig.setApiName("NEWS_FEED");
        newsApiConfig.setApiUrl("https://feeds.internal/news");

        MarketApiConfig onchainApiConfig = new MarketApiConfig();
        onchainApiConfig.setId(202L);
        onchainApiConfig.setDataCategory("ONCHAIN");
        onchainApiConfig.setApiName("ONCHAIN_FEED");
        onchainApiConfig.setApiUrl("https://feeds.internal/onchain");

        MarketApiConfig socialApiConfig = new MarketApiConfig();
        socialApiConfig.setId(203L);
        socialApiConfig.setDataCategory("SOCIAL");
        socialApiConfig.setApiName("SOCIAL_FEED");
        socialApiConfig.setApiUrl("https://feeds.internal/social");

        MarketDataConfig marketDataConfig = new MarketDataConfig();
        marketDataConfig.setId(301L);
        marketDataConfig.setSymbol("BTCUSDT");
        marketDataConfig.setEnabled("1");
        marketDataConfig.setCollectInterval(15);
        marketDataConfig.setCollectOnchain("1");
        marketDataConfig.setDataSources("[\"binance\",\"rss\",\"whale-alert\"]");

        when(marketApiConfigService.selectEnabledApis("NEWS")).thenReturn(List.of(newsApiConfig));
        when(marketApiConfigService.selectEnabledApis("ONCHAIN")).thenReturn(List.of(onchainApiConfig));
        when(marketApiConfigService.selectEnabledApis("SOCIAL")).thenReturn(List.of(socialApiConfig));
        when(marketDataConfigService.selectConfigBySymbol("BTCUSDT")).thenReturn(marketDataConfig);

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getAiModelConfig()).isNotNull();
        assertThat(bootstrap.getAiModelConfig().getModelCode()).isEqualTo("gpt-4.1");
        assertThat(bootstrap.getNewsApiConfig()).isNotNull();
        assertThat(bootstrap.getNewsApiConfig().getApiUrl()).isEqualTo("https://feeds.internal/news");
        assertThat(bootstrap.getOnchainApiConfig()).isNotNull();
        assertThat(bootstrap.getOnchainApiConfig().getApiUrl()).isEqualTo("https://feeds.internal/onchain");
        assertThat(bootstrap.getSocialApiConfig()).isNotNull();
        assertThat(bootstrap.getSocialApiConfig().getApiUrl()).isEqualTo("https://feeds.internal/social");
        assertThat(bootstrap.getMarketDataConfig()).isNotNull();
        assertThat(bootstrap.getMarketDataConfig().getSymbol()).isEqualTo("BTCUSDT");
        assertThat(bootstrap.getMarketDataConfig().getCollectOnchain()).isEqualTo("1");
    }

    @Test
    void getBootstrapConfigSelectsExactScopeLatestVersionAndFirstEnabledAccountBinding() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(7L);
        strategy.setStrategyKey("btc-event");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(7L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("binance");
        when(tradeStrategyMapper.selectTradeSymbolScopes(7L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(7L);
        version.setVersionNo(5);
        version.setConfigJson("{\"riskBudget\":0.02}");
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(7L)).thenReturn(version);

        ExchangeAccountBinding disabledBinding = new ExchangeAccountBinding();
        disabledBinding.setStrategyId(7L);
        disabledBinding.setAccountId(10L);
        disabledBinding.setExchangeCode("binance");
        disabledBinding.setEnabled(Boolean.FALSE);

        ExchangeAccountBinding disabledAccountBinding = new ExchangeAccountBinding();
        disabledAccountBinding.setStrategyId(7L);
        disabledAccountBinding.setAccountId(11L);
        disabledAccountBinding.setExchangeCode("binance");
        disabledAccountBinding.setEnabled(Boolean.TRUE);

        ExchangeAccountBinding activeBinding = new ExchangeAccountBinding();
        activeBinding.setStrategyId(7L);
        activeBinding.setAccountId(12L);
        activeBinding.setExchangeCode("binance");
        activeBinding.setEnabled(Boolean.TRUE);
        when(tradeStrategyMapper.selectExchangeAccountBindings(7L))
            .thenReturn(List.of(disabledBinding, disabledAccountBinding, activeBinding));

        ExchangeAccount disabledAccount = new ExchangeAccount();
        disabledAccount.setId(11L);
        disabledAccount.setExchangeCode("binance");
        disabledAccount.setEnabled(Boolean.FALSE);
        when(exchangeAccountMapper.selectExchangeAccountById(11L)).thenReturn(disabledAccount);

        ExchangeAccount activeAccount = new ExchangeAccount();
        activeAccount.setId(12L);
        activeAccount.setExchangeCode("binance");
        activeAccount.setAccountName("primary-binance");
        activeAccount.setEnabled(Boolean.TRUE);
        when(exchangeAccountMapper.selectExchangeAccountById(12L)).thenReturn(activeAccount);

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getRuntimeConfig().getDefaultMode()).isEqualTo(TradeRuntimeMode.SHADOW);
        assertThat(bootstrap.getStrategy().getId()).isEqualTo(7L);
        assertThat(bootstrap.getStrategyVersion().getVersionNo()).isEqualTo(5);
        assertThat(bootstrap.getSymbolScope().getSymbol()).isEqualTo("BTCUSDT");
        assertThat(bootstrap.getExchangeAccountBinding().getAccountId()).isEqualTo(12L);
        assertThat(bootstrap.getExchangeAccount().getAccountName()).isEqualTo("primary-binance");
    }

    @Test
    void getBootstrapConfigIncludesFilteredPromptBindingsAndEnabledAgentProfiles() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(71L);
        strategy.setStrategyKey("prompt-bootstrap");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(71L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("binance");
        when(tradeStrategyMapper.selectTradeSymbolScopes(71L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setId(171L);
        version.setStrategyId(71L);
        version.setVersionNo(3);
        version.setConfigJson("{\"riskBudget\":0.02}");
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(71L)).thenReturn(version);

        TradePromptBinding exactBinding = new TradePromptBinding();
        exactBinding.setId(1L);
        exactBinding.setStrategyId(71L);
        exactBinding.setStrategyVersionId(171L);
        exactBinding.setSymbol("BTCUSDT");
        exactBinding.setExchangeCode("BINANCE");
        exactBinding.setBindingScope("SUPERVISOR");
        exactBinding.setTemplateCode("trade.supervisor.v1");
        exactBinding.setPriority(10);
        exactBinding.setModeScopeJson("[\"shadow\"]");
        exactBinding.setEnabled(Boolean.TRUE);

        TradePromptBinding globalBinding = new TradePromptBinding();
        globalBinding.setId(2L);
        globalBinding.setBindingScope("MARKET_AGENT");
        globalBinding.setTemplateCode("trade.market.v1");
        globalBinding.setPriority(20);
        globalBinding.setEnabled(Boolean.TRUE);

        TradePromptBinding wrongModeBinding = new TradePromptBinding();
        wrongModeBinding.setId(3L);
        wrongModeBinding.setStrategyId(71L);
        wrongModeBinding.setStrategyVersionId(171L);
        wrongModeBinding.setSymbol("BTCUSDT");
        wrongModeBinding.setExchangeCode("BINANCE");
        wrongModeBinding.setBindingScope("NEWS_AGENT");
        wrongModeBinding.setTemplateCode("trade.news.v1");
        wrongModeBinding.setModeScopeJson("[\"live\"]");
        wrongModeBinding.setEnabled(Boolean.TRUE);

        TradePromptBinding wrongSymbolBinding = new TradePromptBinding();
        wrongSymbolBinding.setId(4L);
        wrongSymbolBinding.setStrategyId(71L);
        wrongSymbolBinding.setStrategyVersionId(171L);
        wrongSymbolBinding.setSymbol("ETHUSDT");
        wrongSymbolBinding.setExchangeCode("BINANCE");
        wrongSymbolBinding.setBindingScope("SOCIAL_AGENT");
        wrongSymbolBinding.setTemplateCode("trade.social.v1");
        wrongSymbolBinding.setEnabled(Boolean.TRUE);

        when(tradePromptBindingMapper.selectTradePromptBindingList(any(TradePromptBinding.class)))
            .thenReturn(List.of(exactBinding, globalBinding, wrongModeBinding, wrongSymbolBinding));

        TradeAgentProfile supervisorProfile = new TradeAgentProfile();
        supervisorProfile.setId(11L);
        supervisorProfile.setAgentCode("supervisor_agent");
        supervisorProfile.setAgentType("HYBRID");
        supervisorProfile.setEnabled(Boolean.TRUE);
        supervisorProfile.setLlmEnabled(Boolean.TRUE);
        supervisorProfile.setDefaultModelId(21L);
        supervisorProfile.setDefaultTemplateCode("trade.supervisor.default");
        supervisorProfile.setDefaultFallbackTemplateCode("trade.supervisor.fallback");
        supervisorProfile.setDefaultOutputSchemaCode("supervisor_decision_v1");
        supervisorProfile.setSpeakOrder(1);

        TradeAgentProfile disabledProfile = new TradeAgentProfile();
        disabledProfile.setId(12L);
        disabledProfile.setAgentCode("news_agent");
        disabledProfile.setEnabled(Boolean.FALSE);
        disabledProfile.setSpeakOrder(2);

        TradeAgentProfile marketProfile = new TradeAgentProfile();
        marketProfile.setId(13L);
        marketProfile.setAgentCode("market_agent");
        marketProfile.setAgentType("LLM");
        marketProfile.setEnabled(Boolean.TRUE);
        marketProfile.setLlmEnabled(Boolean.TRUE);
        marketProfile.setDefaultModelId(22L);
        marketProfile.setDefaultTemplateCode("trade.market.default");
        marketProfile.setDefaultOutputSchemaCode("agent_view_v1");
        marketProfile.setSpeakOrder(3);

        when(tradeAgentProfileMapper.selectTradeAgentProfileList(any(TradeAgentProfile.class)))
            .thenReturn(List.of(marketProfile, disabledProfile, supervisorProfile));

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getPromptBindings()).extracting(TradePromptBinding::getId).containsExactly(1L, 2L);
        assertThat(bootstrap.getAgentProfiles()).extracting(TradeAgentProfile::getAgentCode).containsExactly("supervisor_agent", "market_agent");
        assertThat(bootstrap.getResolvedAgentConfigs()).extracting(ResolvedAgentConfig::getAgentCode)
            .containsExactly("supervisor_agent", "market_agent");
        assertThat(bootstrap.getResolvedAgentConfigs().get(0).getModelId()).isEqualTo(21L);
        assertThat(bootstrap.getResolvedAgentConfigs().get(0).getTemplateCode()).isEqualTo("trade.supervisor.v1");
        assertThat(bootstrap.getResolvedAgentConfigs().get(0).getFallbackTemplateCode()).isEqualTo("trade.supervisor.fallback");
        assertThat(bootstrap.getResolvedAgentConfigs().get(0).getOutputSchemaCode()).isEqualTo("supervisor_decision_v1");
        assertThat(bootstrap.getResolvedAgentConfigs().get(0).getSourceProfileId()).isEqualTo(11L);
        assertThat(bootstrap.getResolvedAgentConfigs().get(0).getSourceBindingId()).isEqualTo(1L);
        assertThat(bootstrap.getResolvedAgentConfigs().get(0).getResolutionSource()).isEqualTo("BINDING_OVERRIDE");
        assertThat(bootstrap.getResolvedAgentConfigs().get(1).getModelId()).isEqualTo(22L);
        assertThat(bootstrap.getResolvedAgentConfigs().get(1).getTemplateCode()).isEqualTo("trade.market.v1");
    }

    @Test
    void getBootstrapConfigLoadsAgentProfilesWithoutPromptBindings() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(72L);
        strategy.setStrategyKey("profile-default-bootstrap");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(72L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("OKX");
        when(tradeStrategyMapper.selectTradeSymbolScopes(72L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setId(172L);
        version.setStrategyId(72L);
        version.setVersionNo(1);
        version.setConfigJson("{}");
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(72L)).thenReturn(version);

        when(tradePromptBindingMapper.selectTradePromptBindingList(any(TradePromptBinding.class)))
            .thenReturn(List.of());

        TradeAgentProfile supervisorProfile = new TradeAgentProfile();
        supervisorProfile.setId(81L);
        supervisorProfile.setAgentCode("supervisor_agent");
        supervisorProfile.setAgentType("HYBRID");
        supervisorProfile.setEnabled(Boolean.TRUE);
        supervisorProfile.setLlmEnabled(Boolean.TRUE);
        supervisorProfile.setSpeakOrder(1);
        supervisorProfile.setDefaultModelId(6L);
        supervisorProfile.setDefaultTemplateCode("trade.supervisor.v1");
        supervisorProfile.setDefaultFallbackTemplateCode("trade.supervisor.fallback");
        supervisorProfile.setDefaultOutputSchemaCode("supervisor_decision_v1");

        TradeAgentProfile marketProfile = new TradeAgentProfile();
        marketProfile.setId(82L);
        marketProfile.setAgentCode("market_agent");
        marketProfile.setAgentType("LLM");
        marketProfile.setEnabled(Boolean.TRUE);
        marketProfile.setLlmEnabled(Boolean.TRUE);
        marketProfile.setSpeakOrder(2);
        marketProfile.setDefaultModelId(6L);
        marketProfile.setDefaultTemplateCode("trade.market.v1");
        marketProfile.setDefaultOutputSchemaCode("agent_view_v1");

        when(tradeAgentProfileMapper.selectTradeAgentProfileList(any(TradeAgentProfile.class)))
            .thenReturn(List.of(supervisorProfile, marketProfile));
        AiModelConfig modelConfig = new AiModelConfig();
        modelConfig.setId(6L);
        modelConfig.setModelCode("deepseek-reasoner");
        modelConfig.setProvider("deepseek");
        modelConfig.setIsEnabled(1);
        when(aiModelConfigService.selectAiModelConfigById(6L)).thenReturn(modelConfig);

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "okx");

        assertThat(bootstrap.getPromptBindings()).isEmpty();
        assertThat(bootstrap.getAgentProfiles())
            .extracting(TradeAgentProfile::getAgentCode)
            .containsExactly("supervisor_agent", "market_agent");
        assertThat(bootstrap.getResolvedAgentConfigs())
            .extracting(ResolvedAgentConfig::getAgentCode, ResolvedAgentConfig::getTemplateCode, ResolvedAgentConfig::getModelCode, ResolvedAgentConfig::getResolutionSource)
            .containsExactly(
                org.assertj.core.groups.Tuple.tuple("supervisor_agent", "trade.supervisor.v1", "deepseek-reasoner", "PROFILE_DEFAULT"),
                org.assertj.core.groups.Tuple.tuple("market_agent", "trade.market.v1", "deepseek-reasoner", "PROFILE_DEFAULT")
            );
    }

    @Test
    void getBootstrapConfigKeepsMultipleBindingsForSameScopeWhenEventStrengthDiffers() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(73L);
        strategy.setStrategyKey("event-strength-bindings");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(73L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("BINANCE");
        when(tradeStrategyMapper.selectTradeSymbolScopes(73L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setId(173L);
        version.setStrategyId(73L);
        version.setVersionNo(1);
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(73L)).thenReturn(version);

        TradePromptBinding normalBinding = new TradePromptBinding();
        normalBinding.setId(31L);
        normalBinding.setStrategyId(73L);
        normalBinding.setStrategyVersionId(173L);
        normalBinding.setSymbol("BTCUSDT");
        normalBinding.setExchangeCode("BINANCE");
        normalBinding.setBindingScope("MARKET_AGENT");
        normalBinding.setTemplateCode("trade.market.normal");
        normalBinding.setModeScopeJson("[\"shadow\"]");
        normalBinding.setEventStrengthScopeJson("[\"normal\"]");
        normalBinding.setEnabled(Boolean.TRUE);

        TradePromptBinding strongBinding = new TradePromptBinding();
        strongBinding.setId(32L);
        strongBinding.setStrategyId(73L);
        strongBinding.setStrategyVersionId(173L);
        strongBinding.setSymbol("BTCUSDT");
        strongBinding.setExchangeCode("BINANCE");
        strongBinding.setBindingScope("MARKET_AGENT");
        strongBinding.setTemplateCode("trade.market.strong");
        strongBinding.setModeScopeJson("[\"shadow\"]");
        strongBinding.setEventStrengthScopeJson("[\"strong\"]");
        strongBinding.setEnabled(Boolean.TRUE);

        when(tradePromptBindingMapper.selectTradePromptBindingList(any(TradePromptBinding.class)))
            .thenReturn(List.of(normalBinding, strongBinding));

        TradeAgentProfile marketProfile = new TradeAgentProfile();
        marketProfile.setId(41L);
        marketProfile.setAgentCode("market_agent");
        marketProfile.setEnabled(Boolean.TRUE);
        marketProfile.setSpeakOrder(1);
        when(tradeAgentProfileMapper.selectTradeAgentProfileList(any(TradeAgentProfile.class))).thenReturn(List.of(marketProfile));

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getPromptBindings())
            .extracting(TradePromptBinding::getId)
            .containsExactly(31L, 32L);
    }

    @Test
    void getBootstrapConfigKeepsSupervisorPromptBindingWhenSupervisorProfileIsMissing() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(72L);
        strategy.setStrategyKey("supervisor-binding-only");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(72L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("BINANCE");
        when(tradeStrategyMapper.selectTradeSymbolScopes(72L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setId(172L);
        version.setStrategyId(72L);
        version.setVersionNo(1);
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(72L)).thenReturn(version);

        TradePromptBinding supervisorBinding = new TradePromptBinding();
        supervisorBinding.setId(5L);
        supervisorBinding.setStrategyId(72L);
        supervisorBinding.setStrategyVersionId(172L);
        supervisorBinding.setSymbol("BTCUSDT");
        supervisorBinding.setExchangeCode("BINANCE");
        supervisorBinding.setBindingScope("SUPERVISOR");
        supervisorBinding.setTemplateCode("trade.supervisor.v1");
        supervisorBinding.setFallbackTemplateCode("trade.supervisor.fallback");
        supervisorBinding.setEnabled(Boolean.TRUE);
        when(tradePromptBindingMapper.selectTradePromptBindingList(any(TradePromptBinding.class)))
            .thenReturn(List.of(supervisorBinding));

        when(tradeAgentProfileMapper.selectTradeAgentProfileList(any(TradeAgentProfile.class)))
            .thenReturn(List.of());

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getPromptBindings()).hasSize(1);
        assertThat(bootstrap.getPromptBindings().get(0).getBindingScope()).isEqualTo("SUPERVISOR");
        assertThat(bootstrap.getPromptBindings().get(0).getTemplateCode()).isEqualTo("trade.supervisor.v1");
        assertThat(bootstrap.getAgentProfiles()).isEmpty();
    }

    @Test
    void getBootstrapConfigIncludesDeliberationPolicyFromRuntimeConfig() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        config.setDeliberationEnabled(Boolean.TRUE);
        config.setDeliberationMaxRounds(1);
        config.setDeliberationFailOpen(Boolean.TRUE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of());

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getDeliberationPolicy()).containsEntry("enabled", true);
        assertThat(bootstrap.getDeliberationPolicy()).containsEntry("maxRounds", 1);
        assertThat(bootstrap.getDeliberationPolicy()).containsEntry("failOpen", true);
    }

    @Test
    void getBootstrapConfigCarriesRouteSchedulerSettingsFromRuntimeConfig() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        config.setRouteMaxConcurrency(4);
        config.setRouteSchedulerMode("THREAD_POOL");
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of());

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getRuntimeConfig().getRouteMaxConcurrency()).isEqualTo(4);
        assertThat(bootstrap.getRuntimeConfig().getRouteSchedulerMode()).isEqualTo("THREAD_POOL");
    }

    @Test
    void getBootstrapConfigExposesMergedTriggerThresholdsForPythonConsumers() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        config.setRuntimeFlagsJson("""
            {
              "triggerMode": "EVENT_GATED",
              "marketTrigger": {
                "ruleOnlyPriceChangePct": 1.0,
                "priceChangePct": 2.5
              },
              "newsTrigger": {
                "ruleOnlyScoreThreshold": 0.7,
                "scoreThreshold": 0.9
              }
            }
            """);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of());

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getRuntimeConfig().getMarketTrigger())
            .containsEntry("ruleOnlyPriceChangePct", 1.0)
            .containsEntry("priceChangePct", 2.5);
        assertThat(bootstrap.getRuntimeConfig().getNewsTrigger())
            .containsEntry("ruleOnlyScoreThreshold", 0.7)
            .containsEntry("scoreThreshold", 0.9);
    }

    @Test
    void getBootstrapConfigKeepsMostSpecificAndGlobalPromptBindingCandidatesForRuntimeResolver() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(88L);
        strategy.setStrategyKey("specificity-check");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(88L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("BINANCE");
        when(tradeStrategyMapper.selectTradeSymbolScopes(88L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setId(188L);
        version.setStrategyId(88L);
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(88L)).thenReturn(version);

        TradePromptBinding globalBinding = new TradePromptBinding();
        globalBinding.setId(20L);
        globalBinding.setBindingScope("SUPERVISOR");
        globalBinding.setTemplateCode("trade.supervisor.global");
        globalBinding.setPriority(5);
        globalBinding.setEnabled(Boolean.TRUE);

        TradePromptBinding exactBinding = new TradePromptBinding();
        exactBinding.setId(21L);
        exactBinding.setStrategyId(88L);
        exactBinding.setStrategyVersionId(188L);
        exactBinding.setSymbol("BTCUSDT");
        exactBinding.setExchangeCode("BINANCE");
        exactBinding.setBindingScope("SUPERVISOR");
        exactBinding.setTemplateCode("trade.supervisor.exact");
        exactBinding.setPriority(50);
        exactBinding.setEnabled(Boolean.TRUE);

        when(tradePromptBindingMapper.selectTradePromptBindingList(any(TradePromptBinding.class)))
            .thenReturn(List.of(globalBinding, exactBinding));

        TradeAgentProfile supervisorProfile = new TradeAgentProfile();
        supervisorProfile.setId(31L);
        supervisorProfile.setAgentCode("supervisor_agent");
        supervisorProfile.setEnabled(Boolean.TRUE);
        when(tradeAgentProfileMapper.selectTradeAgentProfileList(any(TradeAgentProfile.class)))
            .thenReturn(List.of(supervisorProfile));

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getPromptBindings())
            .extracting(TradePromptBinding::getId, TradePromptBinding::getTemplateCode)
            .containsExactly(
                org.assertj.core.groups.Tuple.tuple(20L, "trade.supervisor.global"),
                org.assertj.core.groups.Tuple.tuple(21L, "trade.supervisor.exact")
            );
    }

    @Test
    void getBootstrapConfigFallsBackToFirstScopeWhenNoPreferredSymbolOrExchangeIsProvided() {
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(null);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(9L);
        strategy.setStrategyKey("multi-scope");
        strategy.setRuntimeMode(TradeRuntimeMode.PAPER);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope firstScope = new TradeSymbolScope();
        firstScope.setStrategyId(9L);
        firstScope.setSymbol("ETHUSDT");
        firstScope.setExchangeCode("okx");

        TradeSymbolScope secondScope = new TradeSymbolScope();
        secondScope.setStrategyId(9L);
        secondScope.setSymbol("BTCUSDT");
        secondScope.setExchangeCode("binance");
        when(tradeStrategyMapper.selectTradeSymbolScopes(9L)).thenReturn(List.of(firstScope, secondScope));

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig(null, null);

        assertThat(bootstrap.getRuntimeConfig().getDefaultMode()).isEqualTo(TradeRuntimeMode.PAPER);
        assertThat(bootstrap.getRuntimeConfig().getLiveEnabled()).isFalse();
        assertThat(bootstrap.getSymbolScope().getSymbol()).isEqualTo("ETHUSDT");
        assertThat(bootstrap.getSymbolScope().getExchangeCode()).isEqualTo("okx");
    }

    @Test
    void getBootstrapConfigFallbackDoesNotExposeRequestedScopeOutsideV1Whitelist() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.PAPER);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of());

        MarketDataConfig fallbackMarketDataConfig = new MarketDataConfig();
        fallbackMarketDataConfig.setId(401L);
        fallbackMarketDataConfig.setSymbol("BTCUSDT");
        fallbackMarketDataConfig.setEnabled("1");
        when(marketDataConfigService.selectEnabledConfigs()).thenReturn(List.of(fallbackMarketDataConfig));

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("XRPUSDT", "kraken");

        assertThat(bootstrap.getSymbolScope()).isNull();
        assertThat(bootstrap.getMarketDataConfig()).isNotNull();
        assertThat(bootstrap.getMarketDataConfig().getSymbol()).isEqualTo("BTCUSDT");
        verify(marketDataConfigService, never()).selectConfigBySymbol("XRPUSDT");
        verify(tradeExecutionMapper, never()).selectLatestActivePositionSnapshotByScope("kraken", "XRPUSDT");
        verify(tradeExecutionMapper, never()).selectRecentExchangeOrdersByScope("kraken", "XRPUSDT", 10);
    }

    @Test
    void listBootstrapConfigsReturnsAllEnabledScopedRoutesWithResolvedAccounts() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(13L);
        strategy.setStrategyKey("multi-route");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope btcScope = new TradeSymbolScope();
        btcScope.setStrategyId(13L);
        btcScope.setSymbol("BTCUSDT");
        btcScope.setExchangeCode("binance");
        TradeSymbolScope ethScope = new TradeSymbolScope();
        ethScope.setStrategyId(13L);
        ethScope.setSymbol("ETHUSDT");
        ethScope.setExchangeCode("okx");
        when(tradeStrategyMapper.selectTradeSymbolScopes(13L)).thenReturn(List.of(btcScope, ethScope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(13L);
        version.setVersionNo(4);
        version.setConfigJson("{\"riskBudget\":0.02}");
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(13L)).thenReturn(version);

        ExchangeAccountBinding binanceBinding = new ExchangeAccountBinding();
        binanceBinding.setStrategyId(13L);
        binanceBinding.setAccountId(31L);
        binanceBinding.setExchangeCode("binance");
        binanceBinding.setEnabled(Boolean.TRUE);

        ExchangeAccountBinding okxBinding = new ExchangeAccountBinding();
        okxBinding.setStrategyId(13L);
        okxBinding.setAccountId(32L);
        okxBinding.setExchangeCode("okx");
        okxBinding.setEnabled(Boolean.TRUE);
        when(tradeStrategyMapper.selectExchangeAccountBindings(13L)).thenReturn(List.of(binanceBinding, okxBinding));

        ExchangeAccount binanceAccount = new ExchangeAccount();
        binanceAccount.setId(31L);
        binanceAccount.setExchangeCode("binance");
        binanceAccount.setAccountName("binance-main");
        binanceAccount.setEnabled(Boolean.TRUE);
        when(exchangeAccountMapper.selectExchangeAccountById(31L)).thenReturn(binanceAccount);

        ExchangeAccount okxAccount = new ExchangeAccount();
        okxAccount.setId(32L);
        okxAccount.setExchangeCode("okx");
        okxAccount.setAccountName("okx-main");
        okxAccount.setEnabled(Boolean.TRUE);
        when(exchangeAccountMapper.selectExchangeAccountById(32L)).thenReturn(okxAccount);

        List<TradeRuntimeBootstrap> bootstraps = tradeRuntimeConfigService.listBootstrapConfigs();

        assertThat(bootstraps).hasSize(2);
        assertThat(bootstraps)
            .extracting(item -> item.getSymbolScope().getSymbol(), item -> item.getSymbolScope().getExchangeCode())
            .containsExactly(
                org.assertj.core.groups.Tuple.tuple("BTCUSDT", "binance"),
                org.assertj.core.groups.Tuple.tuple("ETHUSDT", "okx")
            );
        assertThat(bootstraps)
            .extracting(item -> item.getExchangeAccount().getAccountName())
            .containsExactly("binance-main", "okx-main");
        assertThat(bootstraps)
            .extracting(item -> item.getStrategyVersion().getVersionNo())
            .containsOnly(4);
    }

    @Test
    void getBootstrapConfigResolvesStrategyManagedConfigReferencesWithoutOverridingRuntimeRiskLimits() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.PAPER);
        config.setLiveEnabled(Boolean.TRUE);
        config.setMaxPositionRatio(new java.math.BigDecimal("0.40"));
        config.setMaxDailyLoss(new java.math.BigDecimal("-500.00"));
        config.setMaxConsecutiveFailures(3);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(21L);
        strategy.setStrategyKey("btc-live");
        strategy.setRuntimeMode(TradeRuntimeMode.LIVE);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(21L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("binance");
        when(tradeStrategyMapper.selectTradeSymbolScopes(21L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(21L);
        version.setVersionNo(6);
        version.setConfigJson("""
            {
              "aiModelId": 901,
              "marketDataConfigId": 902,
              "newsApiConfigId": 903,
              "onchainApiConfigId": 904,
              "socialApiConfigId": 905,
              "riskConfig": {
                "maxPositionRatio": 0.22,
                "maxDailyLoss": -320.5,
                "maxConsecutiveFailures": 7
              }
            }
            """);
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(21L)).thenReturn(version);

        AiModelConfig aiModelConfig = new AiModelConfig();
        aiModelConfig.setId(901L);
        aiModelConfig.setModelCode("gpt-4.1-mini");
        aiModelConfig.setIsEnabled(1);
        when(aiModelConfigService.selectAiModelConfigById(901L)).thenReturn(aiModelConfig);
        when(aiModelConfigService.getDefaultModel()).thenReturn(new AiModelConfig());

        MarketDataConfig marketDataConfig = new MarketDataConfig();
        marketDataConfig.setId(902L);
        marketDataConfig.setSymbol("BTCUSDT");
        marketDataConfig.setEnabled("1");
        when(marketDataConfigService.selectConfigById(902L)).thenReturn(marketDataConfig);

        MarketApiConfig newsApi = new MarketApiConfig();
        newsApi.setId(903L);
        newsApi.setEnabled("1");
        newsApi.setDataCategory("NEWS");
        newsApi.setApiUrl("https://runtime/news");
        when(marketApiConfigService.selectApiConfigById(903L)).thenReturn(newsApi);

        MarketApiConfig onchainApi = new MarketApiConfig();
        onchainApi.setId(904L);
        onchainApi.setEnabled("1");
        onchainApi.setDataCategory("ONCHAIN");
        onchainApi.setApiUrl("https://runtime/onchain");
        when(marketApiConfigService.selectApiConfigById(904L)).thenReturn(onchainApi);

        MarketApiConfig socialApi = new MarketApiConfig();
        socialApi.setId(905L);
        socialApi.setEnabled("1");
        socialApi.setDataCategory("SOCIAL");
        socialApi.setApiUrl("https://runtime/social");
        when(marketApiConfigService.selectApiConfigById(905L)).thenReturn(socialApi);

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getRuntimeConfig().getDefaultMode()).isEqualTo(TradeRuntimeMode.LIVE);
        assertThat(bootstrap.getRuntimeConfig().getMaxPositionRatio()).isEqualByComparingTo("0.40");
        assertThat(bootstrap.getRuntimeConfig().getMaxDailyLoss()).isEqualByComparingTo("-500.00");
        assertThat(bootstrap.getRuntimeConfig().getMaxConsecutiveFailures()).isEqualTo(3);
        assertThat(bootstrap.getAiModelConfig().getId()).isEqualTo(901L);
        assertThat(bootstrap.getMarketDataConfig().getId()).isEqualTo(902L);
        assertThat(bootstrap.getNewsApiConfig().getId()).isEqualTo(903L);
        assertThat(bootstrap.getOnchainApiConfig().getId()).isEqualTo(904L);
        assertThat(bootstrap.getSocialApiConfig().getId()).isEqualTo(905L);
    }

    @Test
    void getBootstrapConfigFallsBackToLatestStrategyScopedPromptBindingsWhenOnlyOlderVersionBindingsExist() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(96L);
        strategy.setStrategyKey("stale-binding-fallback");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(96L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("BINANCE");
        when(tradeStrategyMapper.selectTradeSymbolScopes(96L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setId(296L);
        version.setStrategyId(96L);
        version.setVersionNo(4);
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(96L)).thenReturn(version);

        TradePromptBinding staleSupervisorBinding = new TradePromptBinding();
        staleSupervisorBinding.setId(61L);
        staleSupervisorBinding.setStrategyId(96L);
        staleSupervisorBinding.setStrategyVersionId(193L);
        staleSupervisorBinding.setSymbol("BTCUSDT");
        staleSupervisorBinding.setExchangeCode("BINANCE");
        staleSupervisorBinding.setBindingScope("SUPERVISOR");
        staleSupervisorBinding.setTemplateCode("trade.supervisor.v1");
        staleSupervisorBinding.setEnabled(Boolean.TRUE);

        TradePromptBinding staleMarketBinding = new TradePromptBinding();
        staleMarketBinding.setId(62L);
        staleMarketBinding.setStrategyId(96L);
        staleMarketBinding.setStrategyVersionId(193L);
        staleMarketBinding.setSymbol("BTCUSDT");
        staleMarketBinding.setExchangeCode("BINANCE");
        staleMarketBinding.setBindingScope("MARKET_AGENT");
        staleMarketBinding.setTemplateCode("trade.market.v1");
        staleMarketBinding.setEnabled(Boolean.TRUE);

        when(tradePromptBindingMapper.selectTradePromptBindingList(any(TradePromptBinding.class)))
            .thenReturn(List.of(staleSupervisorBinding, staleMarketBinding));

        TradeAgentProfile supervisorProfile = new TradeAgentProfile();
        supervisorProfile.setId(71L);
        supervisorProfile.setAgentCode("supervisor_agent");
        supervisorProfile.setEnabled(Boolean.TRUE);
        supervisorProfile.setSpeakOrder(1);

        TradeAgentProfile marketProfile = new TradeAgentProfile();
        marketProfile.setId(72L);
        marketProfile.setAgentCode("market_agent");
        marketProfile.setEnabled(Boolean.TRUE);
        marketProfile.setSpeakOrder(2);

        when(tradeAgentProfileMapper.selectTradeAgentProfileList(any(TradeAgentProfile.class)))
            .thenReturn(List.of(supervisorProfile, marketProfile));

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getPromptBindings())
            .extracting(TradePromptBinding::getId)
            .containsExactly(61L, 62L);
        assertThat(bootstrap.getAgentProfiles())
            .extracting(TradeAgentProfile::getAgentCode)
            .containsExactly("supervisor_agent", "market_agent");
    }

    @Test
    void getBootstrapConfigResolvesMarketSourceConfigFromEnabledBinding() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(61L);
        strategy.setStrategyKey("btc-market-route");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(61L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("binance");
        when(tradeStrategyMapper.selectTradeSymbolScopes(61L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(61L);
        version.setVersionNo(2);
        version.setConfigJson("{\"riskBudget\":0.02}");
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(61L)).thenReturn(version);

        TradeDataSourceBinding binding = new TradeDataSourceBinding();
        binding.setId(701L);
        binding.setBindingName("binance-market");
        binding.setStrategyId(61L);
        binding.setSourceId(801L);
        binding.setEventType("market_tick");
        binding.setSymbolScopeJson("[\"BTCUSDT\"]");
        binding.setExchangeScopeJson("[\"BINANCE\"]");
        binding.setModeScopeJson("[\"shadow\"]");
        binding.setEnabled(Boolean.TRUE);
        when(tradeDataSourceBindingMapper.selectTradeDataSourceBindingList(any(TradeDataSourceBinding.class)))
            .thenReturn(List.of(binding));

        MarketApiConfig marketApiConfig = new MarketApiConfig();
        marketApiConfig.setId(801L);
        marketApiConfig.setEnabled("1");
        marketApiConfig.setVersionNo(7);
        marketApiConfig.setDataCategory("PRICE");
        marketApiConfig.setTransportType("WEBSOCKET");
        marketApiConfig.setVendorCode("BINANCE");
        marketApiConfig.setApiName("BINANCE_FUTURES_TICKER_WS");
        marketApiConfig.setMarketScope("FUTURES");
        marketApiConfig.setWsBaseUrl("wss://fstream.binance.com");
        marketApiConfig.setWsPath("/stream");
        marketApiConfig.setWsStreamNameTemplate("{symbol_lower}@ticker");
        marketApiConfig.setWsCombinedEnabled(Boolean.TRUE);
        marketApiConfig.setWsSymbolLowercase(Boolean.TRUE);
        marketApiConfig.setWsPingIntervalSeconds(20);
        marketApiConfig.setWsPongTimeoutSeconds(60);
        marketApiConfig.setWsConnectionTtlHours(24);
        marketApiConfig.setWsMaxStreamsPerConnection(1024);
        marketApiConfig.setWsControlMessagesPerSecond(5);
        marketApiConfig.setUpdateTime(new Date(1760667300000L));
        when(marketApiConfigService.selectApiConfigById(801L)).thenReturn(marketApiConfig);

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getMarketApiConfig()).isNotNull();
        assertThat(bootstrap.getMarketApiConfig().getId()).isEqualTo(801L);
        assertThat(bootstrap.getMarketApiConfig().getVersionNo()).isEqualTo(7);
        assertThat(bootstrap.getMarketApiConfig().getTransportType()).isEqualTo("WEBSOCKET");
        assertThat(bootstrap.getMarketApiConfig().getVendorCode()).isEqualTo("BINANCE");
        assertThat(bootstrap.getMarketApiConfig().getMarketScope()).isEqualTo("FUTURES");
        assertThat(bootstrap.getMarketApiConfig().getWsBaseUrl()).isEqualTo("wss://fstream.binance.com");
        assertThat(bootstrap.getMarketApiConfig().getWsPath()).isEqualTo("/stream");
        assertThat(bootstrap.getMarketApiConfig().getWsConnectionTtlHours()).isEqualTo(24);
        assertThat(bootstrap.getMarketApiConfig().getUpdateTime()).isNotNull();
    }

    @Test
    void getBootstrapConfigIncludesRuntimeAccountContextFromSnapshotsAndOrders() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(81L);
        strategy.setStrategyKey("btc-runtime-context");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(81L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("binance");
        when(tradeStrategyMapper.selectTradeSymbolScopes(81L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(81L);
        version.setVersionNo(2);
        version.setConfigJson("{\"riskBudget\":0.02}");
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(81L)).thenReturn(version);

        PnlSnapshot pnlSnapshot = new PnlSnapshot();
        pnlSnapshot.setAccountEquity(new java.math.BigDecimal("12500.50"));
        pnlSnapshot.setDailyPnl(new java.math.BigDecimal("235.10"));
        pnlSnapshot.setRealizedPnl(new java.math.BigDecimal("180.25"));
        pnlSnapshot.setUnrealizedPnl(new java.math.BigDecimal("-12.75"));
        pnlSnapshot.setMaxDrawdownPct(new java.math.BigDecimal("4.25"));
        pnlSnapshot.setPeakAccountEquity(new java.math.BigDecimal("13055.75"));
        when(tradeExecutionMapper.selectLatestPnlSnapshotByMode("shadow")).thenReturn(pnlSnapshot);

        PositionSnapshot positionSnapshot = new PositionSnapshot();
        positionSnapshot.setSide("long");
        positionSnapshot.setPositionQuantity(new java.math.BigDecimal("0.25000000"));
        positionSnapshot.setEntryPrice(new java.math.BigDecimal("64000.00"));
        positionSnapshot.setTraceId("trace-reduce-1");
        positionSnapshot.setEntryTraceId("trace-open-1");
        when(tradeExecutionMapper.selectLatestActivePositionSnapshotByScope("binance", "BTCUSDT")).thenReturn(positionSnapshot);

        ExchangeOrder failedOrder = new ExchangeOrder();
        failedOrder.setStatus("failed");
        ExchangeOrder failedOrder2 = new ExchangeOrder();
        failedOrder2.setStatus("failed");
        ExchangeOrder filledOrder = new ExchangeOrder();
        filledOrder.setStatus("filled");
        when(tradeExecutionMapper.selectRecentExchangeOrdersByScope("binance", "BTCUSDT", 10))
            .thenReturn(List.of(failedOrder, failedOrder2, filledOrder));

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getRuntimeAccountContext()).isNotNull();
        TradeRuntimeAccountContext context = bootstrap.getRuntimeAccountContext();
        assertThat(context.getAccountEquity()).isEqualByComparingTo("12500.50");
        assertThat(context.getDailyPnl()).isEqualByComparingTo("235.10");
        assertThat(context.getRealizedPnl()).isEqualByComparingTo("180.25");
        assertThat(context.getUnrealizedPnl()).isEqualByComparingTo("-12.75");
        assertThat(context.getCurrentPositionSide()).isEqualTo("long");
        assertThat(context.getCurrentPositionQuantity()).isEqualByComparingTo("0.25000000");
        assertThat(context.getCurrentPositionNotional()).isEqualByComparingTo("16000.0000000000");
        assertThat(context.getEntryPrice()).isEqualByComparingTo("64000.00");
        assertThat(context.getMaxDrawdownPct()).isEqualByComparingTo("4.25");
        assertThat(context.getPeakAccountEquity()).isEqualByComparingTo("13055.75");
        assertThat(context.getEntryTraceId()).isEqualTo("trace-open-1");
        assertThat(context.getConsecutiveFailures()).isEqualTo(2);
    }

    @Test
    void getBootstrapConfigResetsStaleDailyPnlFromPreviousUtcDay() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(811L);
        strategy.setStrategyKey("btc-runtime-context-stale-pnl");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(811L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("binance");
        when(tradeStrategyMapper.selectTradeSymbolScopes(811L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(811L);
        version.setVersionNo(1);
        version.setConfigJson("{\"riskBudget\":0.02}");
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(811L)).thenReturn(version);

        PnlSnapshot pnlSnapshot = new PnlSnapshot();
        pnlSnapshot.setAccountEquity(new java.math.BigDecimal("12500.50"));
        pnlSnapshot.setDailyPnl(new java.math.BigDecimal("235.10"));
        pnlSnapshot.setRealizedPnl(new java.math.BigDecimal("180.25"));
        pnlSnapshot.setUnrealizedPnl(new java.math.BigDecimal("-12.75"));
        pnlSnapshot.setMaxDrawdownPct(new java.math.BigDecimal("4.25"));
        pnlSnapshot.setPeakAccountEquity(new java.math.BigDecimal("13055.75"));
        pnlSnapshot.setCreatedAt("2000-01-01 23:59:59");
        when(tradeExecutionMapper.selectLatestPnlSnapshotByMode("shadow")).thenReturn(pnlSnapshot);
        when(tradeExecutionMapper.selectRecentExchangeOrdersByScope("binance", "BTCUSDT", 10)).thenReturn(List.of());

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getRuntimeAccountContext()).isNotNull();
        TradeRuntimeAccountContext context = bootstrap.getRuntimeAccountContext();
        assertThat(context.getAccountEquity()).isEqualByComparingTo("12500.50");
        assertThat(context.getDailyPnl()).isEqualByComparingTo("0");
        assertThat(context.getRealizedPnl()).isEqualByComparingTo("180.25");
        assertThat(context.getUnrealizedPnl()).isEqualByComparingTo("-12.75");
        assertThat(context.getMaxDrawdownPct()).isEqualByComparingTo("4.25");
        assertThat(context.getPeakAccountEquity()).isEqualByComparingTo("13055.75");
    }

    @Test
    void getBootstrapConfigIncludesPositionGuardAndCurrentPositionOpenedAt() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(82L);
        strategy.setStrategyKey("btc-position-guard");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(82L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("binance");
        when(tradeStrategyMapper.selectTradeSymbolScopes(82L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(82L);
        version.setVersionNo(1);
        version.setConfigJson("{\"riskBudget\":0.02}");
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(82L)).thenReturn(version);

        PositionSnapshot positionSnapshot = new PositionSnapshot();
        positionSnapshot.setSide("long");
        positionSnapshot.setPositionQuantity(new java.math.BigDecimal("0.12000000"));
        positionSnapshot.setEntryPrice(new java.math.BigDecimal("65000.00"));
        when(tradeExecutionMapper.selectLatestActivePositionSnapshotByScope("binance", "BTCUSDT")).thenReturn(positionSnapshot);
        when(tradeExecutionMapper.selectRecentExchangeOrdersByScope("binance", "BTCUSDT", 10)).thenReturn(List.of());

        TradePositionGuard positionGuard = new TradePositionGuard();
        positionGuard.setId(301L);
        positionGuard.setGuardName("btc-default-guard");
        positionGuard.setScopeType("SYMBOL");
        positionGuard.setStrategyId(82L);
        positionGuard.setSymbol("BTCUSDT");
        positionGuard.setExchangeCode("BINANCE");
        positionGuard.setStopLossPct(new java.math.BigDecimal("0.02"));
        positionGuard.setTakeProfitPct(new java.math.BigDecimal("0.05"));
        positionGuard.setMaxHoldingMinutes(180);
        positionGuard.setEnabled(Boolean.TRUE);
        when(tradePositionGuardMapper.selectEffectiveGuard(82L, "BTCUSDT", "binance")).thenReturn(positionGuard);
        when(tradePositionGuardMapper.selectCurrentPositionOpenedAt("binance", "BTCUSDT", "long"))
            .thenReturn("2026-04-21 09:15:00");

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getPositionGuard()).isNotNull();
        assertThat(bootstrap.getPositionGuard().getGuardName()).isEqualTo("btc-default-guard");
        assertThat(bootstrap.getPositionGuard().getStopLossPct()).isEqualByComparingTo("0.02");
        assertThat(bootstrap.getPositionGuard().getTakeProfitPct()).isEqualByComparingTo("0.05");
        assertThat(bootstrap.getPositionGuard().getMaxHoldingMinutes()).isEqualTo(180);
        assertThat(bootstrap.getRuntimeAccountContext().getCurrentPositionOpenedAt()).isEqualTo("2026-04-21 09:15:00");
        assertThat(bootstrap.getRuntimeAccountContext().getCurrentTime()).isNotBlank();
        assertThat(bootstrap.getRuntimeAccountContext().getCurrentPositionHoldingMinutes()).isNotNull();
        assertThat(bootstrap.getRuntimeAccountContext().getCurrentPositionHoldingMinutes()).isGreaterThanOrEqualTo(0);
    }

    @Test
    void getBootstrapConfigFallsBackToPositionSnapshotCreatedAtWhenOpenedAtQueryIsEmpty() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(82L);
        strategy.setStrategyKey("btc-position-guard-fallback");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(82L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("binance");
        when(tradeStrategyMapper.selectTradeSymbolScopes(82L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(82L);
        version.setVersionNo(1);
        version.setConfigJson("{\"riskBudget\":0.02}");
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(82L)).thenReturn(version);

        PositionSnapshot positionSnapshot = new PositionSnapshot();
        positionSnapshot.setSide("short");
        positionSnapshot.setPositionQuantity(new java.math.BigDecimal("0.42482978"));
        positionSnapshot.setEntryPrice(new java.math.BigDecimal("2356.04"));
        positionSnapshot.setCreatedAt("2026-05-06 13:41:01");
        when(tradeExecutionMapper.selectLatestActivePositionSnapshotByScope("binance", "BTCUSDT")).thenReturn(positionSnapshot);
        when(tradeExecutionMapper.selectRecentExchangeOrdersByScope("binance", "BTCUSDT", 10)).thenReturn(List.of());

        TradePositionGuard positionGuard = new TradePositionGuard();
        positionGuard.setId(301L);
        positionGuard.setGuardName("btc-default-guard");
        positionGuard.setScopeType("SYMBOL");
        positionGuard.setStrategyId(82L);
        positionGuard.setSymbol("BTCUSDT");
        positionGuard.setExchangeCode("BINANCE");
        positionGuard.setStopLossPct(new java.math.BigDecimal("0.02"));
        positionGuard.setTakeProfitPct(new java.math.BigDecimal("0.05"));
        positionGuard.setMaxHoldingMinutes(180);
        positionGuard.setEnabled(Boolean.TRUE);
        when(tradePositionGuardMapper.selectEffectiveGuard(82L, "BTCUSDT", "binance")).thenReturn(positionGuard);
        when(tradePositionGuardMapper.selectCurrentPositionOpenedAt("binance", "BTCUSDT", "short")).thenReturn(null);

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getRuntimeAccountContext().getCurrentPositionOpenedAt()).isEqualTo("2026-05-06 13:41:01");
        assertThat(bootstrap.getRuntimeAccountContext().getCurrentTime()).isNotBlank();
        assertThat(bootstrap.getRuntimeAccountContext().getCurrentPositionHoldingMinutes()).isNotNull();
    }

    @Test
    void getBootstrapConfigTreatsZeroQuantityPositionSnapshotAsFlat() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(83L);
        strategy.setStrategyKey("btc-position-closed");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(83L);
        scope.setSymbol("ETHUSDT");
        scope.setExchangeCode("okx");
        when(tradeStrategyMapper.selectTradeSymbolScopes(83L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(83L);
        version.setVersionNo(1);
        version.setConfigJson("{\"riskBudget\":0.02}");
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(83L)).thenReturn(version);

        PositionSnapshot positionSnapshot = new PositionSnapshot();
        positionSnapshot.setSide("short");
        positionSnapshot.setPositionQuantity(new java.math.BigDecimal("0.00000000"));
        positionSnapshot.setEntryPrice(new java.math.BigDecimal("0.00000000"));
        positionSnapshot.setCreatedAt("2026-05-07 09:10:14");
        when(tradeExecutionMapper.selectLatestActivePositionSnapshotByScope("okx", "ETHUSDT")).thenReturn(positionSnapshot);
        when(tradeExecutionMapper.selectRecentExchangeOrdersByScope("okx", "ETHUSDT", 10)).thenReturn(List.of());

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("ETHUSDT", "okx");

        TradeRuntimeAccountContext context = bootstrap.getRuntimeAccountContext();
        assertThat(context.getCurrentPositionSide()).isEqualTo("flat");
        assertThat(context.getCurrentPositionQuantity()).isEqualByComparingTo("0.00000000");
        assertThat(context.getCurrentPositionOpenedAt()).isNull();
        assertThat(context.getCurrentPositionHoldingMinutes()).isNull();
    }

    @Test
    void getBootstrapConfigSkipsUnhealthyExecutionAccountWhenLiveRequiresValidatedAccount() {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.LIVE);
        config.setLiveEnabled(Boolean.TRUE);
        config.setLiveOrderRequiresHealthyAccount(Boolean.TRUE);
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(91L);
        strategy.setStrategyKey("btc-live-unhealthy-account");
        strategy.setRuntimeMode(TradeRuntimeMode.LIVE);
        when(tradeStrategyMapper.selectTradeStrategyList(any(TradeStrategy.class))).thenReturn(List.of(strategy));

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(91L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("binance");
        when(tradeStrategyMapper.selectTradeSymbolScopes(91L)).thenReturn(List.of(scope));

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(91L);
        version.setVersionNo(1);
        version.setConfigJson("{\"riskBudget\":0.02}");
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(91L)).thenReturn(version);

        ExchangeAccountBinding binding = new ExchangeAccountBinding();
        binding.setStrategyId(91L);
        binding.setAccountId(41L);
        binding.setExchangeCode("binance");
        binding.setEnabled(Boolean.TRUE);
        when(tradeStrategyMapper.selectExchangeAccountBindings(91L)).thenReturn(List.of(binding));

        ExchangeAccount unhealthyAccount = new ExchangeAccount();
        unhealthyAccount.setId(41L);
        unhealthyAccount.setExchangeCode("binance");
        unhealthyAccount.setAccountName("binance-live");
        unhealthyAccount.setEnabled(Boolean.TRUE);
        unhealthyAccount.setHealthStatus("degraded");
        unhealthyAccount.setLastValidatedAt(new Date());
        when(exchangeAccountMapper.selectExchangeAccountById(41L)).thenReturn(unhealthyAccount);

        TradeRuntimeBootstrap bootstrap = tradeRuntimeConfigService.getBootstrapConfig("BTCUSDT", "binance");

        assertThat(bootstrap.getRuntimeConfig().getDefaultMode()).isEqualTo(TradeRuntimeMode.LIVE);
        assertThat(bootstrap.getExchangeAccountBinding()).isNull();
        assertThat(bootstrap.getExchangeAccount()).isNull();
    }

    @Test
    void saveCurrentConfigNormalizesSpecsManagedWhitelistAndSafetyFields() {
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(null);
        when(tradeRuntimeConfigMapper.insertTradeRuntimeConfig(any(TradeRuntimeConfig.class))).thenReturn(1);

        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.LIVE);
        config.setLiveEnabled(Boolean.TRUE);
        config.setAllowedSymbolsJson("[\" solusdt \",\"BTCUSDT\",\"ethusdt\"]");
        config.setAllowedExchangesJson("[\"okx\",\" BINANCE \"]");
        config.setRequireAccountBinding(Boolean.TRUE);
        config.setLiveOrderRequiresHealthyAccount(Boolean.TRUE);
        config.setRuntimeFlagsJson("{\"haltOnDataGap\":true}");
        config.setNotifyDefaultsJson("{\"channels\":[\"OPS\"]}");
        config.setEventRetentionDays(45);
        config.setReplayRetentionDays(14);
        config.setRouteMaxConcurrency(3);
        config.setRouteSchedulerMode("THREAD_POOL");

        tradeRuntimeConfigService.saveCurrentConfig(config);

        assertThat(config.getAllowedSymbolsJson()).isEqualTo("[\"SOLUSDT\",\"BTCUSDT\",\"ETHUSDT\"]");
        assertThat(config.getAllowedExchangesJson()).isEqualTo("[\"OKX\",\"BINANCE\"]");
        assertThat(config.getRequireAccountBinding()).isTrue();
        assertThat(config.getLiveOrderRequiresHealthyAccount()).isTrue();
        assertThat(config.getRuntimeFlagsJson()).contains("\"haltOnDataGap\":true");
        assertThat(config.getRuntimeFlagsJson()).contains("\"triggerMode\":\"EVENT_GATED\"");
        assertThat(config.getTriggerMode()).isEqualTo("EVENT_GATED");
        assertThat(config.getNotifyDefaultsJson()).isEqualTo("{\"channels\":[\"OPS\"]}");
        assertThat(config.getEventRetentionDays()).isEqualTo(45);
        assertThat(config.getReplayRetentionDays()).isEqualTo(14);
        assertThat(config.getRouteMaxConcurrency()).isEqualTo(3);
        assertThat(config.getRouteSchedulerMode()).isEqualTo("THREAD_POOL");
        verify(tradeRuntimeConfigMapper).insertTradeRuntimeConfig(config);
    }

    @Test
    void saveCurrentConfigRejectsSymbolsOutsideSpecsWhitelist() {
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(null);

        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setAllowedSymbolsJson("[\"BTCUSDT\",\"XRPUSDT\"]");
        config.setAllowedExchangesJson("[\"BINANCE\"]");

        assertThatThrownBy(() -> tradeRuntimeConfigService.saveCurrentConfig(config))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("XRPUSDT");
    }

    @Test
    void saveCurrentConfigNormalizesEventGatedRuntimePolicyAndBootstrapExposesStructuredPolicy() {
        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(null);
        when(tradeRuntimeConfigMapper.insertTradeRuntimeConfig(any(TradeRuntimeConfig.class))).thenReturn(1);

        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.SHADOW);
        config.setLiveEnabled(Boolean.FALSE);
        config.setRuntimeFlagsJson("""
            {
              "cooldownPolicy": {
                "globalSeconds": 180
              },
              "llmBudgetPolicy": {
                "perSymbolDailyLimit": 4
              }
            }
            """);

        tradeRuntimeConfigService.saveCurrentConfig(config);

        when(tradeRuntimeConfigMapper.selectCurrentConfig()).thenReturn(config);

        assertThat(config.getRuntimeFlagsJson()).contains("\"triggerMode\":\"EVENT_GATED\"");
        assertThat(config.getRuntimeFlagsJson()).contains("\"marketTrigger\"");
        assertThat(config.getRuntimeFlagsJson()).contains("\"newsTrigger\"");
        assertThat(config.getRuntimeFlagsJson()).contains("\"onchainTrigger\"");
        assertThat(config.getRuntimeFlagsJson()).contains("\"socialTrigger\"");
        assertThat(config.getRuntimeFlagsJson()).contains("\"signalMemoryPolicy\"");
        assertThat(config.getRuntimeFlagsJson()).contains("\"triggerMatrix\"");
        assertThat(config.getRuntimeFlagsJson()).contains("\"dedupePolicy\"");
        assertThat(config.getRuntimeFlagsJson()).contains("\"globalSeconds\":180");
        assertThat(config.getRuntimeFlagsJson()).contains("\"perSymbolDailyLimit\":4");
        assertThat(config.getTriggerMode()).isEqualTo("EVENT_GATED");
        assertThat(config.getSignalMemoryPolicy()).containsKeys("market", "news", "onchain", "social");
        assertThat(config.getLlmBudgetPolicy()).containsEntry("perSymbolDailyLimit", 4);

        TradeRuntimeConfig current = tradeRuntimeConfigService.getCurrentConfig();

        assertThat(current.getTriggerMode()).isEqualTo("EVENT_GATED");
        assertThat(current.getMarketTrigger()).containsKeys("priceChangePct", "priceAccelerationPct");
        assertThat(current.getCooldownPolicy()).containsEntry("globalSeconds", 180);
        assertThat(current.getDedupePolicy()).containsKeys("sameDirectionOnly", "dedupeWindowSeconds");
        assertThat(current.getTriggerMatrix()).isNotEmpty();
    }

}
