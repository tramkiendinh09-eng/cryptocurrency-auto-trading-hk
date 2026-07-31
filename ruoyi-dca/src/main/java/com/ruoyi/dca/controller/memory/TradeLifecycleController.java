package com.ruoyi.dca.controller.memory;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.dca.domain.memory.TradeLifecycle;
import com.ruoyi.dca.service.memory.TradeLifecycleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/dca/trade-lifecycle")
public class TradeLifecycleController extends BaseController {
    @Autowired
    private TradeLifecycleService tradeLifecycleService;

    @Anonymous
    @PostMapping
    public AjaxResult create(@RequestBody TradeLifecycle lifecycle) {
        TradeLifecycle created = tradeLifecycleService.createLifecycle(lifecycle);
        return success(created);
    }

    @Anonymous
    @GetMapping("/{traceId}")
    public AjaxResult getByTraceId(@PathVariable String traceId) {
        TradeLifecycle lifecycle = tradeLifecycleService.getByTraceId(traceId);
        if (lifecycle == null) {
            return error("Lifecycle not found");
        }
        return success(lifecycle);
    }

    @Anonymous
    @PatchMapping("/{traceId}")
    public AjaxResult update(@PathVariable String traceId, @RequestBody TradeLifecycle updates) {
        TradeLifecycle updated = tradeLifecycleService.updateLifecycle(traceId, updates);
        return success(updated);
    }

    @Anonymous
    @GetMapping("/closed")
    public AjaxResult listClosed(@RequestParam(required = false) Integer limit) {
        List<TradeLifecycle> lifecycles = tradeLifecycleService.listClosedLifecycles(limit);
        return success(lifecycles);
    }
}