package com.ruoyi.dca.domain;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;

import java.math.BigDecimal;
import java.time.DateTimeException;

/**
 * 市场数据对象 market_data
 *
 * @author ruoyi
 * @date 2026-04-05
 */
public class MarketData extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 数据ID */
    private Long id;

    /** 交易对 */
    @Excel(name = "交易对")
    private String symbol;

    /** 数据时间戳（毫秒） */
    @Excel(name = "数据时间戳")
    private Long timestamp;

    /** 采集时间 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @Excel(name = "采集时间", width = 30, dateFormat = "yyyy-MM-dd HH:mm:ss")
    private String collectionTime;

    /** 当前价格 */
    @Excel(name = "当前价格")
    private BigDecimal price;

    /** 24小时价格变化 */
    @Excel(name = "24H价格变化")
    private BigDecimal priceChange24h;

    /** 24小时涨跌幅（%） */
    @Excel(name = "24H涨跌幅")
    private BigDecimal priceChangePercent24h;

    /** 24小时成交量（USDT） */
    @Excel(name = "24H成交量")
    private BigDecimal volume24h;

    /** 24小时成交量（基础货币） */
    private BigDecimal volume24hBase;

    /** 24小时最高价 */
    @Excel(name = "24H最高价")
    private BigDecimal high24h;

    /** 24小时最低价 */
    @Excel(name = "24H最低价")
    private BigDecimal low24h;

    // K线数据（1小时）
    private BigDecimal kline1hOpen;
    private BigDecimal kline1hHigh;
    private BigDecimal kline1hLow;
    private BigDecimal kline1hClose;
    private BigDecimal kline1hVolume;
    private Long kline1hTimestamp;

    // K线数据（4小时）
    private BigDecimal kline4hOpen;
    private BigDecimal kline4hHigh;
    private BigDecimal kline4hLow;
    private BigDecimal kline4hClose;
    private BigDecimal kline4hVolume;
    private Long kline4hTimestamp;

    // K线数据（1天）
    private BigDecimal kline1dOpen;
    private BigDecimal kline1dHigh;
    private BigDecimal kline1dLow;
    private BigDecimal kline1dClose;
    private BigDecimal kline1dVolume;
    private Long kline1dTimestamp;

    /** 恐慌贪婪指数（0-100） */
    @Excel(name = "恐慌指数")
    private Integer fearGreedIndex;

    /** 恐慌贪婪分类 */
    @Excel(name = "恐慌分类")
    private String fearGreedClassification;

    /** 交易所流入量 */
    private BigDecimal exchangeInflow;

    /** 交易所流出量 */
    private BigDecimal exchangeOutflow;

    /** 净流量 */
    private BigDecimal netFlow;

    /** 大额交易笔数 */
    private Integer whaleTransactions;

    /** 数据来源 */
    @Excel(name = "数据来源")
    private String dataSource;

    /** 原始数据（JSON） */
    private String rawData;

    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setTimestamp(Long timestamp) {
        this.timestamp = timestamp;
    }

    public Long getTimestamp() {
        return timestamp;
    }

    public void setCollectionTime(String collectionTime) {
        this.collectionTime = collectionTime;
    }

    public String getCollectionTime() {
        return collectionTime;
    }

    public void setPrice(BigDecimal price) {
        this.price = price;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public void setPriceChange24h(BigDecimal priceChange24h) {
        this.priceChange24h = priceChange24h;
    }

    public BigDecimal getPriceChange24h() {
        return priceChange24h;
    }

    public void setPriceChangePercent24h(BigDecimal priceChangePercent24h) {
        this.priceChangePercent24h = priceChangePercent24h;
    }

    public BigDecimal getPriceChangePercent24h() {
        return priceChangePercent24h;
    }

    public void setVolume24h(BigDecimal volume24h) {
        this.volume24h = volume24h;
    }

    public BigDecimal getVolume24h() {
        return volume24h;
    }

    public void setVolume24hBase(BigDecimal volume24hBase) {
        this.volume24hBase = volume24hBase;
    }

    public BigDecimal getVolume24hBase() {
        return volume24hBase;
    }

    public void setHigh24h(BigDecimal high24h) {
        this.high24h = high24h;
    }

    public BigDecimal getHigh24h() {
        return high24h;
    }

    public void setLow24h(BigDecimal low24h) {
        this.low24h = low24h;
    }

    public BigDecimal getLow24h() {
        return low24h;
    }

    public BigDecimal getKline1hOpen() {
        return kline1hOpen;
    }

    public void setKline1hOpen(BigDecimal kline1hOpen) {
        this.kline1hOpen = kline1hOpen;
    }

    public BigDecimal getKline1hHigh() {
        return kline1hHigh;
    }

    public void setKline1hHigh(BigDecimal kline1hHigh) {
        this.kline1hHigh = kline1hHigh;
    }

    public BigDecimal getKline1hLow() {
        return kline1hLow;
    }

    public void setKline1hLow(BigDecimal kline1hLow) {
        this.kline1hLow = kline1hLow;
    }

    public BigDecimal getKline1hClose() {
        return kline1hClose;
    }

    public void setKline1hClose(BigDecimal kline1hClose) {
        this.kline1hClose = kline1hClose;
    }

    public BigDecimal getKline1hVolume() {
        return kline1hVolume;
    }

    public void setKline1hVolume(BigDecimal kline1hVolume) {
        this.kline1hVolume = kline1hVolume;
    }

    public Long getKline1hTimestamp() {
        return kline1hTimestamp;
    }

    public void setKline1hTimestamp(Long kline1hTimestamp) {
        this.kline1hTimestamp = kline1hTimestamp;
    }

    public BigDecimal getKline4hOpen() {
        return kline4hOpen;
    }

    public void setKline4hOpen(BigDecimal kline4hOpen) {
        this.kline4hOpen = kline4hOpen;
    }

    public BigDecimal getKline4hHigh() {
        return kline4hHigh;
    }

    public void setKline4hHigh(BigDecimal kline4hHigh) {
        this.kline4hHigh = kline4hHigh;
    }

    public BigDecimal getKline4hLow() {
        return kline4hLow;
    }

    public void setKline4hLow(BigDecimal kline4hLow) {
        this.kline4hLow = kline4hLow;
    }

    public BigDecimal getKline4hClose() {
        return kline4hClose;
    }

    public void setKline4hClose(BigDecimal kline4hClose) {
        this.kline4hClose = kline4hClose;
    }

    public BigDecimal getKline4hVolume() {
        return kline4hVolume;
    }

    public void setKline4hVolume(BigDecimal kline4hVolume) {
        this.kline4hVolume = kline4hVolume;
    }

    public Long getKline4hTimestamp() {
        return kline4hTimestamp;
    }

    public void setKline4hTimestamp(Long kline4hTimestamp) {
        this.kline4hTimestamp = kline4hTimestamp;
    }

    public BigDecimal getKline1dOpen() {
        return kline1dOpen;
    }

    public void setKline1dOpen(BigDecimal kline1dOpen) {
        this.kline1dOpen = kline1dOpen;
    }

    public BigDecimal getKline1dHigh() {
        return kline1dHigh;
    }

    public void setKline1dHigh(BigDecimal kline1dHigh) {
        this.kline1dHigh = kline1dHigh;
    }

    public BigDecimal getKline1dLow() {
        return kline1dLow;
    }

    public void setKline1dLow(BigDecimal kline1dLow) {
        this.kline1dLow = kline1dLow;
    }

    public BigDecimal getKline1dClose() {
        return kline1dClose;
    }

    public void setKline1dClose(BigDecimal kline1dClose) {
        this.kline1dClose = kline1dClose;
    }

    public BigDecimal getKline1dVolume() {
        return kline1dVolume;
    }

    public void setKline1dVolume(BigDecimal kline1dVolume) {
        this.kline1dVolume = kline1dVolume;
    }

    public Long getKline1dTimestamp() {
        return kline1dTimestamp;
    }

    public void setKline1dTimestamp(Long kline1dTimestamp) {
        this.kline1dTimestamp = kline1dTimestamp;
    }

    public Integer getFearGreedIndex() {
        return fearGreedIndex;
    }

    public void setFearGreedIndex(Integer fearGreedIndex) {
        this.fearGreedIndex = fearGreedIndex;
    }

    public String getFearGreedClassification() {
        return fearGreedClassification;
    }

    public void setFearGreedClassification(String fearGreedClassification) {
        this.fearGreedClassification = fearGreedClassification;
    }

    public BigDecimal getExchangeInflow() {
        return exchangeInflow;
    }

    public void setExchangeInflow(BigDecimal exchangeInflow) {
        this.exchangeInflow = exchangeInflow;
    }

    public BigDecimal getExchangeOutflow() {
        return exchangeOutflow;
    }

    public void setExchangeOutflow(BigDecimal exchangeOutflow) {
        this.exchangeOutflow = exchangeOutflow;
    }

    public BigDecimal getNetFlow() {
        return netFlow;
    }

    public void setNetFlow(BigDecimal netFlow) {
        this.netFlow = netFlow;
    }

    public Integer getWhaleTransactions() {
        return whaleTransactions;
    }

    public void setWhaleTransactions(Integer whaleTransactions) {
        this.whaleTransactions = whaleTransactions;
    }

    public String getDataSource() {
        return dataSource;
    }

    public void setDataSource(String dataSource) {
        this.dataSource = dataSource;
    }

    public String getRawData() {
        return rawData;
    }

    public void setRawData(String rawData) {
        this.rawData = rawData;
    }
}
