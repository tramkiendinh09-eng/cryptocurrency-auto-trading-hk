package com.ruoyi.dca.domain.replay;

import com.ruoyi.dca.domain.risk.RiskGuardHit;

import java.util.List;
import java.util.Map;

public class ReplayComparison {
    private Long sessionId;
    private String sourceTraceId;
    private String replayTraceId;
    private boolean actionMatched;
    private boolean executionStatusChanged;
    private boolean orderStatusChanged;
    private Map<String, Object> originalDecision;
    private Map<String, Object> replayDecision;
    private Map<String, Object> originalOrder;
    private Map<String, Object> replayOrder;
    private List<RiskGuardHit> originalRiskHits;
    private List<RiskGuardHit> replayRiskHits;

    public Long getSessionId() {
        return sessionId;
    }

    public void setSessionId(Long sessionId) {
        this.sessionId = sessionId;
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

    public boolean isActionMatched() {
        return actionMatched;
    }

    public void setActionMatched(boolean actionMatched) {
        this.actionMatched = actionMatched;
    }

    public boolean isExecutionStatusChanged() {
        return executionStatusChanged;
    }

    public void setExecutionStatusChanged(boolean executionStatusChanged) {
        this.executionStatusChanged = executionStatusChanged;
    }

    public boolean isOrderStatusChanged() {
        return orderStatusChanged;
    }

    public void setOrderStatusChanged(boolean orderStatusChanged) {
        this.orderStatusChanged = orderStatusChanged;
    }

    public Map<String, Object> getOriginalDecision() {
        return originalDecision;
    }

    public void setOriginalDecision(Map<String, Object> originalDecision) {
        this.originalDecision = originalDecision;
    }

    public Map<String, Object> getReplayDecision() {
        return replayDecision;
    }

    public void setReplayDecision(Map<String, Object> replayDecision) {
        this.replayDecision = replayDecision;
    }

    public Map<String, Object> getOriginalOrder() {
        return originalOrder;
    }

    public void setOriginalOrder(Map<String, Object> originalOrder) {
        this.originalOrder = originalOrder;
    }

    public Map<String, Object> getReplayOrder() {
        return replayOrder;
    }

    public void setReplayOrder(Map<String, Object> replayOrder) {
        this.replayOrder = replayOrder;
    }

    public List<RiskGuardHit> getOriginalRiskHits() {
        return originalRiskHits;
    }

    public void setOriginalRiskHits(List<RiskGuardHit> originalRiskHits) {
        this.originalRiskHits = originalRiskHits;
    }

    public List<RiskGuardHit> getReplayRiskHits() {
        return replayRiskHits;
    }

    public void setReplayRiskHits(List<RiskGuardHit> replayRiskHits) {
        this.replayRiskHits = replayRiskHits;
    }
}
