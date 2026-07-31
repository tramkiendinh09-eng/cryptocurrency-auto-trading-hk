package com.ruoyi.dca.domain.decision;

import com.fasterxml.jackson.annotation.JsonAlias;

public class SignalEvent {
    private Long id;
    private String traceId;
    private String symbol;
    private String signalType;
    private Double score;
    private String featureJson;
    private String createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTraceId() {
        return traceId;
    }

    @JsonAlias("trace_id")
    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getSignalType() {
        return signalType;
    }

    @JsonAlias("signal_type")
    public void setSignalType(String signalType) {
        this.signalType = signalType;
    }

    public String getFeatureJson() {
        return featureJson;
    }

    @JsonAlias("feature_json")
    public void setFeatureJson(String featureJson) {
        this.featureJson = featureJson;
    }

    public Double getScore() {
        return score;
    }

    @JsonAlias("score")
    public void setScore(Double score) {
        this.score = score;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}

