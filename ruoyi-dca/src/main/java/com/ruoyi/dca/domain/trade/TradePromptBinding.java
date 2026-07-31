package com.ruoyi.dca.domain.trade;

public class TradePromptBinding {
    private Long id;
    private String bindingName;
    private Long strategyId;
    private Long strategyVersionId;
    private String symbol;
    private String exchangeCode;
    private String bindingScope;
    private String templateCode;
    private String fallbackTemplateCode;
    private Long modelId;
    private String outputSchemaCode;
    private Integer priority;
    private String modeScopeJson;
    private String eventStrengthScopeJson;
    private Boolean enabled;
    private String remark;
    private String createdAt;
    private String updatedAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getBindingName() { return bindingName; }
    public void setBindingName(String bindingName) { this.bindingName = bindingName; }
    public Long getStrategyId() { return strategyId; }
    public void setStrategyId(Long strategyId) { this.strategyId = strategyId; }
    public Long getStrategyVersionId() { return strategyVersionId; }
    public void setStrategyVersionId(Long strategyVersionId) { this.strategyVersionId = strategyVersionId; }
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public String getExchangeCode() { return exchangeCode; }
    public void setExchangeCode(String exchangeCode) { this.exchangeCode = exchangeCode; }
    public String getBindingScope() { return bindingScope; }
    public void setBindingScope(String bindingScope) { this.bindingScope = bindingScope; }
    public String getTemplateCode() { return templateCode; }
    public void setTemplateCode(String templateCode) { this.templateCode = templateCode; }
    public String getFallbackTemplateCode() { return fallbackTemplateCode; }
    public void setFallbackTemplateCode(String fallbackTemplateCode) { this.fallbackTemplateCode = fallbackTemplateCode; }
    public Long getModelId() { return modelId; }
    public void setModelId(Long modelId) { this.modelId = modelId; }
    public String getOutputSchemaCode() { return outputSchemaCode; }
    public void setOutputSchemaCode(String outputSchemaCode) { this.outputSchemaCode = outputSchemaCode; }
    public Integer getPriority() { return priority; }
    public void setPriority(Integer priority) { this.priority = priority; }
    public String getModeScopeJson() { return modeScopeJson; }
    public void setModeScopeJson(String modeScopeJson) { this.modeScopeJson = modeScopeJson; }
    public String getEventStrengthScopeJson() { return eventStrengthScopeJson; }
    public void setEventStrengthScopeJson(String eventStrengthScopeJson) { this.eventStrengthScopeJson = eventStrengthScopeJson; }
    public Boolean getEnabled() { return enabled; }
    public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    public String getRemark() { return remark; }
    public void setRemark(String remark) { this.remark = remark; }
    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }
    public String getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(String updatedAt) { this.updatedAt = updatedAt; }
}
