package com.ruoyi.dca.domain.decision;

import com.fasterxml.jackson.annotation.JsonAlias;

public class AgentMessage {
    private Long id;
    private String traceId;
    private Long agentRunId;
    private Integer roundNo;
    private String speakerAgent;
    private String targetAgent;
    private String messageType;
    private String templateCode;
    private String modelCode;
    private String contentJson;
    private String summaryText;
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

    public Long getAgentRunId() {
        return agentRunId;
    }

    @JsonAlias("agent_run_id")
    public void setAgentRunId(Long agentRunId) {
        this.agentRunId = agentRunId;
    }

    public Integer getRoundNo() {
        return roundNo;
    }

    @JsonAlias("round_no")
    public void setRoundNo(Integer roundNo) {
        this.roundNo = roundNo;
    }

    public String getSpeakerAgent() {
        return speakerAgent;
    }

    @JsonAlias("speaker_agent")
    public void setSpeakerAgent(String speakerAgent) {
        this.speakerAgent = speakerAgent;
    }

    public String getTargetAgent() {
        return targetAgent;
    }

    @JsonAlias("target_agent")
    public void setTargetAgent(String targetAgent) {
        this.targetAgent = targetAgent;
    }

    public String getMessageType() {
        return messageType;
    }

    @JsonAlias("message_type")
    public void setMessageType(String messageType) {
        this.messageType = messageType;
    }

    public String getTemplateCode() {
        return templateCode;
    }

    @JsonAlias("template_code")
    public void setTemplateCode(String templateCode) {
        this.templateCode = templateCode;
    }

    public String getModelCode() {
        return modelCode;
    }

    @JsonAlias("model_code")
    public void setModelCode(String modelCode) {
        this.modelCode = modelCode;
    }

    public String getContentJson() {
        return contentJson;
    }

    @JsonAlias("content_json")
    public void setContentJson(String contentJson) {
        this.contentJson = contentJson;
    }

    public String getSummaryText() {
        return summaryText;
    }

    @JsonAlias("summary_text")
    public void setSummaryText(String summaryText) {
        this.summaryText = summaryText;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}
