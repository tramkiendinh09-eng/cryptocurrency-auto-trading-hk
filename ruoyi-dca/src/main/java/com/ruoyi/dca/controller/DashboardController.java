package com.ruoyi.dca.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.dca.service.IDashboardService;
import com.ruoyi.dca.service.trade.ITradeRuntimeOverviewService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * DCA浠〃鐩楥ontroller
 *
 * @author ruoyi
 */
@RestController
@RequestMapping("/dca/dashboard")
public class DashboardController extends BaseController {
    private static final String LEGACY_CHART_RETIRED_MESSAGE =
        "Legacy dashboard chart endpoints are retired. Use /dca/dashboard/overview or /dca/dashboard/runtimeFeed instead.";

    @Autowired
    private IDashboardService dashboardService;

    @Autowired
    private ITradeRuntimeOverviewService tradeRuntimeOverviewService;

    @Autowired
    private ObjectMapper objectMapper;

    /**
     * 鑾峰彇浠〃鐩樻瑙堢粺璁?
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/overview")
    public AjaxResult getOverview() {
        Map<String, Object> overview = dashboardService.getOverviewMap(getUserId());
        return success(overview);
    }

    /**
     * 鑾峰彇Worker鐘舵€?
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/workerStatus")
    public AjaxResult getWorkerStatus() {
        Map<String, Object> overview = dashboardService.getOverviewMap(getUserId());
        Object workerStatus = overview.get("workerStatus");
        // TODO: 浠嶹orker蹇冭烦琛ㄨ幏鍙栫湡瀹炵姸鎬?
        return success(workerStatus);
    }

    /**
     * 鑾峰彇閫氱煡缁熻
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/notifyStats")
    public AjaxResult getNotifyStats() {
        Map<String, Object> overview = dashboardService.getOverviewMap(getUserId());
        Object notifyStats = overview.get("notifyStats");
        return success(notifyStats);
    }

    /**
     * 鑾峰彇椋庢帶缁熻
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/riskStats")
    public AjaxResult getRiskStats() {
        Map<String, Object> overview = dashboardService.getOverviewMap(getUserId());
        Object riskStats = overview.get("riskStats");
        return success(riskStats);
    }

    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/runtimeFeed")
    public AjaxResult getRuntimeFeed() {
        return success(normalizeRuntimeOverviewPayload(tradeRuntimeOverviewService.getOverview()));
    }


    /**
     * 鑾峰彇鐩堜簭鏇茬嚎鏁版嵁
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/profitLossCurve/{strategyId}")
    public AjaxResult getProfitLossCurve(@PathVariable Long strategyId) {
        return legacyChartRetiredMap();
    }

    /**
     * 鑾峰彇鎸佷粨鍒嗗竷鏁版嵁
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/holdingDistribution")
    public AjaxResult getHoldingDistribution() {
        return legacyChartRetiredList();
    }

    /**
     * 鑾峰彇AI娑堣€楃粺璁℃暟鎹?
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/aiConsumption")
    public AjaxResult getAiConsumption() {
        return legacyChartRetiredMap();
    }

    /**
     * 鑾峰彇绛栫暐瑙﹀彂瓒嬪娍鏁版嵁
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/triggerTrend")
    public AjaxResult getTriggerTrend() {
        return legacyChartRetiredMap();
    }

    /**
     * 鑾峰彇浜ゆ槗閲忕粺璁℃暟鎹?
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/tradeVolume")
    public AjaxResult getTradeVolume() {
        return legacyChartRetiredMap();
    }

    /**
     * 鑾峰彇鏀剁泭鐜囩粺璁?
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/profitRate")
    public AjaxResult getProfitRate() {
        return legacyChartRetiredMap();
    }

    /**
     * 鑾峰彇浠锋牸璧板娍鏁版嵁
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/priceTrend/{symbol}")
    public AjaxResult getPriceTrend(@PathVariable String symbol) {
        return legacyChartRetiredMap();
    }

    /**
     * 鑾峰彇绛栫暐瀵规瘮鏁版嵁
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/strategyComparison")
    public AjaxResult getStrategyComparison() {
        return legacyChartRetiredList();
    }

    /**
     * 鑾峰彇鏈€杩戠瓥鐣ヨЕ鍙戣褰?
     */
    @PreAuthorize("@ss.hasPermi('dca:dashboard:list')")
    @GetMapping("/recentTriggers")
    public AjaxResult getRecentTriggers() {
        return legacyChartRetiredList();
    }

    private AjaxResult legacyChartRetiredMap() {
        return AjaxResult.success(LEGACY_CHART_RETIRED_MESSAGE, Collections.emptyMap());
    }

    private AjaxResult legacyChartRetiredList() {
        return AjaxResult.success(LEGACY_CHART_RETIRED_MESSAGE, Collections.emptyList());
    }

    private Map<String, Object> normalizeRuntimeOverviewPayload(Object overview) {
        if (overview == null) {
            return null;
        }
        Map<String, Object> payload = objectMapper.convertValue(overview, new TypeReference<>() {});
        Object recentOrdersRaw = payload.get("recentOrders");
        if (!(recentOrdersRaw instanceof List<?> recentOrders)) {
            return payload;
        }
        List<Map<String, Object>> normalizedOrders = new java.util.ArrayList<>(recentOrders.size());
        for (Object item : recentOrders) {
            Map<String, Object> order = new LinkedHashMap<>(objectMapper.convertValue(item, new TypeReference<>() {}));
            Object status = order.get("status");
            Object executionStatus = order.get("executionStatus");
            if (executionStatus == null || executionStatus.toString().trim().isEmpty()) {
                order.put("executionStatus", status == null || status.toString().trim().isEmpty() ? "pending" : status);
            }
            normalizedOrders.add(order);
        }
        payload.put("recentOrders", normalizedOrders);
        return payload;
    }
}
