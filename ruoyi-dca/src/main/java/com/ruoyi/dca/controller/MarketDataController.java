package com.ruoyi.dca.controller;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.common.utils.poi.ExcelUtil;
import com.ruoyi.dca.domain.MarketApiConfig;
import com.ruoyi.dca.domain.MarketCollectTask;
import com.ruoyi.dca.domain.MarketData;
import com.ruoyi.dca.domain.MarketDataCollectLog;
import com.ruoyi.dca.domain.MarketDataConfig;
import com.ruoyi.dca.mapper.MarketDataCollectLogMapper;
import com.ruoyi.dca.service.IMarketApiConfigService;
import com.ruoyi.dca.service.IMarketCollectTaskService;
import com.ruoyi.dca.service.IMarketDataCollectService;
import com.ruoyi.dca.service.IMarketDataConfigService;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/dca/market")
public class MarketDataController extends BaseController {

    private static final String LEGACY_MARKET_RETIRED_MESSAGE =
        "Legacy market-data collection endpoints are frozen. Use /dca/market/api or /dca/trade/* instead.";

    @Autowired
    private IMarketDataCollectService collectService;

    @Autowired
    private IMarketDataConfigService configService;

    @Autowired
    private MarketDataCollectLogMapper collectLogMapper;

    @Autowired
    private IMarketApiConfigService apiConfigService;

    @Autowired
    private IMarketCollectTaskService taskService;

    @PreAuthorize("@ss.hasPermi('dca:market:query')")
    @GetMapping("/config/list")
    public TableDataInfo configList(MarketDataConfig config) {
        startPage();
        return getDataTable(configService.selectConfigList(config));
    }

    @PreAuthorize("@ss.hasPermi('dca:market:query')")
    @GetMapping("/config/{id}")
    public AjaxResult getConfig(@PathVariable("id") Long id) {
        return success(configService.selectConfigById(id));
    }

    @PreAuthorize("@ss.hasPermi('dca:market:add')")
    @Log(title = "Legacy Market Config", businessType = BusinessType.INSERT)
    @PostMapping("/config")
    public AjaxResult addConfig(@RequestBody MarketDataConfig config) {
        return legacyMarketRetired();
    }

    @PreAuthorize("@ss.hasPermi('dca:market:edit')")
    @Log(title = "Legacy Market Config", businessType = BusinessType.UPDATE)
    @PutMapping("/config")
    public AjaxResult updateConfig(@RequestBody MarketDataConfig config) {
        return legacyMarketRetired();
    }

    @PreAuthorize("@ss.hasPermi('dca:market:remove')")
    @Log(title = "Legacy Market Config", businessType = BusinessType.DELETE)
    @DeleteMapping("/config/{ids}")
    public AjaxResult deleteConfig(@PathVariable Long[] ids) {
        return legacyMarketRetired();
    }

    @PreAuthorize("@ss.hasPermi('dca:market:query')")
    @GetMapping("/data/{symbol}")
    public AjaxResult getMarketData(@PathVariable String symbol) {
        MarketData data = collectService.getLatestMarketData(symbol);
        if (data == null) {
            return error("未找到市场数据");
        }
        return success(data);
    }

    @PreAuthorize("@ss.hasPermi('dca:market:query')")
    @GetMapping("/data")
    public AjaxResult getMarketDataList(@RequestParam String symbols) {
        String[] symbolArray = symbols.split(",");
        Map<String, MarketData> resultMap = new HashMap<>();
        for (String symbol : symbolArray) {
            MarketData data = collectService.getLatestMarketData(symbol.trim());
            if (data != null) {
                resultMap.put(symbol, data);
            }
        }
        return success(resultMap);
    }

    @PreAuthorize("@ss.hasPermi('dca:market:query')")
    @GetMapping("/data/{symbol}/history")
    public AjaxResult getMarketDataHistory(@PathVariable String symbol, @RequestParam(defaultValue = "7") int days) {
        return success(collectService.getMarketDataHistory(symbol, days));
    }

    @GetMapping("/feargreed")
    public AjaxResult getFearGreedIndex() {
        Integer index = collectService.getFearGreedIndex();
        Map<String, Object> result = new HashMap<>();
        if (index != null) {
            result.put("value", index);
            result.put("classification", getFearGreedClassification(index));
        } else {
            result.put("value", null);
            result.put("classification", "Unknown");
        }
        return success(result);
    }

    @PreAuthorize("@ss.hasPermi('dca:market:collect')")
    @Log(title = "Legacy Market Collect", businessType = BusinessType.OTHER)
    @PostMapping("/collect/trigger")
    public AjaxResult triggerCollection(@RequestBody Map<String, Object> params) {
        return legacyMarketRetired();
    }

    @PreAuthorize("@ss.hasPermi('dca:market:log')")
    @GetMapping("/log/list")
    public TableDataInfo logList(MarketDataCollectLog log) {
        startPage();
        return getDataTable(collectLogMapper.selectMarketDataCollectLogList(log));
    }

