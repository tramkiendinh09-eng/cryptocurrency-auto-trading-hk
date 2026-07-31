package com.ruoyi.dca.mapper;

import com.ruoyi.dca.domain.MarketDataCollectLog;
import java.util.List;

/**
 * 市场数据采集日志Mapper接口
 *
 * @author ruoyi
 * @date 2026-04-05
 */
public interface MarketDataCollectLogMapper {

    /**
     * 查询市场数据采集日志
     *
     * @param id 市场数据采集日志主键
     * @return 市场数据采集日志
     */
    public MarketDataCollectLog selectMarketDataCollectLogById(Long id);

    /**
     * 查询市场数据采集日志列表
     *
     * @param marketDataCollectLog 市场数据采集日志
     * @return 市场数据采集日志集合
     */
    public List<MarketDataCollectLog> selectMarketDataCollectLogList(MarketDataCollectLog marketDataCollectLog);

    /**
     * 新增市场数据采集日志
     *
     * @param marketDataCollectLog 市场数据采集日志
     * @return 结果
     */
    public int insertMarketDataCollectLog(MarketDataCollectLog marketDataCollectLog);

    /**
     * 修改市场数据采集日志
     *
     * @param marketDataCollectLog 市场数据采集日志
     * @return 结果
     */
    public int updateMarketDataCollectLog(MarketDataCollectLog marketDataCollectLog);

    /**
     * 删除市场数据采集日志
     *
     * @param id 市场数据采集日志主键
     * @return 结果
     */
    public int deleteMarketDataCollectLogById(Long id);

    /**
     * 批量删除市场数据采集日志
     *
     * @param ids 需要删除的数据主键集合
     * @return 结果
     */
    public int deleteMarketDataCollectLogByIds(Long[] ids);

    /**
     * 清空过期日志
     *
     * @param days 保留天数
     * @return 结果
     */
    public int cleanOldLogs(Integer days);
}
