package com.ruoyi.dca.controller.runtime;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.order.OrderRequest;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionChangeLog;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.risk.RiskGuardHit;
import com.ruoyi.dca.service.runtime.ITradeExecutionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 交易执行控制器
 * 提供订单、成交、风控、持仓等交易执行数据的记录和查询接口
 *
 * @author ruoyi-dca
 */
@RestController
@RequestMapping("/dca/trade/execution")
public class TradeExecutionController extends BaseController {

    @Autowired
    private ITradeExecutionService tradeExecutionService;

    /**
     * 创建订单请求记录
     *
     * @param request 订单请求
     * @return 操作结果
     */
    @Anonymous
    @PostMapping("/order")
    public AjaxResult createOrder(@RequestBody OrderRequest request) {
        tradeExecutionService.recordOrderRequest(request);
        return success();
    }

    /**
     * 创建交易所订单记录
     *
     * @param order 交易所订单
     * @return 操作结果
     */
    @Anonymous
    @PostMapping("/exchange-order")
    public AjaxResult createExchangeOrder(@RequestBody ExchangeOrder order) {
        tradeExecutionService.recordExchangeOrder(order);
        return success();
    }

    /**
     * 创建成交记录
     *
     * @param fill 成交信息
     * @return 操作结果
     */
    @Anonymous
    @PostMapping("/exchange-fill")
    public AjaxResult createExchangeFill(@RequestBody ExchangeFill fill) {
        tradeExecutionService.recordExchangeFill(fill);
        return success();
    }

    /**
     * 创建风控触发记录
     *
     * @param riskGuardHit 风控触发信息
     * @return 操作结果
     */
    @Anonymous
    @PostMapping("/risk-guard-hit")
    public AjaxResult createRiskGuardHit(@RequestBody RiskGuardHit riskGuardHit) {
        tradeExecutionService.recordRiskGuardHit(riskGuardHit);
        return success();
    }

    /**
     * 创建盈亏快照记录
     *
     * @param pnlSnapshot 盈亏快照
     * @return 操作结果
     */
    @Anonymous
    @PostMapping("/pnl-snapshot")
    public AjaxResult createPnlSnapshot(@RequestBody PnlSnapshot pnlSnapshot) {
        tradeExecutionService.recordPnlSnapshot(pnlSnapshot);
        return success();
    }

    /**
     * 创建持仓快照记录
     *
     * @param positionSnapshot 持仓快照
     * @return 操作结果
     */
    @Anonymous
    @PostMapping("/position-snapshot")
    public AjaxResult createPositionSnapshot(@RequestBody PositionSnapshot positionSnapshot) {
        tradeExecutionService.recordPositionSnapshot(positionSnapshot);
        return success();
    }

    /**
     * 查询订单列表
     *
     * @param status 状态
     * @param orderStatus 订单状态
     * @return 订单列表
     */
    @GetMapping("/orders")
    public TableDataInfo listOrders(@RequestParam(required = false) String status,
                                    @RequestParam(required = false) String orderStatus) {
        startPage();
        return getDataTable(tradeExecutionService.listOrders(status, orderStatus));
    }

    @GetMapping("/orders/pending")
    public TableDataInfo listPendingLiveOrders(@RequestParam(required = false) String exchangeCode,
                                               @RequestParam(required = false) String symbol,
                                               @RequestParam(required = false) String mode) {
        startPage();
        return getDataTable(tradeExecutionService.listPendingLiveOrders(exchangeCode, symbol, mode));
    }

    /**
     * 查询成交列表
     *
     * @return 成交列表
     */
    @GetMapping("/fills")
    public TableDataInfo listFills() {
        startPage();
        return getDataTable(tradeExecutionService.listFills());
    }

    /**
     * 查询风控触发记录列表
     *
     * @return 风控触发记录列表
     */
    @GetMapping("/risk-hits")
    public TableDataInfo listRiskHits() {
        startPage();
        return getDataTable(tradeExecutionService.listRiskGuardHits());
    }

    /**
     * 查询持仓列表
     *
     * @return 持仓列表
     */
    @GetMapping("/positions")
    public TableDataInfo listPositions() {
        startPage();
        return getDataTable(tradeExecutionService.listPositions());
    }

    /**
     * 查询持仓变更记录列表
     *
     * @return 持仓变更记录列表
     */
    @GetMapping("/position-changes")
    public TableDataInfo listPositionChanges() {
        startPage();
        return getDataTable(tradeExecutionService.listPositionChanges());
    }
}