    @PreAuthorize("@ss.hasPermi('dca:market:query')")
    @GetMapping("/dashboard")
    public AjaxResult getDashboard() {
        Map<String, Object> dashboard = new HashMap<>();
        List<MarketDataConfig> configs = configService.selectEnabledConfigs();
        Map<String, Object> marketData = new HashMap<>();
        Integer fearGreedIndex = collectService.getFearGreedIndex();

        for (MarketDataConfig config : configs) {
            MarketData data = collectService.getLatestMarketData(config.getSymbol());
            if (data != null) {
                marketData.put(config.getSymbol(), data);
            }
        }

        dashboard.put("marketData", marketData);
        dashboard.put("fearGreedIndex", fearGreedIndex);
        dashboard.put("configCount", configs.size());
        return success(dashboard);
    }

    @PreAuthorize("@ss.hasPermi('dca:market:export')")
    @Log(title = "Market Data", businessType = BusinessType.EXPORT)
    @PostMapping("/data/export")
    public void exportData(HttpServletResponse response, MarketData marketData) {
        List<MarketData> list = collectService.getMarketDataHistory(marketData.getSymbol(), 7);
        ExcelUtil<MarketData> util = new ExcelUtil<>(MarketData.class);
        util.exportExcel(response, list, "市场数据");
    }

    @PreAuthorize("@ss.hasPermi('dca:market:task')")
    @GetMapping("/task/list")
    public TableDataInfo taskList(MarketCollectTask task) {
        startPage();
        return getDataTable(taskService.selectTaskList(task));
    }

    @PreAuthorize("@ss.hasPermi('dca:market:task')")
    @GetMapping("/task/{id}")
    public AjaxResult getTask(@PathVariable("id") Long id) {
        return success(taskService.selectTaskById(id));
    }

    @PreAuthorize("@ss.hasPermi('dca:market:task:add')")
    @Log(title = "Legacy Market Task", businessType = BusinessType.INSERT)
    @PostMapping("/task")
    public AjaxResult addTask(@RequestBody MarketCollectTask task) {
        return legacyMarketRetired();
    }

    @PreAuthorize("@ss.hasPermi('dca:market:task:edit')")
    @Log(title = "Legacy Market Task", businessType = BusinessType.UPDATE)
    @PutMapping("/task")
    public AjaxResult updateTask(@RequestBody MarketCollectTask task) {
        return legacyMarketRetired();
    }

    @PreAuthorize("@ss.hasPermi('dca:market:task:remove')")
    @Log(title = "Legacy Market Task", businessType = BusinessType.DELETE)
    @DeleteMapping("/task/{ids}")
    public AjaxResult deleteTask(@PathVariable Long[] ids) {
        return legacyMarketRetired();
    }

    @Anonymous
    @GetMapping("/api/config/enabled/{dataCategory}")
    public AjaxResult getEnabledApiConfigs(@PathVariable String dataCategory) {
        return success(apiConfigService.selectEnabledApis(dataCategory));
    }

    @PreAuthorize("@ss.hasPermi('dca:market:api')")
    @GetMapping("/api/list")
    public TableDataInfo apiList(MarketApiConfig config) {
        startPage();
        return getDataTable(apiConfigService.selectApiConfigList(config));
    }

    @PreAuthorize("@ss.hasPermi('dca:market:api')")
    @GetMapping("/api/{id}")
    public AjaxResult getApi(@PathVariable("id") Long id) {
        return success(apiConfigService.selectApiConfigById(id));
    }

    @PreAuthorize("@ss.hasPermi('dca:market:api:add')")
    @Log(title = "Market API Config", businessType = BusinessType.INSERT)
    @PostMapping("/api")
    public AjaxResult addApi(@RequestBody MarketApiConfig config) {
        return toAjax(apiConfigService.insertApiConfig(config));
    }

    @PreAuthorize("@ss.hasPermi('dca:market:api:edit')")
    @Log(title = "Market API Config", businessType = BusinessType.UPDATE)
    @PutMapping("/api")
    public AjaxResult updateApi(@RequestBody MarketApiConfig config) {
        return toAjax(apiConfigService.updateApiConfig(config));
    }

    @PreAuthorize("@ss.hasPermi('dca:market:api:remove')")
    @Log(title = "Market API Config", businessType = BusinessType.DELETE)
    @DeleteMapping("/api/{ids}")
    public AjaxResult deleteApi(@PathVariable Long[] ids) {
        return toAjax(apiConfigService.deleteApiConfigByIds(ids));
    }

    @PreAuthorize("@ss.hasPermi('dca:market:api:test')")
    @PostMapping("/api/test/{id}")
    public AjaxResult testApi(@PathVariable Long id) {
        Map<String, Object> result = apiConfigService.testApiConnection(id);
        if (Boolean.TRUE.equals(result.get("success"))) {
            return success(result);
        }
        return error(String.valueOf(result.get("message")));
    }

    private String getFearGreedClassification(int value) {
        if (value <= 20) {
            return "Extreme Fear";
        }
        if (value <= 40) {
            return "Fear";
        }
        if (value <= 60) {
            return "Neutral";
        }
        if (value <= 80) {
            return "Greed";
        }
        return "Extreme Greed";
    }

    private AjaxResult legacyMarketRetired() {
        return AjaxResult.error(LEGACY_MARKET_RETIRED_MESSAGE);
    }
}
