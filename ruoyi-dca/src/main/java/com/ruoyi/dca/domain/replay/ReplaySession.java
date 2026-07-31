package com.ruoyi.dca.domain.replay;

public class ReplaySession {
    private Long id;
    private String sessionName;
    private String symbol;
    private String exchangeCode;
    private String mode;
    private String sourceType;
    private String status;
    private String sourceTraceId;
    private String replayTraceId;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getSessionName() {
        return sessionName;
    }

    public void setSessionName(String sessionName) {
        this.sessionName = sessionName;
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

    public String getSourceType() {
        return sourceType;
    }

    public void setSourceType(String sourceType) {
        this.sourceType = sourceType;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getSourceTraceId() {
        return sourceTraceId;
    }

    public void setSourceTraceId(String sourceTraceId) {
        this.sourceTraceId = sourceTraceId;
    }

    public String getReplayTraceId() {
        return replayTraceId;
    }

    public void setReplayTraceId(String replayTraceId) {
        this.replayTraceId = replayTraceId;
    }
}
