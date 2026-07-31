package com.ruoyi.dca.domain.trade;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public class TradeNotifyPolicy {
    private Long id;
    private String policyName;
    private String policyScope;
    private Long strategyId;
    private String eventScopeJson;
    private String severityScopeJson;
    private String modeScopeJson;
    private Integer throttleSeconds;
    private String notifyTemplateCode;
    private Boolean enabled;
    private String createdAt;
    private String updatedAt;
    private List<TradeNotifyPolicyChannel> channelBindings;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getPolicyName() { return policyName; }
    public void setPolicyName(String policyName) { this.policyName = policyName; }
    public String getPolicyScope() { return policyScope; }
    public void setPolicyScope(String policyScope) { this.policyScope = policyScope; }
    public Long getStrategyId() { return strategyId; }
    public void setStrategyId(Long strategyId) { this.strategyId = strategyId; }
    public String getEventScopeJson() { return eventScopeJson; }
    public void setEventScopeJson(String eventScopeJson) { this.eventScopeJson = eventScopeJson; }
    public String getSeverityScopeJson() { return severityScopeJson; }
    public void setSeverityScopeJson(String severityScopeJson) { this.severityScopeJson = severityScopeJson; }
    public String getModeScopeJson() { return modeScopeJson; }
    public void setModeScopeJson(String modeScopeJson) { this.modeScopeJson = modeScopeJson; }
    public Integer getThrottleSeconds() { return throttleSeconds; }
    public void setThrottleSeconds(Integer throttleSeconds) { this.throttleSeconds = throttleSeconds; }
    @JsonProperty("notifyTemplateCode")
    public String getNotifyTemplateCode() { return notifyTemplateCode; }
    @JsonAlias("templateCode")
    public void setNotifyTemplateCode(String notifyTemplateCode) { this.notifyTemplateCode = notifyTemplateCode; }
    @JsonIgnore
    public String getTemplateCode() { return notifyTemplateCode; }
    @JsonIgnore
    public void setTemplateCode(String templateCode) { this.notifyTemplateCode = templateCode; }
    public Boolean getEnabled() { return enabled; }
    public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }
    public String getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(String updatedAt) { this.updatedAt = updatedAt; }
    public List<TradeNotifyPolicyChannel> getChannelBindings() { return channelBindings; }
    public void setChannelBindings(List<TradeNotifyPolicyChannel> channelBindings) { this.channelBindings = channelBindings; }
}
