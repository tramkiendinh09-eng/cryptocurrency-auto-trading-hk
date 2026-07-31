package com.ruoyi.dca.mapper.trade;

import com.ruoyi.dca.domain.trade.ExchangeAccountBinding;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.domain.trade.TradeSymbolScope;
import com.ruoyi.dca.domain.trade.TradeStrategyVersion;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 交易策略Mapper接口
 * 提供交易策略的数据库访问操作
 *
 * @author ruoyi-dca
 */
public interface TradeStrategyMapper {

    /**
     * 查询交易策略列表
     *
     * @param query 查询条件
     * @return 策略列表
     */
    List<TradeStrategy> selectTradeStrategyList(TradeStrategy query);

    /**
     * 根据ID查询交易策略
     *
     * @param id 策略ID
     * @return 策略信息
     */
    TradeStrategy selectTradeStrategyById(@Param("id") Long id);

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
    int deleteTradeStrategyByIds(@Param("ids") Long[] ids);

    /**
     * 批量删除策略版本
     *
     * @param ids 策略ID数组
     * @return 影响行数
     */
    int deleteTradeStrategyVersionsByStrategyIds(@Param("ids") Long[] ids);

    /**
     * 根据策略ID删除交易品种范围
     *
     * @param strategyId 策略ID
     * @return 影响行数
     */
    int deleteTradeSymbolScopesByStrategyId(@Param("strategyId") Long strategyId);

    /**
     * 批量删除交易品种范围
     *
     * @param ids 策略ID数组
     * @return 影响行数
     */
    int deleteTradeSymbolScopesByStrategyIds(@Param("ids") Long[] ids);

    /**
     * 批量插入交易品种范围
     *
     * @param scopes 品种范围列表
     * @return 影响行数
     */
    int insertTradeSymbolScopes(@Param("scopes") List<TradeSymbolScope> scopes);

    /**
     * 查询交易品种范围列表
     *
     * @param strategyId 策略ID
     * @return 品种范围列表
     */
    List<TradeSymbolScope> selectTradeSymbolScopes(@Param("strategyId") Long strategyId);

    /**
     * 查询策略账户绑定列表
     *
     * @param strategyId 策略ID
     * @return 账户绑定列表
     */
    List<ExchangeAccountBinding> selectExchangeAccountBindings(@Param("strategyId") Long strategyId);

    /**
     * 根据策略ID删除账户绑定
     *
     * @param strategyId 策略ID
     * @return 影响行数
     */
    int deleteExchangeAccountBindingsByStrategyId(@Param("strategyId") Long strategyId);

    /**
     * 批量删除账户绑定
     *
     * @param ids 策略ID数组
     * @return 影响行数
     */
    int deleteExchangeAccountBindingsByStrategyIds(@Param("ids") Long[] ids);

    /**
     * 批量插入账户绑定
     *
     * @param bindings 账户绑定列表
     * @return 影响行数
     */
    int insertExchangeAccountBindings(@Param("bindings") List<ExchangeAccountBinding> bindings);

    /**
     * 查询最大版本号
     *
     * @param strategyId 策略ID
     * @return 最大版本号
     */
    Integer selectMaxVersionNo(@Param("strategyId") Long strategyId);

    /**
     * 插入策略版本
     *
     * @param tradeStrategyVersion 策略版本
     * @return 影响行数
     */
    int insertTradeStrategyVersion(TradeStrategyVersion tradeStrategyVersion);

    /**
     * 查询最新策略版本
     *
     * @param strategyId 策略ID
     * @return 最新策略版本
     */
    TradeStrategyVersion selectLatestTradeStrategyVersion(@Param("strategyId") Long strategyId);

    /**
     * 查询策略版本列表
     *
     * @param strategyId 策略ID
     * @return 版本列表
     */
    List<TradeStrategyVersion> selectTradeStrategyVersions(@Param("strategyId") Long strategyId);
}
