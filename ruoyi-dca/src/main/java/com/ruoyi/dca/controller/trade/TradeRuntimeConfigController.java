package com.ruoyi.dca.controller.trade;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.StringUtils;
import com.ruoyi.dca.domain.trade.RuntimeModelCallRequest;
import com.ruoyi.dca.domain.trade.TradeRuntimeConfig;
import com.ruoyi.dca.service.IAiModelConfigService;
import com.ruoyi.dca.service.trade.ITradeRuntimeConfigService;
import com.ruoyi.dca.service.trade.ITradeRuntimeOverviewService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 交易运行时配置控制器
 *
 * 提供交易运行时的配置管理RESTful API接口，是Java后端与Python Worker交互的核心入口。
 *
 * 核心功能:
 * 1. 运行时配置管理: 获取和更新交易运行时的全局配置
 * 2. 启动配置组装: 为Python Worker提供完整的启动引导配置(TradeRuntimeBootstrap)
 * 3. 路由配置: 支持多交易对、多交易所的路由配置
 * 4. 运行时概览: 提供交易运行时的统计数据和概览信息
 * 5. 模型调用: 代理调用AI模型，供Python Worker使用
 *
 * 接口说明:
 * - /config: 运行时配置CRUD
 * - /bootstrap: 启动引导配置(供Python Worker调用)
 * - /routes: 路由配置列表
 * - /overview: 运行时概览
 * - /model-call: AI模型调用代理
 *
 * 与Python Worker的交互:
 * Python Worker启动时调用/bootstrap接口获取完整配置，包括:
 * - 运行时配置(runtimeConfig)
 * - 策略配置(strategy, strategyVersion)
 * - 交易对范围(symbolScope)
 * - 交易所账户(exchangeAccount)
 * - AI模型配置(aiModelConfig)
 * - 数据源配置(newsApiConfig, onchainApiConfig, etc.)
 * - Agent配置(agentProfiles, promptBindings)
 * - 账户上下文(runtimeAccountContext)
 *
 * @author ruoyi-dca
 */
@RestController
@RequestMapping("/dca/trade/runtime")
public class TradeRuntimeConfigController extends BaseController {

    @Autowired
    private ITradeRuntimeConfigService runtimeConfigService;

    @Autowired
    private ITradeRuntimeOverviewService tradeRuntimeOverviewService;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private IAiModelConfigService aiModelConfigService;

    /**
     * 获取当前运行时配置
     *
     * @return 运行时配置
     */
    @Anonymous
    @GetMapping("/config")
    public AjaxResult getConfig() {
        return success(runtimeConfigService.getCurrentConfig());
    }

    /**
     * 获取启动配置
     *
     * @param symbol 交易对
     * @param exchange 交易所
     * @return 启动配置
     */
    @Anonymous
    @GetMapping("/bootstrap")
    public AjaxResult getBootstrap(
        @RequestParam(required = false) String symbol,
        @RequestParam(required = false) String exchange
    ) {
        return success(runtimeConfigService.getBootstrapConfig(symbol, exchange));
    }

    /**
     * 获取路由列表
     *
     * @return 路由配置列表
     */
    @Anonymous
    @GetMapping("/routes")
    public AjaxResult listRoutes() {
        return success(runtimeConfigService.listBootstrapConfigs());
    }

    /**
     * 获取运行时概览
     *
     * @return 运行时概览数据
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeRuntime:query')")
    @GetMapping("/overview")
    public AjaxResult getOverview() {
        return success(normalizeRuntimeOverviewPayload(tradeRuntimeOverviewService.getOverview()));
    }

    /**
     * 更新运行时配置
     *
     * @param tradeRuntimeConfig 运行时配置
     * @return 操作结果
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeRuntime:edit')")
    @PutMapping("/config")
    public AjaxResult updateConfig(@RequestBody TradeRuntimeConfig tradeRuntimeConfig) {
        return toAjax(runtimeConfigService.saveCurrentConfig(tradeRuntimeConfig));
    }

    /**
     * 调用运行时模型
     *
     * @param request 模型调用请求
     * @return 模型调用结果
     */
    @Anonymous
    @PostMapping("/model-call")
    public AjaxResult callRuntimeModel(@RequestBody RuntimeModelCallRequest request) {
        String prompt = request == null ? null : request.getPrompt();
        if (StringUtils.isEmpty(prompt) || StringUtils.isEmpty(prompt.trim())) {
            return error("prompt不能为空");
        }
        return success(aiModelConfigService.callAiModelForRuntime(request.getModelId(), prompt.trim()));
    }

    /**
     * 标准化运行时概览数据
     * 确保订单状态字段完整
     *
     * @param overview 概览对象
     * @return 标准化后的概览数据
     */
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
