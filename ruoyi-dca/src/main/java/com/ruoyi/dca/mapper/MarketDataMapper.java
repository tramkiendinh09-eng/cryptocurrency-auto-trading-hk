package com.ruoyi.dca.mapper;

import com.ruoyi.dca.domain.MarketData;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 市场数据Mapper接口
 *
 * @author ruoyi
 * @date 2026-04-05
 */
public interface MarketDataMapper {

    /**
     * 查询市场数据（最新一条）
     *
     * @param symbol 交易对
     * @return 市场数据
     */
    MarketData selectLatestMarketData(@Param("symbol") String symbol);

    /**
     * 查询市场数据历史列表
     *
     * @param symbol 交易对
     * @param startTime 开始时间
     * @param endTime 结束时间
     * @param limit 限制条数
     * @return 市场数据列表
     */
    List<MarketData> selectMarketDataHistory(
        @Param("symbol") String symbol,
        @Param("startTime") LocalDateTime startTime,
        @Param("endTime") LocalDateTime endTime,
        @Param("limit") Integer limit
    );

    /**
     * 插入市场数据
     *
     * @param marketData 市场数据
     * @return 影响行数
     */
    int insertMarketData(MarketData marketData);

    /**
     * 批量插入市场数据
     *
     * @param marketDataList 市场数据列表
     * @return 影响行数
     */
    int batchInsertMarketData(@Param("list") List<MarketData> marketDataList);

    /**
     * 删除指定交易对的旧数据
     *
     * @param symbol 交易对
     * @param beforeTime 在此时间之前的数据
     * @return 影响行数
     */
    int deleteOldData(@Param("symbol") String symbol, @Param("beforeTime") LocalDateTime beforeTime);

    /**
     * 查询所有支持的交易对（去重）
     *
     * @return 交易对列表
     */
    List<String> selectDistinctSymbols();

    /**
     * 获取最新的恐慌贪婪指数
     *
     * @return 市场数据（包含恐慌指数）
     */
    MarketData selectLatestFearGreedIndex();
}
