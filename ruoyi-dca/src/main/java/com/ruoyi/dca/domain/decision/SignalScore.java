package com.ruoyi.dca.domain.decision;

import java.math.BigDecimal;

public class SignalScore {
    private Long id;
    private Long signalEventId;
    private String traceId;
    private String signalType;
    private BigDecimal score;
    private String createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getSignalEventId() {
        return signalEventId;
    }

    public void setSignalEventId(Long signalEventId) {
        this.signalEventId = signalEventId;
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getSignalType() {
        return signalType;
    }

    public void setSignalType(String signalType) {
        this.signalType = signalType;
    }

    public BigDecimal getScore() {
        return score;
    }

    public void setScore(BigDecimal score) {
        this.score = score;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}
