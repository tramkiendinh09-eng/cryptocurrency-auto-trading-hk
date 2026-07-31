package com.ruoyi.dca.domain.replay;

import java.util.LinkedHashMap;
import java.util.Map;

public class TraceAuditEvent {
    private Long id;
    private String eventType;
    private String symbol;
    private String exchangeCode;
    private String createdAt;
    private String rawJson;
    private Map<String, Object> payload = new LinkedHashMap<>();
    private String displayTitle;
    private String displaySubtitle;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getEventType() {
        return eventType;
    }

    public void setEventType(String eventType) {
        this.eventType = eventType;
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

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }

    public String getRawJson() {
        return rawJson;
    }

    public void setRawJson(String rawJson) {
        this.rawJson = rawJson;
    }

    public Map<String, Object> getPayload() {
        return payload;
    }

    public void setPayload(Map<String, Object> payload) {
        this.payload = payload == null ? new LinkedHashMap<>() : new LinkedHashMap<>(payload);
    }

    public String getDisplayTitle() {
        return displayTitle;
    }

    public void setDisplayTitle(String displayTitle) {
        this.displayTitle = displayTitle;
    }

    public String getDisplaySubtitle() {
        return displaySubtitle;
    }

    public void setDisplaySubtitle(String displaySubtitle) {
        this.displaySubtitle = displaySubtitle;
    }
}
