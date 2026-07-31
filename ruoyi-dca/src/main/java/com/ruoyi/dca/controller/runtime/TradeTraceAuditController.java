package com.ruoyi.dca.controller.runtime;

import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.dca.service.runtime.ITradeReplayService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 交易追踪审计控制器
 * 提供追踪审计详情查询等RESTful API接口
 *
 * @author ruoyi-dca
 */
@RestController
@RequestMapping("/dca/trade/trace")
public class TradeTraceAuditController extends BaseController {

    @Autowired
    private ITradeReplayService tradeReplayService;

    /**
     * 获取追踪审计详情
     *
     * @param traceId 追踪ID
     * @return 追踪审计详情
     */
    @GetMapping("/detail")
    public AjaxResult getTraceAuditDetail(@RequestParam String traceId) {
        return success(tradeReplayService.getTraceAuditDetail(traceId));
    }
}
