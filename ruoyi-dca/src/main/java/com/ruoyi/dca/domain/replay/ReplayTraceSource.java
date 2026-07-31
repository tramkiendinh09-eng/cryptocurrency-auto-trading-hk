package com.ruoyi.dca.domain.replay;

import java.util.List;
import java.util.Map;

public class ReplayTraceSource {
    private String traceId;
    private String symbol;
    private String exchangeCode;
    private String mode;
    private List<Map<String, Object>> eventBundle;

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getExchangeCode() {
        return exchangeCode;
    }

    public void setExchangeCode(String exchangeCode) {
        this.exchangeCode = exchangeCode;
    }

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

    public List<Map<String, Object>> getEventBundle() {
        return eventBundle;
    }

    public void setEventBundle(List<Map<String, Object>> eventBundle) {
        this.eventBundle = eventBundle;
    }
}
