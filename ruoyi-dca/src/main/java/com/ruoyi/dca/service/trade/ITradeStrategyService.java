package com.ruoyi.dca.service.trade;

import com.ruoyi.dca.domain.trade.ExchangeAccountBinding;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.domain.trade.TradeStrategyVersion;

import java.util.List;

/**
 * 交易策略服务接口
 * 提供交易策略的增删改查、版本管理、账户绑定等业务逻辑
 *
 * @author ruoyi-dca
 */
public interface ITradeStrategyService {

    /**
     * 查询交易策略列表
     *
     * @param query 查询条件
     * @return 策略列表
     */
    List<TradeStrategy> selectTradeStrategyList(TradeStrategy query);

    /**
     * 新增交易策略
     *
     * @param tradeStrategy 交易策略
     * @return 影响行数
     */
    int insertTradeStrategy(TradeStrategy tradeStrategy);

    /**
     * 修改交易策略
     *
     * @param tradeStrategy 交易策略
     * @return 影响行数
     */
    int updateTradeStrategy(TradeStrategy tradeStrategy);

    /**
     * 批量删除交易策略
     *
     * @param ids 策略ID数组
     * @return 影响行数
     */
    int deleteTradeStrategyByIds(Long[] ids);

    /**
     * 查询策略版本列表
     *
     * @param strategyId 策略ID
     * @return 版本列表
     */
    List<TradeStrategyVersion> selectTradeStrategyVersions(Long strategyId);

    /**
     * 查询策略账户绑定列表
     *
     * @param strategyId 策略ID
     * @return 账户绑定列表
     */
    List<ExchangeAccountBinding> selectExchangeAccountBindings(Long strategyId);

    /**
     * 替换策略账户绑定
     *
     * @param strategyId 策略ID
     * @param bindings 账户绑定列表
     * @return 影响行数
     */
    int replaceExchangeAccountBindings(Long strategyId, List<ExchangeAccountBinding> bindings);
}
