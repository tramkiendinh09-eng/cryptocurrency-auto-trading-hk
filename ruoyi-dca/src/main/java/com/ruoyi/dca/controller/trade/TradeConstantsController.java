package com.ruoyi.dca.controller.trade;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.dca.constants.TradeConstants;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * 交易系统常量配置API
 *
 * 提供前端获取系统常量的接口，避免前端硬编码
 */
@RestController
@RequestMapping("/dca/trade/constants")
public class TradeConstantsController extends BaseController {

    /**
     * 获取所有交易系统常量配置
     *
     * @return 常量配置
     */
    @Anonymous
    @GetMapping("/all")
    public AjaxResult getAllConstants() {
        Map<String, Object> constants = new HashMap<>();

        // 交易所配置
        Map<String, Object> exchanges = new HashMap<>();
        exchanges.put("allowed", TradeConstants.V1_ALLOWED_EXCHANGES);
        exchanges.put("binance", TradeConstants.EXCHANGE_BINANCE);
        exchanges.put("okx", TradeConstants.EXCHANGE_OKX);
        constants.put("exchanges", exchanges);

        // 交易对配置
        Map<String, Object> symbols = new HashMap<>();
        symbols.put("allowed", TradeConstants.V1_ALLOWED_SYMBOLS);
        constants.put("symbols", symbols);

        // 运行模式配置
        Map<String, Object> modes = new HashMap<>();
        modes.put("allowed", TradeConstants.ALLOWED_MODES);
        modes.put("paper", TradeConstants.MODE_PAPER);
        modes.put("shadow", TradeConstants.MODE_SHADOW);
        modes.put("live", TradeConstants.MODE_LIVE);
        constants.put("modes", modes);

        // 订单动作配置
        Map<String, Object> actions = new HashMap<>();
        actions.put("open", TradeConstants.ACTION_OPEN);
        actions.put("close", TradeConstants.ACTION_CLOSE);
        actions.put("reduce", TradeConstants.ACTION_REDUCE);
        actions.put("hold", TradeConstants.ACTION_HOLD);
        constants.put("actions", actions);

        // 持仓方向配置
        Map<String, Object> positionSides = new HashMap<>();
        positionSides.put("long", TradeConstants.POSITION_SIDE_LONG);
        positionSides.put("short", TradeConstants.POSITION_SIDE_SHORT);
        positionSides.put("net", TradeConstants.POSITION_SIDE_NET);
        constants.put("positionSides", positionSides);

        // 保证金模式配置
        Map<String, Object> marginModes = new HashMap<>();
        marginModes.put("cross", TradeConstants.MARGIN_MODE_CROSS);
        marginModes.put("isolated", TradeConstants.MARGIN_MODE_ISOLATED);
        constants.put("marginModes", marginModes);

        // 仓位模式配置
        Map<String, Object> positionModes = new HashMap<>();
        positionModes.put("longShort", TradeConstants.POSITION_MODE_LONG_SHORT);
        positionModes.put("net", TradeConstants.POSITION_MODE_NET);
        constants.put("positionModes", positionModes);

        // 订单类型配置
        Map<String, Object> orderTypes = new HashMap<>();
        orderTypes.put("market", TradeConstants.ORDER_TYPE_MARKET);
        orderTypes.put("limit", TradeConstants.ORDER_TYPE_LIMIT);
        constants.put("orderTypes", orderTypes);

        // 订单状态配置
        Map<String, Object> orderStatuses = new HashMap<>();
        orderStatuses.put("new", TradeConstants.ORDER_STATUS_NEW);
        orderStatuses.put("filled", TradeConstants.ORDER_STATUS_FILLED);
        orderStatuses.put("partiallyFilled", TradeConstants.ORDER_STATUS_PARTIALLY_FILLED);
        orderStatuses.put("canceled", TradeConstants.ORDER_STATUS_CANCELED);
        orderStatuses.put("rejected", TradeConstants.ORDER_STATUS_REJECTED);
        orderStatuses.put("expired", TradeConstants.ORDER_STATUS_EXPIRED);
        constants.put("orderStatuses", orderStatuses);

        return success(constants);
    }

    /**
     * 获取支持的交易所列表
     *
     * @return 交易所列表
     */
    @Anonymous
    @GetMapping("/exchanges")
    public AjaxResult getExchanges() {
        return success(TradeConstants.V1_ALLOWED_EXCHANGES);
    }

    /**
     * 获取支持的交易对列表
     *
     * @return 交易对列表
     */
    @Anonymous
    @GetMapping("/symbols")
    public AjaxResult getSymbols() {
        return success(TradeConstants.V1_ALLOWED_SYMBOLS);
    }

    /**
     * 获取支持的运行模式列表
     *
     * @return 运行模式列表
     */
    @Anonymous
    @GetMapping("/modes")
    public AjaxResult getModes() {
        return success(TradeConstants.ALLOWED_MODES);
    }
}