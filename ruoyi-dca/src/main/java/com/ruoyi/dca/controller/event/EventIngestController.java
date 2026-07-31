package com.ruoyi.dca.controller.event;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.dca.domain.event.EventRaw;
import com.ruoyi.dca.service.event.IEventIngestService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/dca/event")
public class EventIngestController extends BaseController {

    @Autowired
    private IEventIngestService eventIngestService;

    @Anonymous
    @PostMapping("/ingest")
    public AjaxResult ingest(@RequestBody EventRaw eventRaw) {
        eventIngestService.ingest(eventRaw);
        return success();
    }

    @Anonymous
    @GetMapping("/market-history")
    public AjaxResult listMarketHistory(@RequestParam String symbol,
                                        @RequestParam String exchange,
                                        @RequestParam(required = false, defaultValue = "60") Integer limit,
                                        @RequestParam(required = false, defaultValue = "300") Integer maxAgeMinutes) {
        return success(eventIngestService.listRecentMarketHistory(symbol, exchange, limit, maxAgeMinutes));
    }
}
