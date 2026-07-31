package com.ruoyi.dca.service;

import java.math.BigDecimal;
import java.util.Map;

/**
 * 价格服务接口
 *
 * @author ruoyi
 * @date 2026-04-03
 */
public interface IPriceService {

    /**
     * 获取当前价格（从Redis缓存或实时获取）
     *
     * @param symbol 交易对（如BTCUSDT）
     * @return 当前价格
     */
    BigDecimal getCurrentPrice(String symbol);

    /**
     * 刷新指定币种价格（触发Python Worker采集）
     *
     * @param symbol 交易对
     */
    void refreshPrice(String symbol);

    /**
     * 获取所有支持的币种价格
     *
     * @return 价格Map（symbol -> price）
     */
    Map<String, BigDecimal> getAllPrices();

    /**
     * 批量刷新价格
     *
     * @param symbols 交易对列表
     */
    void batchRefreshPrice(String... symbols);
}
