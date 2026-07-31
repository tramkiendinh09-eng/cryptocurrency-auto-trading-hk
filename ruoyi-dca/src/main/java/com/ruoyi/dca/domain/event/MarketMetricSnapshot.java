package com.ruoyi.dca.domain.event;

import java.math.BigDecimal;

public class MarketMetricSnapshot {
    private Long id;
    private String traceId;
    private String symbol;
    private String exchangeCode;
    private String observedAt;
    private BigDecimal latestPrice;
    private BigDecimal markPrice;
    private BigDecimal markPriceDeviationPct;
    private BigDecimal fundingRate;
    private BigDecimal openInterest;
    private BigDecimal volume24h;
    private BigDecimal quoteVolume24h;
    private BigDecimal liquidationNotional15m;
    private BigDecimal liquidationNotional60m;
    private BigDecimal liquidationNotional240m;
    private BigDecimal largestLiquidationNotionalUsd;
    private String largestLiquidationSide;
    private String sourceStatus;
    private String payloadJson;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getTraceId() { return traceId; }
    public void setTraceId(String traceId) { this.traceId = traceId; }
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public String getExchangeCode() { return exchangeCode; }
    public void setExchangeCode(String exchangeCode) { this.exchangeCode = exchangeCode; }
    public String getObservedAt() { return observedAt; }
    public void setObservedAt(String observedAt) { this.observedAt = observedAt; }
    public BigDecimal getLatestPrice() { return latestPrice; }
    public void setLatestPrice(BigDecimal latestPrice) { this.latestPrice = latestPrice; }
    public BigDecimal getMarkPrice() { return markPrice; }
    public void setMarkPrice(BigDecimal markPrice) { this.markPrice = markPrice; }
    public BigDecimal getMarkPriceDeviationPct() { return markPriceDeviationPct; }
    public void setMarkPriceDeviationPct(BigDecimal markPriceDeviationPct) { this.markPriceDeviationPct = markPriceDeviationPct; }
    public BigDecimal getFundingRate() { return fundingRate; }
    public void setFundingRate(BigDecimal fundingRate) { this.fundingRate = fundingRate; }
    public BigDecimal getOpenInterest() { return openInterest; }
    public void setOpenInterest(BigDecimal openInterest) { this.openInterest = openInterest; }
    public BigDecimal getVolume24h() { return volume24h; }
    public void setVolume24h(BigDecimal volume24h) { this.volume24h = volume24h; }
    public BigDecimal getQuoteVolume24h() { return quoteVolume24h; }
    public void setQuoteVolume24h(BigDecimal quoteVolume24h) { this.quoteVolume24h = quoteVolume24h; }
    public BigDecimal getLiquidationNotional15m() { return liquidationNotional15m; }
    public void setLiquidationNotional15m(BigDecimal liquidationNotional15m) { this.liquidationNotional15m = liquidationNotional15m; }
    public BigDecimal getLiquidationNotional60m() { return liquidationNotional60m; }
    public void setLiquidationNotional60m(BigDecimal liquidationNotional60m) { this.liquidationNotional60m = liquidationNotional60m; }
    public BigDecimal getLiquidationNotional240m() { return liquidationNotional240m; }
    public void setLiquidationNotional240m(BigDecimal liquidationNotional240m) { this.liquidationNotional240m = liquidationNotional240m; }
    public BigDecimal getLargestLiquidationNotionalUsd() { return largestLiquidationNotionalUsd; }
    public void setLargestLiquidationNotionalUsd(BigDecimal largestLiquidationNotionalUsd) { this.largestLiquidationNotionalUsd = largestLiquidationNotionalUsd; }
    public String getLargestLiquidationSide() { return largestLiquidationSide; }
    public void setLargestLiquidationSide(String largestLiquidationSide) { this.largestLiquidationSide = largestLiquidationSide; }
    public String getSourceStatus() { return sourceStatus; }
    public void setSourceStatus(String sourceStatus) { this.sourceStatus = sourceStatus; }
    public String getPayloadJson() { return payloadJson; }
    public void setPayloadJson(String payloadJson) { this.payloadJson = payloadJson; }
}
