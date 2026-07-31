package com.ruoyi.dca.dashboard;

import com.ruoyi.common.core.domain.entity.SysUser;
import com.ruoyi.common.core.domain.model.LoginUser;
import com.ruoyi.dca.controller.DashboardController;
import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.trade.TradeRuntimeOverview;
import com.ruoyi.dca.service.IDashboardService;
import com.ruoyi.dca.service.trade.ITradeRuntimeOverviewService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Collections;
import java.util.Map;

import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(DashboardController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {DashboardControllerTest.TestApplication.class, DashboardController.class})
class DashboardControllerTest {
    private static final String LEGACY_CHART_RETIRED_MESSAGE =
        "Legacy dashboard chart endpoints are retired. Use /dca/dashboard/overview or /dca/dashboard/runtimeFeed instead.";

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private IDashboardService dashboardService;

    @MockBean
    private ITradeRuntimeOverviewService tradeRuntimeOverviewService;

    @Test
    void getOverviewReturnsExecutionStatsForOperatorConsole() throws Exception {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(loginUser(1L), null));
        try {
            when(dashboardService.getOverviewMap(1L)).thenReturn(Map.of(
                "executionStats", Map.of(
                    "total", 10L,
                    "filled", 3L,
                    "pending", 2L,
                    "partial", 1L,
                    "canceled", 1L,
                    "expired", 0L,
                    "failed", 1L,
                    "blocked", 1L,
                    "skipped", 1L
                )
            ));

            mockMvc.perform(get("/dca/dashboard/overview"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.executionStats.total").value(10))
                .andExpect(jsonPath("$.data.executionStats.filled").value(3))
                .andExpect(jsonPath("$.data.executionStats.pending").value(2))
                .andExpect(jsonPath("$.data.executionStats.partial").value(1))
                .andExpect(jsonPath("$.data.executionStats.canceled").value(1))
                .andExpect(jsonPath("$.data.executionStats.expired").value(0))
                .andExpect(jsonPath("$.data.executionStats.failed").value(1))
                .andExpect(jsonPath("$.data.executionStats.blocked").value(1))
                .andExpect(jsonPath("$.data.executionStats.skipped").value(1));
        } finally {
            SecurityContextHolder.clearContext();
        }
    }

    @Test
    void getWorkerStatusReturnsRuntimeWorkerSnapshot() throws Exception {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(loginUser(1L), null));
        try {
            when(dashboardService.getOverviewMap(1L)).thenReturn(Map.of(
                "workerStatus", Map.of(
                    "online", true,
                    "workerId", "runtime-worker-1",
                    "workerType", "Python Worker",
                    "queueLength", 4,
                    "totalTasks", 12,
                    "successTasks", 10,
                    "failedTasks", 2
                )
            ));

            mockMvc.perform(get("/dca/dashboard/workerStatus"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.online").value(true))
                .andExpect(jsonPath("$.data.workerId").value("runtime-worker-1"))
                .andExpect(jsonPath("$.data.workerType").value("Python Worker"))
                .andExpect(jsonPath("$.data.queueLength").value(4))
                .andExpect(jsonPath("$.data.totalTasks").value(12))
                .andExpect(jsonPath("$.data.successTasks").value(10))
                .andExpect(jsonPath("$.data.failedTasks").value(2));
        } finally {
            SecurityContextHolder.clearContext();
        }
    }

    @Test
    void getNotifyStatsReturnsOverviewBackedNotifySummary() throws Exception {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(loginUser(1L), null));
        try {
            when(dashboardService.getOverviewMap(1L)).thenReturn(Map.of(
                "notifyStats", Map.of(
                    "successRate", 97,
                    "todayCount", 12
                )
            ));

            mockMvc.perform(get("/dca/dashboard/notifyStats"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.successRate").value(97))
                .andExpect(jsonPath("$.data.todayCount").value(12));
        } finally {
            SecurityContextHolder.clearContext();
        }
    }

    @Test
    void getRiskStatsReturnsOverviewBackedRiskSummary() throws Exception {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(loginUser(1L), null));
        try {
            when(dashboardService.getOverviewMap(1L)).thenReturn(Map.of(
                "riskStats", Map.of(
                    "todayBlocks", 3,
                    "blockRate", 25
                )
            ));

            mockMvc.perform(get("/dca/dashboard/riskStats"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.todayBlocks").value(3))
                .andExpect(jsonPath("$.data.blockRate").value(25));
        } finally {
            SecurityContextHolder.clearContext();
        }
    }

    @Test
    void getRuntimeFeedReturnsRuntimeRecentReadModel() throws Exception {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(loginUser(1L), null));
        try {
            TradeRuntimeOverview overview = new TradeRuntimeOverview();
            overview.setDecisionCount(4L);
            overview.setRiskHitCount(1L);
            overview.setExecutionStats(Map.of("total", 3L, "filled", 2L, "failed", 1L));
            ExchangeOrder order = new ExchangeOrder();
            order.setTraceId("trace-order-1");
            order.setStatus("blocked");
            order.setOrderStatus("BLOCKED");
            overview.setRecentOrders(java.util.List.of(order));
            ExchangeFill fill = new ExchangeFill();
            fill.setTraceId("trace-fill-1");
            fill.setOrderRef("ord-1");
            overview.setRecentFills(java.util.List.of(fill));

            when(tradeRuntimeOverviewService.getOverview()).thenReturn(overview);

            mockMvc.perform(get("/dca/dashboard/runtimeFeed"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.decisionCount").value(4))
                .andExpect(jsonPath("$.data.riskHitCount").value(1))
                .andExpect(jsonPath("$.data.executionStats.total").value(3))
                .andExpect(jsonPath("$.data.executionStats.filled").value(2))
                .andExpect(jsonPath("$.data.executionStats.failed").value(1))
                .andExpect(jsonPath("$.data.recentFills[0].traceId").value("trace-fill-1"))
                .andExpect(jsonPath("$.data.recentFills[0].orderRef").value("ord-1"))
                .andExpect(jsonPath("$.data.recentOrders[0].executionStatus").value("blocked"))
                .andExpect(jsonPath("$.data.recentOrders[0].status").value("blocked"))
                .andExpect(jsonPath("$.data.recentOrders[0].orderStatus").value("BLOCKED"));
        } finally {
            SecurityContextHolder.clearContext();
        }
    }

    @Test
    void legacyChartEndpointsReturnRetiredPayloadWithoutServiceCalls() throws Exception {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(loginUser(1L), null));
        try {
            mockMvc.perform(get("/dca/dashboard/profitLossCurve/7"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.msg").value(LEGACY_CHART_RETIRED_MESSAGE))
                .andExpect(jsonPath("$.data").isMap());

            mockMvc.perform(get("/dca/dashboard/holdingDistribution"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.msg").value(LEGACY_CHART_RETIRED_MESSAGE))
                .andExpect(jsonPath("$.data").isArray());

            mockMvc.perform(get("/dca/dashboard/aiConsumption"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.msg").value(LEGACY_CHART_RETIRED_MESSAGE))
                .andExpect(jsonPath("$.data").isMap());

            mockMvc.perform(get("/dca/dashboard/triggerTrend"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.msg").value(LEGACY_CHART_RETIRED_MESSAGE));

            mockMvc.perform(get("/dca/dashboard/tradeVolume"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.msg").value(LEGACY_CHART_RETIRED_MESSAGE));

            mockMvc.perform(get("/dca/dashboard/profitRate"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.msg").value(LEGACY_CHART_RETIRED_MESSAGE));

            mockMvc.perform(get("/dca/dashboard/priceTrend/BTCUSDT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.msg").value(LEGACY_CHART_RETIRED_MESSAGE));

            mockMvc.perform(get("/dca/dashboard/strategyComparison"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.msg").value(LEGACY_CHART_RETIRED_MESSAGE))
                .andExpect(jsonPath("$.data").isArray());

            mockMvc.perform(get("/dca/dashboard/recentTriggers"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.msg").value(LEGACY_CHART_RETIRED_MESSAGE))
                .andExpect(jsonPath("$.data").isArray());

            verifyNoInteractions(dashboardService, tradeRuntimeOverviewService);
        } finally {
            SecurityContextHolder.clearContext();
        }
    }

    private LoginUser loginUser(Long userId) {
        SysUser user = new SysUser(userId);
        user.setUserName("operator");
        user.setPassword("ignored");
        return new LoginUser(userId, 1L, user, Collections.emptySet());
    }
}
