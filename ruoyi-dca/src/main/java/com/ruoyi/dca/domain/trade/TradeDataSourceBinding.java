package com.ruoyi.dca.domain.trade;

public class TradeDataSourceBinding {
    private Long id;
    private String bindingName;
    private Long strategyId;
    private Long sourceId;
    private String eventType;
    private String symbolScopeJson;
    private String exchangeScopeJson;
    private String modeScopeJson;
    private Boolean enabled;
    private String createdAt;
    private String updatedAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getBindingName() { return bindingName; }
    public void setBindingName(String bindingName) { this.bindingName = bindingName; }
    public Long getStrategyId() { return strategyId; }
    public void setStrategyId(Long strategyId) { this.strategyId = strategyId; }
    public Long getSourceId() { return sourceId; }
    public void setSourceId(Long sourceId) { this.sourceId = sourceId; }
    public String getEventType() { return eventType; }
    public void setEventType(String eventType) { this.eventType = eventType; }
    public String getSymbolScopeJson() { return symbolScopeJson; }
    public void setSymbolScopeJson(String symbolScopeJson) { this.symbolScopeJson = symbolScopeJson; }
    public String getExchangeScopeJson() { return exchangeScopeJson; }
    public void setExchangeScopeJson(String exchangeScopeJson) { this.exchangeScopeJson = exchangeScopeJson; }
    public String getModeScopeJson() { return modeScopeJson; }
    public void setModeScopeJson(String modeScopeJson) { this.modeScopeJson = modeScopeJson; }
    public Boolean getEnabled() { return enabled; }
    public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }
    public String getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(String updatedAt) { this.updatedAt = updatedAt; }
}
