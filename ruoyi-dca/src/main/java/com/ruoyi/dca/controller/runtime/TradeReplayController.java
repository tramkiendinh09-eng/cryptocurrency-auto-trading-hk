package com.ruoyi.dca.controller.runtime;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.dca.domain.replay.PaperTradeOrder;
import com.ruoyi.dca.domain.replay.ReplayComparison;
import com.ruoyi.dca.domain.replay.ReplayEvent;
import com.ruoyi.dca.domain.replay.ReplaySession;
import com.ruoyi.dca.domain.replay.ReplayTraceSource;
import com.ruoyi.dca.domain.replay.ShadowDecisionLog;
import com.ruoyi.dca.service.runtime.ITradeReplayService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 交易回放控制器
 * 提供回放会话、事件、纸面交易、影子决策等RESTful API接口
 *
 * @author ruoyi-dca
 */
@RestController
@RequestMapping("/dca/trade/replay")
public class TradeReplayController extends BaseController {

    @Autowired
    private ITradeReplayService tradeReplayService;

    /**
     * 创建回放会话
     *
     * @param replaySession 回放会话
     * @return 操作结果
     */
    @Anonymous
    @PostMapping("/session")
    public AjaxResult createReplaySession(@RequestBody ReplaySession replaySession) {
        tradeReplayService.recordReplaySession(replaySession);
        return success(replaySession);
    }

    /**
     * 更新回放会话
     *
     * @param replaySession 回放会话
     * @return 操作结果
     */
    @Anonymous
    @PutMapping("/session")
    public AjaxResult updateReplaySession(@RequestBody ReplaySession replaySession) {
        tradeReplayService.updateReplaySession(replaySession);
        return success();
    }

    /**
     * 创建回放事件
     *
     * @param replayEvent 回放事件
     * @return 操作结果
     */
    @Anonymous
    @PostMapping("/event")
    public AjaxResult createReplayEvent(@RequestBody ReplayEvent replayEvent) {
        tradeReplayService.recordReplayEvent(replayEvent);
        return success();
    }

    /**
     * 创建纸面交易订单
     *
     * @param paperTradeOrder 纸面交易订单
     * @return 操作结果
     */
    @Anonymous
    @PostMapping("/paper-order")
    public AjaxResult createPaperTradeOrder(@RequestBody PaperTradeOrder paperTradeOrder) {
        tradeReplayService.recordPaperTradeOrder(paperTradeOrder);
        return success();
    }

    /**
     * 创建影子决策日志
     *
     * @param shadowDecisionLog 影子决策日志
     * @return 操作结果
     */
    @Anonymous
    @PostMapping("/shadow-decision")
    public AjaxResult createShadowDecisionLog(@RequestBody ShadowDecisionLog shadowDecisionLog) {
        tradeReplayService.recordShadowDecisionLog(shadowDecisionLog);
        return success();
    }

    /**
     * 查询回放会话列表
     *
     * @return 回放会话列表
     */
    @GetMapping("/sessions")
    public TableDataInfo listReplaySessions() {
        startPage();
        return getDataTable(tradeReplayService.listReplaySessions());
    }

    /**
     * 查询回放事件列表
     *
     * @param sessionId 会话ID
     * @return 回放事件列表
     */
    @GetMapping("/events")
    public AjaxResult listReplayEvents(@RequestParam(required = false) Long sessionId) {
        return success(tradeReplayService.listReplayEvents(sessionId));
    }

    /**
     * 查询纸面交易订单列表
     *
     * @return 纸面交易订单列表
     */
    @GetMapping("/paper-orders")
    public AjaxResult listPaperTradeOrders() {
        return success(tradeReplayService.listPaperTradeOrders());
    }

    /**
     * 查询影子决策日志列表
     *
     * @return 影子决策日志列表
     */
    @GetMapping("/shadow-decisions")
    public AjaxResult listShadowDecisionLogs() {
        return success(tradeReplayService.listShadowDecisionLogs());
    }

    /**
     * 获取回放源数据
     *
     * @param traceId 追踪ID
     * @return 回放源数据
     */
    @Anonymous
    @GetMapping("/source")
    public AjaxResult getReplaySource(@RequestParam String traceId) {
        ReplayTraceSource source = tradeReplayService.getReplaySource(traceId);
        return success(source);
    }

    /**
     * 获取回放对比数据
     *
     * @param sessionId 会话ID
     * @return 回放对比数据
     */
    @GetMapping("/compare")
    public AjaxResult getReplayComparison(@RequestParam Long sessionId) {
        ReplayComparison comparison = tradeReplayService.getReplayComparison(sessionId);
        return success(comparison);
    }

    /**
     * 发起回放
     *
     * @param traceId 追踪ID
     * @return 回放会话
     */
    @PostMapping("/dispatch")
    public AjaxResult dispatchReplay(@RequestParam String traceId) {
        return success(tradeReplayService.dispatchReplay(traceId));
    }
}
