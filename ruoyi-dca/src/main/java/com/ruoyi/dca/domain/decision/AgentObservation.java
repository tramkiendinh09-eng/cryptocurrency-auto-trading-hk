package com.ruoyi.dca.domain.decision;

import com.fasterxml.jackson.annotation.JsonAlias;

public class AgentObservation {
    private Long id;
    private Long agentRunId;
    private String traceId;
    private String agentName;
    private String observationType;
    private String observationJson;
    private String createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getAgentRunId() {
        return agentRunId;
    }

    @JsonAlias("agent_run_id")
    public void setAgentRunId(Long agentRunId) {
        this.agentRunId = agentRunId;
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

    public String getObservationType() {
        return observationType;
    }

    @JsonAlias("observation_type")
    public void setObservationType(String observationType) {
        this.observationType = observationType;
    }

    public String getObservationJson() {
        return observationJson;
    }

    @JsonAlias("observation_json")
    public void setObservationJson(String observationJson) {
        this.observationJson = observationJson;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}
