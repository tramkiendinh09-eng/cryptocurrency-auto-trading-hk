package com.ruoyi.dca.domain.event;

import java.math.BigDecimal;

public class MarketKlineSnapshot {
    private Long id;
    private String traceId;
    private String symbol;
    private String exchangeCode;
    private String intervalCode;
    private String openTime;
    private String closeTime;
    private BigDecimal openPrice;
    private BigDecimal highPrice;
    private BigDecimal lowPrice;
    private BigDecimal closePrice;
    private BigDecimal volume;
    private BigDecimal quoteVolume;
    private Long tradeCount;
    private String source;
    private String payloadJson;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getTraceId() { return traceId; }
    public void setTraceId(String traceId) { this.traceId = traceId; }
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public String getExchangeCode() { return exchangeCode; }
    public void setExchangeCode(String exchangeCode) { this.exchangeCode = exchangeCode; }
    public String getIntervalCode() { return intervalCode; }
    public void setIntervalCode(String intervalCode) { this.intervalCode = intervalCode; }
    public String getOpenTime() { return openTime; }
    public void setOpenTime(String openTime) { this.openTime = openTime; }
    public String getCloseTime() { return closeTime; }
    public void setCloseTime(String closeTime) { this.closeTime = closeTime; }
    public BigDecimal getOpenPrice() { return openPrice; }
    public void setOpenPrice(BigDecimal openPrice) { this.openPrice = openPrice; }
    public BigDecimal getHighPrice() { return highPrice; }
    public void setHighPrice(BigDecimal highPrice) { this.highPrice = highPrice; }
    public BigDecimal getLowPrice() { return lowPrice; }
    public void setLowPrice(BigDecimal lowPrice) { this.lowPrice = lowPrice; }
    public BigDecimal getClosePrice() { return closePrice; }
    public void setClosePrice(BigDecimal closePrice) { this.closePrice = closePrice; }
    public BigDecimal getVolume() { return volume; }
    public void setVolume(BigDecimal volume) { this.volume = volume; }
    public BigDecimal getQuoteVolume() { return quoteVolume; }
    public void setQuoteVolume(BigDecimal quoteVolume) { this.quoteVolume = quoteVolume; }
    public Long getTradeCount() { return tradeCount; }
    public void setTradeCount(Long tradeCount) { this.tradeCount = tradeCount; }
    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }
    public String getPayloadJson() { return payloadJson; }
    public void setPayloadJson(String payloadJson) { this.payloadJson = payloadJson; }
}
