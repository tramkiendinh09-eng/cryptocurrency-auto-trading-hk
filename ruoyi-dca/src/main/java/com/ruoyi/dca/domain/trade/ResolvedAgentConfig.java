package com.ruoyi.dca.domain.trade;

public class ResolvedAgentConfig {
    private String agentCode;
    private String agentType;
    private Boolean enabled;
    private Boolean llmEnabled;
    private Long modelId;
    private String modelCode;
    private String modelProvider;
    private String templateCode;
    private String fallbackTemplateCode;
    private String outputSchemaCode;
    private Long sourceProfileId;
    private Long sourceBindingId;
    private String resolutionSource;

    public String getAgentCode() { return agentCode; }
    public void setAgentCode(String agentCode) { this.agentCode = agentCode; }
    public String getAgentType() { return agentType; }
    public void setAgentType(String agentType) { this.agentType = agentType; }
    public Boolean getEnabled() { return enabled; }
    public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    public Boolean getLlmEnabled() { return llmEnabled; }
    public void setLlmEnabled(Boolean llmEnabled) { this.llmEnabled = llmEnabled; }
    public Long getModelId() { return modelId; }
    public void setModelId(Long modelId) { this.modelId = modelId; }
    public String getModelCode() { return modelCode; }
    public void setModelCode(String modelCode) { this.modelCode = modelCode; }
    public String getModelProvider() { return modelProvider; }
    public void setModelProvider(String modelProvider) { this.modelProvider = modelProvider; }
    public String getTemplateCode() { return templateCode; }
    public void setTemplateCode(String templateCode) { this.templateCode = templateCode; }
    public String getFallbackTemplateCode() { return fallbackTemplateCode; }
    public void setFallbackTemplateCode(String fallbackTemplateCode) { this.fallbackTemplateCode = fallbackTemplateCode; }
    public String getOutputSchemaCode() { return outputSchemaCode; }
    public void setOutputSchemaCode(String outputSchemaCode) { this.outputSchemaCode = outputSchemaCode; }
    public Long getSourceProfileId() { return sourceProfileId; }
    public void setSourceProfileId(Long sourceProfileId) { this.sourceProfileId = sourceProfileId; }
    public Long getSourceBindingId() { return sourceBindingId; }
    public void setSourceBindingId(Long sourceBindingId) { this.sourceBindingId = sourceBindingId; }
    public String getResolutionSource() { return resolutionSource; }
    public void setResolutionSource(String resolutionSource) { this.resolutionSource = resolutionSource; }
}
