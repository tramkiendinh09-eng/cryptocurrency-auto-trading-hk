package com.ruoyi.dca.constants;

/**
 * 交易系统常量定义
 *
 * 集中管理所有硬编码值，确保前后端一致
 */
public class TradeConstants {

    private TradeConstants() {
        // 私有构造函数，防止实例化
    }

    // ==================== 交易所相关 ====================

    /**
     * 支持的交易所代码
     */
    public static final String EXCHANGE_BINANCE = "BINANCE";
    public static final String EXCHANGE_OKX = "OKX";

    /**
     * V1 版本支持的交易所列表
     */
    public static final java.util.List<String> V1_ALLOWED_EXCHANGES = java.util.List.of(EXCHANGE_BINANCE, EXCHANGE_OKX);

    // ==================== 交易对相关 ====================

    /**
     * V1 版本支持的交易对列表
     */
    public static final java.util.List<String> V1_ALLOWED_SYMBOLS = java.util.List.of("BTCUSDT", "ETHUSDT", "SOLUSDT");

    // ==================== 运行模式相关 ====================

    /**
     * 运行模式：模拟
     */
    public static final String MODE_PAPER = "paper";

    /**
     * 运行模式：影子
     */
    public static final String MODE_SHADOW = "shadow";

    /**
     * 运行模式：实盘
     */
    public static final String MODE_LIVE = "live";

    /**
     * 支持的运行模式列表
     */
    public static final java.util.List<String> ALLOWED_MODES = java.util.List.of(MODE_PAPER, MODE_SHADOW, MODE_LIVE);

    // ==================== 订单相关 ====================

    /**
     * 订单动作：开仓
     */
    public static final String ACTION_OPEN = "OPEN";

    /**
     * 订单动作：平仓
     */
    public static final String ACTION_CLOSE = "CLOSE";

    /**
     * 订单动作：减仓
     */
    public static final String ACTION_REDUCE = "REDUCE";

    /**
     * 订单动作：持有
     */
    public static final String ACTION_HOLD = "HOLD";

    // ==================== 持仓方向相关 ====================

    /**
     * 持仓方向：多仓
     */
    public static final String POSITION_SIDE_LONG = "long";

    /**
     * 持仓方向：空仓
     */
    public static final String POSITION_SIDE_SHORT = "short";

    /**
     * 持仓方向：净持仓（单向持仓模式）
     */
    public static final String POSITION_SIDE_NET = "net";

    // ==================== 保证金模式相关 ====================

    /**
     * 保证金模式：全仓
     */
    public static final String MARGIN_MODE_CROSS = "cross";

    /**
     * 保证金模式：逐仓
     */
    public static final String MARGIN_MODE_ISOLATED = "isolated";

    // ==================== 仓位模式相关 ====================

    /**
     * 仓位模式：双向持仓
     */
    public static final String POSITION_MODE_LONG_SHORT = "long_short_mode";

    /**
     * 仓位模式：单向持仓
     */
    public static final String POSITION_MODE_NET = "net_mode";

    // ==================== 订单类型相关 ====================

    /**
     * 订单类型：市价单
     */
    public static final String ORDER_TYPE_MARKET = "market";

    /**
     * 订单类型：限价单
     */
    public static final String ORDER_TYPE_LIMIT = "limit";

    // ==================== 订单状态相关 ====================

    /**
     * 订单状态：新订单
     */
    public static final String ORDER_STATUS_NEW = "NEW";

    /**
     * 订单状态：已成交
     */
    public static final String ORDER_STATUS_FILLED = "FILLED";

    /**
     * 订单状态：部分成交
     */
    public static final String ORDER_STATUS_PARTIALLY_FILLED = "PARTIALLY_FILLED";

    /**
     * 订单状态：已取消
     */
    public static final String ORDER_STATUS_CANCELED = "CANCELED";

    /**
     * 订单状态：已拒绝
     */
    public static final String ORDER_STATUS_REJECTED = "REJECTED";

    /**
     * 订单状态：已过期
     */
    public static final String ORDER_STATUS_EXPIRED = "EXPIRED";
}
