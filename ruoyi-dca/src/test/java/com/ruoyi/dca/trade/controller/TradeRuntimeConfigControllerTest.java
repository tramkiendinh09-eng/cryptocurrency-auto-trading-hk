package com.ruoyi.dca.trade.controller;

import com.ruoyi.dca.controller.trade.TradeRuntimeConfigController;
import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.domain.MarketDataConfig;
import com.ruoyi.dca.domain.MarketApiConfig;
import com.ruoyi.dca.domain.enums.TradeRuntimeMode;
import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.decision.SignalWindowState;
import com.ruoyi.dca.domain.trade.ExchangeAccount;
import com.ruoyi.dca.domain.trade.ExchangeAccountBinding;
import com.ruoyi.dca.domain.trade.RuntimeModelCallResponse;
import com.ruoyi.dca.domain.trade.TradeRuntimeAccountContext;
import com.ruoyi.dca.domain.trade.TradeRuntimeBootstrap;
import com.ruoyi.dca.domain.trade.TradeRuntimeConfig;
import com.ruoyi.dca.domain.trade.TradeRuntimeOverview;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.domain.trade.TradeStrategyVersion;
import com.ruoyi.dca.domain.trade.TradeSymbolScope;
import com.ruoyi.dca.service.IAiModelConfigService;
import com.ruoyi.dca.service.trade.ITradeRuntimeOverviewService;
import com.ruoyi.dca.service.trade.ITradeRuntimeConfigService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.util.Date;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(TradeRuntimeConfigController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {TradeRuntimeConfigControllerTest.TestApplication.class, TradeRuntimeConfigController.class})
class TradeRuntimeConfigControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ITradeRuntimeConfigService runtimeConfigService;

    @MockBean
    private ITradeRuntimeOverviewService tradeRuntimeOverviewService;

    @MockBean
    private IAiModelConfigService aiModelConfigService;

    @Test
    void getRuntimeConfigReturnsPaperShadowLiveShape() throws Exception {
        TradeRuntimeConfig config = new TradeRuntimeConfig();
        config.setDefaultMode(TradeRuntimeMode.PAPER);
        config.setLiveEnabled(Boolean.FALSE);
        config.setMaxPositionRatio(new BigDecimal("0.40"));
        config.setMaxDailyLoss(new BigDecimal("-500.00"));
        config.setMaxConsecutiveFailures(3);
        config.setAllowedSymbolsJson("[\"BTCUSDT\",\"ETHUSDT\",\"SOLUSDT\"]");
        config.setAllowedExchangesJson("[\"BINANCE\",\"OKX\"]");
        config.setRequireAccountBinding(Boolean.TRUE);
        config.setLiveOrderRequiresHealthyAccount(Boolean.TRUE);
        config.setRuntimeFlagsJson("{\"haltOnDataGap\":true}");
        config.setNotifyDefaultsJson("{\"channels\":[\"OPS\"]}");
        config.setEventRetentionDays(30);
        config.setReplayRetentionDays(30);
        config.setRouteSchedulerMode("THREAD_POOL");
        config.setRouteMaxConcurrency(3);
        config.setDeliberationEnabled(Boolean.TRUE);
        config.setDeliberationMaxRounds(1);
        config.setDeliberationFailOpen(Boolean.TRUE);
        config.setRuntimeFlagsJson("""
            {
              "triggerMode":"EVENT_GATED",
              "marketTrigger":{"priceChangePct":2.5},
              "newsTrigger":{"scoreThreshold":0.75},
              "onchainTrigger":{"flowUsdThreshold":500000},
              "socialTrigger":{"scoreThreshold":0.7},
              "signalMemoryPolicy":{"news":{"ttlSeconds":900}},
              "triggerMatrix":[{"code":"strong_news_then_break"}],
              "cooldownPolicy":{"globalSeconds":180},
              "llmBudgetPolicy":{"perSymbolDailyLimit":4},
              "dedupePolicy":{"dedupeWindowSeconds":300}
            }
            """);
        when(runtimeConfigService.getCurrentConfig()).thenReturn(config);

        mockMvc.perform(get("/dca/trade/runtime/config"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data.defaultMode").value("PAPER"))
            .andExpect(jsonPath("$.data.liveEnabled").value(false))
            .andExpect(jsonPath("$.data.maxPositionRatio").value(0.40))
            .andExpect(jsonPath("$.data.maxDailyLoss").value(-500.00))
            .andExpect(jsonPath("$.data.maxConsecutiveFailures").value(3))
            .andExpect(jsonPath("$.data.allowedSymbolsJson").value("[\"BTCUSDT\",\"ETHUSDT\",\"SOLUSDT\"]"))
            .andExpect(jsonPath("$.data.allowedExchangesJson").value("[\"BINANCE\",\"OKX\"]"))
            .andExpect(jsonPath("$.data.requireAccountBinding").value(true))
            .andExpect(jsonPath("$.data.liveOrderRequiresHealthyAccount").value(true))
            .andExpect(jsonPath("$.data.runtimeFlagsJson").isString())
            .andExpect(jsonPath("$.data.notifyDefaultsJson").value("{\"channels\":[\"OPS\"]}"))
            .andExpect(jsonPath("$.data.eventRetentionDays").value(30))
            .andExpect(jsonPath("$.data.replayRetentionDays").value(30))
            .andExpect(jsonPath("$.data.routeSchedulerMode").value("THREAD_POOL"))
            .andExpect(jsonPath("$.data.routeMaxConcurrency").value(3))
            .andExpect(jsonPath("$.data.deliberationEnabled").value(true))
            .andExpect(jsonPath("$.data.deliberationMaxRounds").value(1))
            .andExpect(jsonPath("$.data.deliberationFailOpen").value(true))
            .andExpect(jsonPath("$.data.triggerMode").value("EVENT_GATED"))
            .andExpect(jsonPath("$.data.marketTrigger.priceChangePct").value(2.5))
            .andExpect(jsonPath("$.data.signalMemoryPolicy.news.ttlSeconds").value(900))
            .andExpect(jsonPath("$.data.cooldownPolicy.globalSeconds").value(180))
            .andExpect(jsonPath("$.data.llmBudgetPolicy.perSymbolDailyLimit").value(4))
            .andExpect(jsonPath("$.data.dedupePolicy.dedupeWindowSeconds").value(300));
    }

    @Test
    void getBootstrapReturnsSelectedStrategyScopeAndBoundAccount() throws Exception {
        TradeRuntimeBootstrap bootstrap = new TradeRuntimeBootstrap();
        TradeRuntimeConfig runtimeConfig = new TradeRuntimeConfig();
        runtimeConfig.setDefaultMode(TradeRuntimeMode.SHADOW);
        runtimeConfig.setLiveEnabled(Boolean.FALSE);
        bootstrap.setRuntimeConfig(runtimeConfig);

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(9L);
        strategy.setStrategyKey("event-btc");
        strategy.setStrategyName("BTC Event Runtime");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        strategy.setEnabled(Boolean.TRUE);
        bootstrap.setStrategy(strategy);

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setId(11L);
        version.setStrategyId(9L);
        version.setVersionNo(3);
        version.setConfigJson("{\"riskBudget\":0.02}");
        bootstrap.setStrategyVersion(version);

        TradeSymbolScope scope = new TradeSymbolScope();
        scope.setStrategyId(9L);
        scope.setSymbol("BTCUSDT");
        scope.setExchangeCode("binance");
        bootstrap.setSymbolScope(scope);

        ExchangeAccountBinding binding = new ExchangeAccountBinding();
        binding.setStrategyId(9L);
        binding.setAccountId(21L);
        binding.setExchangeCode("binance");
        binding.setEnabled(Boolean.TRUE);
        bootstrap.setExchangeAccountBinding(binding);

        ExchangeAccount account = new ExchangeAccount();
        account.setId(21L);
        account.setExchangeCode("binance");
        account.setAccountName("Primary Binance");
        account.setApiKeyCiphertext("ak-runtime");
        account.setApiSecretCiphertext("sk-runtime");
        account.setTestnet(Boolean.TRUE);
        bootstrap.setExchangeAccount(account);

        AiModelConfig modelConfig = new AiModelConfig();
        modelConfig.setId(31L);
        modelConfig.setModelCode("gpt-4.1");
        modelConfig.setModelName("Runtime Default");
        modelConfig.setProvider("openai");
        bootstrap.setAiModelConfig(modelConfig);

        MarketApiConfig newsApiConfig = new MarketApiConfig();
        newsApiConfig.setId(41L);
        newsApiConfig.setDataCategory("NEWS");
        newsApiConfig.setApiUrl("https://feeds.internal/news");
        bootstrap.setNewsApiConfig(newsApiConfig);

        MarketApiConfig onchainApiConfig = new MarketApiConfig();
        onchainApiConfig.setId(42L);
        onchainApiConfig.setDataCategory("ONCHAIN");
        onchainApiConfig.setApiUrl("https://feeds.internal/onchain");
        bootstrap.setOnchainApiConfig(onchainApiConfig);

        MarketApiConfig socialApiConfig = new MarketApiConfig();
        socialApiConfig.setId(43L);
        socialApiConfig.setDataCategory("SOCIAL");
        socialApiConfig.setApiUrl("https://feeds.internal/social");
        bootstrap.setSocialApiConfig(socialApiConfig);

        MarketApiConfig marketApiConfig = new MarketApiConfig();
        marketApiConfig.setId(81L);
        marketApiConfig.setVersionNo(6);
        marketApiConfig.setDataCategory("PRICE");
        marketApiConfig.setTransportType("WEBSOCKET");
        marketApiConfig.setVendorCode("BINANCE");
        marketApiConfig.setMarketScope("FUTURES");
        marketApiConfig.setApiName("BINANCE_FUTURES_TICKER_WS");
        marketApiConfig.setWsBaseUrl("wss://fstream.binance.com");
        marketApiConfig.setWsPath("/stream");
        marketApiConfig.setWsCombinedEnabled(Boolean.TRUE);
        marketApiConfig.setWsConnectionTtlHours(24);
        marketApiConfig.setUpdateTime(new Date(1760667300000L));
        bootstrap.setMarketApiConfig(marketApiConfig);

        MarketDataConfig marketDataConfig = new MarketDataConfig();
        marketDataConfig.setId(51L);
        marketDataConfig.setConfigName("BTC Runtime Inputs");
        marketDataConfig.setSymbol("BTCUSDT");
        marketDataConfig.setEnabled("1");
        marketDataConfig.setCollectInterval(15);
        marketDataConfig.setCollectOnchain("1");
        marketDataConfig.setDataSources("[\"binance\",\"rss\",\"whale-alert\"]");
        bootstrap.setMarketDataConfig(marketDataConfig);

        TradeRuntimeAccountContext runtimeAccountContext = new TradeRuntimeAccountContext();
        runtimeAccountContext.setAccountEquity(new BigDecimal("12500.50"));
        runtimeAccountContext.setDailyPnl(new BigDecimal("235.10"));
        runtimeAccountContext.setRealizedPnl(new BigDecimal("180.25"));
        runtimeAccountContext.setUnrealizedPnl(new BigDecimal("-12.75"));
        runtimeAccountContext.setCurrentPositionSide("long");
        runtimeAccountContext.setCurrentPositionQuantity(new BigDecimal("0.2500"));
        runtimeAccountContext.setCurrentPositionNotional(new BigDecimal("16000.0000"));
        runtimeAccountContext.setEntryPrice(new BigDecimal("64000.00"));
        runtimeAccountContext.setMaxDrawdownPct(new BigDecimal("4.25"));
        runtimeAccountContext.setPeakAccountEquity(new BigDecimal("13055.75"));
        runtimeAccountContext.setConsecutiveFailures(2);
        bootstrap.setRuntimeAccountContext(runtimeAccountContext);

        when(runtimeConfigService.getBootstrapConfig(eq("BTCUSDT"), eq("binance"))).thenReturn(bootstrap);

        mockMvc.perform(get("/dca/trade/runtime/bootstrap")
                .param("symbol", "BTCUSDT")
                .param("exchange", "binance"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data.runtimeConfig.defaultMode").value("SHADOW"))
            .andExpect(jsonPath("$.data.strategy.strategyKey").value("event-btc"))
            .andExpect(jsonPath("$.data.strategyVersion.versionNo").value(3))
            .andExpect(jsonPath("$.data.symbolScope.symbol").value("BTCUSDT"))
            .andExpect(jsonPath("$.data.exchangeAccountBinding.accountId").value(21))
            .andExpect(jsonPath("$.data.exchangeAccount.exchangeCode").value("binance"))
            .andExpect(jsonPath("$.data.exchangeAccount.testnet").value(true))
            .andExpect(jsonPath("$.data.aiModelConfig.modelCode").value("gpt-4.1"))
            .andExpect(jsonPath("$.data.newsApiConfig.apiUrl").value("https://feeds.internal/news"))
            .andExpect(jsonPath("$.data.onchainApiConfig.apiUrl").value("https://feeds.internal/onchain"))
            .andExpect(jsonPath("$.data.socialApiConfig.apiUrl").value("https://feeds.internal/social"))
            .andExpect(jsonPath("$.data.marketApiConfig.vendorCode").value("BINANCE"))
            .andExpect(jsonPath("$.data.marketApiConfig.marketScope").value("FUTURES"))
            .andExpect(jsonPath("$.data.marketApiConfig.versionNo").value(6))
            .andExpect(jsonPath("$.data.marketApiConfig.updateTime").value("2025-10-17 02:15:00"))
            .andExpect(jsonPath("$.data.marketDataConfig.symbol").value("BTCUSDT"))
            .andExpect(jsonPath("$.data.marketDataConfig.collectOnchain").value("1"))
            .andExpect(jsonPath("$.data.marketDataConfig.collectInterval").value(15))
            .andExpect(jsonPath("$.data.runtimeAccountContext.accountEquity").value(12500.50))
            .andExpect(jsonPath("$.data.runtimeAccountContext.dailyPnl").value(235.10))
            .andExpect(jsonPath("$.data.runtimeAccountContext.realizedPnl").value(180.25))
            .andExpect(jsonPath("$.data.runtimeAccountContext.unrealizedPnl").value(-12.75))
            .andExpect(jsonPath("$.data.runtimeAccountContext.currentPositionSide").value("long"))
            .andExpect(jsonPath("$.data.runtimeAccountContext.currentPositionQuantity").value(0.25))
            .andExpect(jsonPath("$.data.runtimeAccountContext.currentPositionNotional").value(16000.0))
            .andExpect(jsonPath("$.data.runtimeAccountContext.entryPrice").value(64000.0))
            .andExpect(jsonPath("$.data.runtimeAccountContext.maxDrawdownPct").value(4.25))
            .andExpect(jsonPath("$.data.runtimeAccountContext.peakAccountEquity").value(13055.75))
            .andExpect(jsonPath("$.data.runtimeAccountContext.consecutiveFailures").value(2));
    }

    @Test
    void getBootstrapReturnsNormalizedTriggerThresholdFields() throws Exception {
        TradeRuntimeBootstrap bootstrap = new TradeRuntimeBootstrap();
        TradeRuntimeConfig runtimeConfig = new TradeRuntimeConfig();
        runtimeConfig.setDefaultMode(TradeRuntimeMode.SHADOW);
        runtimeConfig.setLiveEnabled(Boolean.FALSE);
        runtimeConfig.setRuntimeFlagsJson("""
            {
              "triggerMode":"EVENT_GATED",
              "marketTrigger":{
                "ruleOnlyPriceChangePct":1.0,
                "priceChangePct":2.5
              },
              "newsTrigger":{
                "ruleOnlyScoreThreshold":0.7,
                "scoreThreshold":0.9
              }
            }
            """);
        bootstrap.setRuntimeConfig(runtimeConfig);
        when(runtimeConfigService.getBootstrapConfig(eq("BTCUSDT"), eq("binance"))).thenReturn(bootstrap);

        mockMvc.perform(get("/dca/trade/runtime/bootstrap")
                .param("symbol", "BTCUSDT")
                .param("exchange", "binance"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data.runtimeConfig.marketTrigger.ruleOnlyPriceChangePct").value(1.0))
            .andExpect(jsonPath("$.data.runtimeConfig.marketTrigger.priceChangePct").value(2.5))
            .andExpect(jsonPath("$.data.runtimeConfig.newsTrigger.ruleOnlyScoreThreshold").value(0.7))
            .andExpect(jsonPath("$.data.runtimeConfig.newsTrigger.scoreThreshold").value(0.9));
    }

    @Test
    void getRoutesReturnsMultipleResolvedRuntimeRoutes() throws Exception {
        TradeRuntimeBootstrap first = new TradeRuntimeBootstrap();
        first.setRuntimeConfig(new TradeRuntimeConfig());
        first.getRuntimeConfig().setDefaultMode(TradeRuntimeMode.SHADOW);
        TradeSymbolScope firstScope = new TradeSymbolScope();
        firstScope.setSymbol("BTCUSDT");
        firstScope.setExchangeCode("binance");
        first.setSymbolScope(firstScope);

        TradeRuntimeBootstrap second = new TradeRuntimeBootstrap();
        second.setRuntimeConfig(new TradeRuntimeConfig());
        second.getRuntimeConfig().setDefaultMode(TradeRuntimeMode.SHADOW);
        TradeSymbolScope secondScope = new TradeSymbolScope();
        secondScope.setSymbol("ETHUSDT");
        secondScope.setExchangeCode("okx");
        second.setSymbolScope(secondScope);

        when(runtimeConfigService.listBootstrapConfigs()).thenReturn(List.of(first, second));

        mockMvc.perform(get("/dca/trade/runtime/routes"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data[0].symbolScope.symbol").value("BTCUSDT"))
            .andExpect(jsonPath("$.data[1].symbolScope.exchangeCode").value("okx"));
    }

    @Test
    void getOverviewReturnsOperatorConsoleSnapshot() throws Exception {
        TradeRuntimeOverview overview = new TradeRuntimeOverview();
        overview.setRuntimeConfig(new TradeRuntimeConfig());
        overview.getRuntimeConfig().setDefaultMode(TradeRuntimeMode.SHADOW);
        overview.getRuntimeConfig().setLiveEnabled(Boolean.FALSE);
        overview.setEventCount(12L);
        overview.setDecisionCount(4L);
        overview.setRiskHitCount(1L);
        overview.setActivePositionCount(2L);
        overview.setLatestDailyPnl(new java.math.BigDecimal("120.50"));
        overview.setMaxDrawdownPct(new java.math.BigDecimal("4.25"));
        overview.setLatestDispatchMode("RULE_ONLY");
        overview.setLastTriggerReason("budget_blocked");
        overview.setLastTriggerSource("news");
        overview.setCooldownSuppressionCount(2L);
        overview.setBudgetSuppressionCount(3L);
        overview.setLastSelectedAgentsJson("[\"market_agent\",\"news_agent\"]");
        overview.setLastCombinationMatchJson("{\"code\":\"strong_news_then_break\"}");
        overview.setExecutionStats(Map.of(
            "total", 7L,
            "filled", 3L,
            "partial", 1L,
            "failed", 1L,
            "blocked", 1L,
            "skipped", 1L
        ));
        ExchangeFill fill = new ExchangeFill();
        fill.setTraceId("trace-fill-1");
        fill.setOrderRef("ord-1");
        fill.setFillPrice(new BigDecimal("65000.00"));
        fill.setFillQuantity(new BigDecimal("0.0100"));
        overview.setRecentFills(List.of(fill));
        ExchangeOrder order = new ExchangeOrder();
        order.setTraceId("trace-order-1");
        order.setStatus("filled");
        order.setOrderStatus("FILLED");
        overview.setRecentOrders(List.of(order));
        SignalWindowState signalWindowState = new SignalWindowState();
        signalWindowState.setWindowKey("news:BTCUSDT:15m");
        signalWindowState.setSourceType("news");
        signalWindowState.setSignalType("headline");
        signalWindowState.setDirection("bullish");
        signalWindowState.setStrengthScore(new BigDecimal("0.82"));
        signalWindowState.setExpiresAt("2026-04-23T11:00:00Z");
        signalWindowState.setActive(Boolean.TRUE);
        overview.setActiveSignalWindows(List.of(signalWindowState));
        when(tradeRuntimeOverviewService.getOverview()).thenReturn(overview);

        mockMvc.perform(get("/dca/trade/runtime/overview"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data.runtimeConfig.defaultMode").value("SHADOW"))
            .andExpect(jsonPath("$.data.eventCount").value(12))
            .andExpect(jsonPath("$.data.riskHitCount").value(1))
            .andExpect(jsonPath("$.data.activePositionCount").value(2))
            .andExpect(jsonPath("$.data.latestDailyPnl").value(120.50))
            .andExpect(jsonPath("$.data.maxDrawdownPct").value(4.25))
            .andExpect(jsonPath("$.data.latestDispatchMode").value("RULE_ONLY"))
            .andExpect(jsonPath("$.data.lastTriggerReason").value("budget_blocked"))
            .andExpect(jsonPath("$.data.lastTriggerSource").value("news"))
            .andExpect(jsonPath("$.data.cooldownSuppressionCount").value(2))
            .andExpect(jsonPath("$.data.budgetSuppressionCount").value(3))
            .andExpect(jsonPath("$.data.lastSelectedAgentsJson").value("[\"market_agent\",\"news_agent\"]"))
            .andExpect(jsonPath("$.data.lastCombinationMatchJson").value("{\"code\":\"strong_news_then_break\"}"))
            .andExpect(jsonPath("$.data.executionStats.total").value(7))
            .andExpect(jsonPath("$.data.executionStats.filled").value(3))
            .andExpect(jsonPath("$.data.executionStats.partial").value(1))
            .andExpect(jsonPath("$.data.executionStats.failed").value(1))
            .andExpect(jsonPath("$.data.executionStats.blocked").value(1))
            .andExpect(jsonPath("$.data.executionStats.skipped").value(1))
            .andExpect(jsonPath("$.data.recentFills[0].traceId").value("trace-fill-1"))
            .andExpect(jsonPath("$.data.recentFills[0].orderRef").value("ord-1"))
            .andExpect(jsonPath("$.data.activeSignalWindows[0].windowKey").value("news:BTCUSDT:15m"))
            .andExpect(jsonPath("$.data.activeSignalWindows[0].sourceType").value("news"))
            .andExpect(jsonPath("$.data.activeSignalWindows[0].signalType").value("headline"))
            .andExpect(jsonPath("$.data.activeSignalWindows[0].direction").value("bullish"))
            .andExpect(jsonPath("$.data.activeSignalWindows[0].strengthScore").value(0.82))
            .andExpect(jsonPath("$.data.activeSignalWindows[0].expiresAt").value("2026-04-23T11:00:00Z"))
            .andExpect(jsonPath("$.data.activeSignalWindows[0].active").value(true))
            .andExpect(jsonPath("$.data.recentOrders[0].executionStatus").value("filled"))
            .andExpect(jsonPath("$.data.recentOrders[0].status").value("filled"))
            .andExpect(jsonPath("$.data.recentOrders[0].orderStatus").value("FILLED"));
    }

    @Test
    void updateRuntimeConfigPersistsWritableControlPlaneState() throws Exception {
        when(runtimeConfigService.saveCurrentConfig(any(TradeRuntimeConfig.class))).thenReturn(1);

        mockMvc.perform(put("/dca/trade/runtime/config")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "defaultMode":"LIVE",
                      "liveEnabled":true,
                      "maxPositionRatio":0.35,
                      "maxDailyLoss":-650.0,
                      "maxConsecutiveFailures":5,
                      "allowedSymbolsJson":"[\\"BTCUSDT\\",\\"ETHUSDT\\"]",
                      "allowedExchangesJson":"[\\"BINANCE\\",\\"OKX\\"]",
                      "requireAccountBinding":true,
                      "liveOrderRequiresHealthyAccount":true,
                      "runtimeFlagsJson":"{\\"haltOnDataGap\\":true}",
                      "notifyDefaultsJson":"{\\"channels\\":[\\"OPS\\"]}",
                      "eventRetentionDays":30,
                      "replayRetentionDays":7,
                      "routeSchedulerMode":"THREAD_POOL",
                      "routeMaxConcurrency":4,
                      "deliberationEnabled":true,
                      "deliberationMaxRounds":1,
                      "deliberationFailOpen":true
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void updateRuntimeConfigAcceptsLowercaseRuntimeModeInJsonBody() throws Exception {
        when(runtimeConfigService.saveCurrentConfig(any(TradeRuntimeConfig.class))).thenReturn(1);

        mockMvc.perform(put("/dca/trade/runtime/config")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "defaultMode":"shadow",
                      "liveEnabled":false
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        ArgumentCaptor<TradeRuntimeConfig> captor = ArgumentCaptor.forClass(TradeRuntimeConfig.class);
        verify(runtimeConfigService).saveCurrentConfig(captor.capture());
        assertEquals(TradeRuntimeMode.SHADOW, captor.getValue().getDefaultMode());
    }

    @Test
    void runtimeModelCallReturnsExtractedContentAndResolvedModelMetadata() throws Exception {
        RuntimeModelCallResponse response = new RuntimeModelCallResponse();
        response.setModelId(31L);
        response.setModelCode("gpt-4.1");
        response.setModelProvider("openai");
        response.setContent("{\"action\":\"OPEN_LONG\"}");
        when(aiModelConfigService.callAiModelForRuntime(eq(31L), eq("Return JSON only"))).thenReturn(response);

        mockMvc.perform(post("/dca/trade/runtime/model-call")
                .contentType(APPLICATION_JSON)
                .content("""
                    {"modelId":31,"prompt":"Return JSON only"}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data.modelId").value(31))
            .andExpect(jsonPath("$.data.modelCode").value("gpt-4.1"))
            .andExpect(jsonPath("$.data.modelProvider").value("openai"))
            .andExpect(jsonPath("$.data.content").value("{\"action\":\"OPEN_LONG\"}"));
    }
}
