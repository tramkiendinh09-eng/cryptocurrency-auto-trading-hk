package com.ruoyi.dca.domain.decision;

import com.fasterxml.jackson.annotation.JsonAnySetter;

import java.util.LinkedHashMap;
import java.util.Map;

public class FeatureSnapshot {
    private Long id;
    private String traceId;
    private String symbol;
    private String eventStrength;
    private String snapshotJson;
    private String createdAt;
    private Map<String, Object> snapshot = new LinkedHashMap<>();

    public FeatureSnapshot() {
    }

    public FeatureSnapshot(Map<String, Object> snapshot) {
        setSnapshot(snapshot);
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

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

    public String getEventStrength() {
        return eventStrength;
    }

    public void setEventStrength(String eventStrength) {
        this.eventStrength = eventStrength;
    }

    public String getSnapshotJson() {
        return snapshotJson;
    }

    public void setSnapshotJson(String snapshotJson) {
        this.snapshotJson = snapshotJson;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }

    public Map<String, Object> getSnapshot() {
        return snapshot;
    }

    public void setSnapshot(Map<String, Object> snapshot) {
        this.snapshot = snapshot == null ? new LinkedHashMap<>() : new LinkedHashMap<>(snapshot);
    }

    @JsonAnySetter
    public void putSnapshotValue(String key, Object value) {
        snapshot.put(key, value);
    }
}
