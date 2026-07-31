package com.ruoyi.dca.service;

import com.ruoyi.dca.domain.MarketData;

import java.util.List;
import java.util.Map;

/**
 * 市场数据采集服务接口
 *
 * @author ruoyi
 * @date 2026-04-05
 */
public interface IMarketDataCollectService {

    /**
     * 采集单个交易对的市场数据
     *
     * @param symbol 交易对
     * @return 市场数据
     */
    MarketData collectMarketData(String symbol);

    /**
     * 采集所有启用配置的市场数据
     *
     * @return 交易对 -> 市场数据的映射
     */
    Map<String, MarketData> collectAllEnabledConfigs();

    Map<String, MarketData> collectAllEnabledConfigs(String collectType);

    /**
     * 手动触发采集
     *
     * @param symbols 交易对列表
     * @return 采集结果
     */
    Map<String, Object> triggerManualCollection(String... symbols);

    /**
     * 获取最新市场数据
     *
     * @param symbol 交易对
     * @return 市场数据
     */
    MarketData getLatestMarketData(String symbol);

    /**
     * 获取市场数据历史
     *
     * @param symbol 交易对
     * @param days 查询天数
     * @return 历史数据列表
     */
    List<MarketData> getMarketDataHistory(String symbol, int days);

    /**
     * 获取最新的恐慌贪婪指数
     *
     * @return 恐慌指数值
     */
    Integer getFearGreedIndex();
}
