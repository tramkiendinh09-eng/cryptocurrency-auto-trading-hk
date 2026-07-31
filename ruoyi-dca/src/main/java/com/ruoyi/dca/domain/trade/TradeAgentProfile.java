package com.ruoyi.dca.domain.trade;

import java.math.BigDecimal;

public class TradeAgentProfile {
    private Long id;
    private String agentCode;
    private String agentName;
    private String agentType;
    private Boolean enabled;
    private Boolean llmEnabled;
    private Long defaultModelId;
    private String defaultTemplateCode;
    private String defaultFallbackTemplateCode;
    private String defaultOutputSchemaCode;
    private Boolean dialogueEnabled;
    private Integer maxDialogueRounds;
    private Integer speakOrder;
    private Integer timeoutSeconds;
    private Integer maxRetries;
    private BigDecimal temperatureOverride;
    private BigDecimal topPOverride;
    private Integer maxTokensOverride;
    private String structuredSchemaCode;
    private String toolPolicyJson;
    private String runtimeOptionsJson;
    private String remark;
    private String createdAt;
    private String updatedAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getAgentCode() { return agentCode; }
    public void setAgentCode(String agentCode) { this.agentCode = agentCode; }
    public String getAgentName() { return agentName; }
    public void setAgentName(String agentName) { this.agentName = agentName; }
    public String getAgentType() { return agentType; }
    public void setAgentType(String agentType) { this.agentType = agentType; }
    public Boolean getEnabled() { return enabled; }
    public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    public Boolean getLlmEnabled() { return llmEnabled; }
    public void setLlmEnabled(Boolean llmEnabled) { this.llmEnabled = llmEnabled; }
    public Long getDefaultModelId() { return defaultModelId; }
    public void setDefaultModelId(Long defaultModelId) { this.defaultModelId = defaultModelId; }
    public String getDefaultTemplateCode() { return defaultTemplateCode; }
    public void setDefaultTemplateCode(String defaultTemplateCode) { this.defaultTemplateCode = defaultTemplateCode; }
    public String getDefaultFallbackTemplateCode() { return defaultFallbackTemplateCode; }
    public void setDefaultFallbackTemplateCode(String defaultFallbackTemplateCode) { this.defaultFallbackTemplateCode = defaultFallbackTemplateCode; }
    public String getDefaultOutputSchemaCode() { return defaultOutputSchemaCode; }
    public void setDefaultOutputSchemaCode(String defaultOutputSchemaCode) { this.defaultOutputSchemaCode = defaultOutputSchemaCode; }
    public Boolean getDialogueEnabled() { return dialogueEnabled; }
    public void setDialogueEnabled(Boolean dialogueEnabled) { this.dialogueEnabled = dialogueEnabled; }
    public Integer getMaxDialogueRounds() { return maxDialogueRounds; }
    public void setMaxDialogueRounds(Integer maxDialogueRounds) { this.maxDialogueRounds = maxDialogueRounds; }
    public Integer getSpeakOrder() { return speakOrder; }
    public void setSpeakOrder(Integer speakOrder) { this.speakOrder = speakOrder; }
    public Integer getTimeoutSeconds() { return timeoutSeconds; }
    public void setTimeoutSeconds(Integer timeoutSeconds) { this.timeoutSeconds = timeoutSeconds; }
    public Integer getMaxRetries() { return maxRetries; }
    public void setMaxRetries(Integer maxRetries) { this.maxRetries = maxRetries; }
    public BigDecimal getTemperatureOverride() { return temperatureOverride; }
    public void setTemperatureOverride(BigDecimal temperatureOverride) { this.temperatureOverride = temperatureOverride; }
    public BigDecimal getTopPOverride() { return topPOverride; }
    public void setTopPOverride(BigDecimal topPOverride) { this.topPOverride = topPOverride; }
    public Integer getMaxTokensOverride() { return maxTokensOverride; }
    public void setMaxTokensOverride(Integer maxTokensOverride) { this.maxTokensOverride = maxTokensOverride; }
    public String getStructuredSchemaCode() { return structuredSchemaCode; }
    public void setStructuredSchemaCode(String structuredSchemaCode) { this.structuredSchemaCode = structuredSchemaCode; }
    public String getToolPolicyJson() { return toolPolicyJson; }
    public void setToolPolicyJson(String toolPolicyJson) { this.toolPolicyJson = toolPolicyJson; }
    public String getRuntimeOptionsJson() { return runtimeOptionsJson; }
    public void setRuntimeOptionsJson(String runtimeOptionsJson) { this.runtimeOptionsJson = runtimeOptionsJson; }
    public String getRemark() { return remark; }
    public void setRemark(String remark) { this.remark = remark; }
    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }
    public String getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(String updatedAt) { this.updatedAt = updatedAt; }
}
