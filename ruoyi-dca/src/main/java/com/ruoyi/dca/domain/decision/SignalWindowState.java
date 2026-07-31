package com.ruoyi.dca.domain.decision;

import com.fasterxml.jackson.annotation.JsonAlias;
import java.math.BigDecimal;

public class SignalWindowState {
    private Long id;
    private String traceId;
    private String symbol;
    private String windowKey;
    private String sourceType;
    private String signalType;
    private String direction;
    private BigDecimal strengthScore;
    private BigDecimal decayScore;
    private String openedAt;
    private String expiresAt;
    private String lastEventAt;
    private String lastConfirmedAt;
    private String dedupeKey;
    private String combineUntilAt;
    private Boolean active;
    private String stateJson;
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

    public String getWindowKey() {
        return windowKey;
    }

    @JsonAlias("window_key")
    public void setWindowKey(String windowKey) {
        this.windowKey = windowKey;
    }

    public String getStateJson() {
        return stateJson;
    }

    @JsonAlias("state_json")
    public void setStateJson(String stateJson) {
        this.stateJson = stateJson;
    }

    public String getSourceType() {
        return sourceType;
    }

    @JsonAlias("source_type")
    public void setSourceType(String sourceType) {
        this.sourceType = sourceType;
    }

    public String getSignalType() {
        return signalType;
    }

    @JsonAlias("signal_type")
    public void setSignalType(String signalType) {
        this.signalType = signalType;
    }

    public String getDirection() {
        return direction;
    }

    public void setDirection(String direction) {
        this.direction = direction;
    }

    public BigDecimal getStrengthScore() {
        return strengthScore;
    }

    @JsonAlias("strength_score")
    public void setStrengthScore(BigDecimal strengthScore) {
        this.strengthScore = strengthScore;
    }

    public BigDecimal getDecayScore() {
        return decayScore;
    }

    @JsonAlias("decay_score")
    public void setDecayScore(BigDecimal decayScore) {
        this.decayScore = decayScore;
    }

    public String getOpenedAt() {
        return openedAt;
    }

    @JsonAlias("opened_at")
    public void setOpenedAt(String openedAt) {
        this.openedAt = openedAt;
    }

    public String getExpiresAt() {
        return expiresAt;
    }

    @JsonAlias("expires_at")
    public void setExpiresAt(String expiresAt) {
        this.expiresAt = expiresAt;
    }

    public String getLastEventAt() {
        return lastEventAt;
    }

    @JsonAlias("last_event_at")
    public void setLastEventAt(String lastEventAt) {
        this.lastEventAt = lastEventAt;
    }

    public String getLastConfirmedAt() {
        return lastConfirmedAt;
    }

    @JsonAlias("last_confirmed_at")
    public void setLastConfirmedAt(String lastConfirmedAt) {
        this.lastConfirmedAt = lastConfirmedAt;
    }

    public String getDedupeKey() {
        return dedupeKey;
    }

    @JsonAlias("dedupe_key")
    public void setDedupeKey(String dedupeKey) {
        this.dedupeKey = dedupeKey;
    }

    public String getCombineUntilAt() {
        return combineUntilAt;
    }

    @JsonAlias("combine_until_at")
    public void setCombineUntilAt(String combineUntilAt) {
        this.combineUntilAt = combineUntilAt;
    }

    public Boolean getActive() {
        return active;
    }

    @JsonAlias("is_active")
    public void setActive(Boolean active) {
        this.active = active;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}
