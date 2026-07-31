package com.ruoyi.dca.domain.decision;

import com.fasterxml.jackson.annotation.JsonAlias;

public class AgentConclusion {
    private Long id;
    private String traceId;
    private String agentName;
    private String bias;
    private Integer confidence;
    private String reason;
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

    public String getAgentName() {
        return agentName;
    }

    @JsonAlias("agent_name")
    public void setAgentName(String agentName) {
        this.agentName = agentName;
    }

    public String getBias() {
        return bias;
    }

    public void setBias(String bias) {
        this.bias = bias;
    }

    public Integer getConfidence() {
        return confidence;
    }

    public void setConfidence(Integer confidence) {
        this.confidence = confidence;
    }

    public String getReason() {
        return reason;
    }

    public void setReason(String reason) {
        this.reason = reason;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}

