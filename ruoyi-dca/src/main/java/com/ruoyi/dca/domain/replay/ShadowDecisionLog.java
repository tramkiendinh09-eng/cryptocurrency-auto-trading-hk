package com.ruoyi.dca.domain.replay;

import com.fasterxml.jackson.annotation.JsonAlias;

public class ShadowDecisionLog {
    private Long id;
    private String traceId;
    private String exchangeCode;
    private String symbol;
    private String mode;
    private String action;
    private String side;
    private Integer confidence;
    private String summaryReason;
    private String modelCode;
    private String modelProvider;
    private String promptSource;
    private String bindingTemplateCode;
    private String fallbackTemplateCode;
    private String resolvedTemplateCode;
    private Boolean promptTemplateFallbackUsed;
    private String executionStatus;
    private String orderStatus;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getExchangeCode() {
        return exchangeCode;
    }

    public void setExchangeCode(String exchangeCode) {
        this.exchangeCode = exchangeCode;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public String getSide() {
        return side;
    }

    public void setSide(String side) {
        this.side = side;
    }

    public Integer getConfidence() {
        return confidence;
    }

    public void setConfidence(Integer confidence) {
        this.confidence = confidence;
    }

    public String getSummaryReason() {
        return summaryReason;
    }

    public void setSummaryReason(String summaryReason) {
        this.summaryReason = summaryReason;
    }

    public String getModelCode() {
        return modelCode;
    }

    @JsonAlias("model_code")
    public void setModelCode(String modelCode) {
        this.modelCode = modelCode;
    }

    public String getModelProvider() {
        return modelProvider;
    }

    @JsonAlias("model_provider")
    public void setModelProvider(String modelProvider) {
        this.modelProvider = modelProvider;
    }

    public String getPromptSource() {
        return promptSource;
    }

    @JsonAlias("prompt_source")
    public void setPromptSource(String promptSource) {
        this.promptSource = promptSource;
    }

    public String getBindingTemplateCode() {
        return bindingTemplateCode;
    }

    @JsonAlias("binding_template_code")
    public void setBindingTemplateCode(String bindingTemplateCode) {
        this.bindingTemplateCode = bindingTemplateCode;
    }

    public String getFallbackTemplateCode() {
        return fallbackTemplateCode;
    }

    @JsonAlias("fallback_template_code")
    public void setFallbackTemplateCode(String fallbackTemplateCode) {
        this.fallbackTemplateCode = fallbackTemplateCode;
    }

    public String getResolvedTemplateCode() {
        return resolvedTemplateCode;
    }

    @JsonAlias("resolved_template_code")
    public void setResolvedTemplateCode(String resolvedTemplateCode) {
        this.resolvedTemplateCode = resolvedTemplateCode;
    }

    public Boolean getPromptTemplateFallbackUsed() {
        return promptTemplateFallbackUsed;
    }

    @JsonAlias("prompt_template_fallback_used")
    public void setPromptTemplateFallbackUsed(Boolean promptTemplateFallbackUsed) {
        this.promptTemplateFallbackUsed = promptTemplateFallbackUsed;
    }

    public String getExecutionStatus() {
        return executionStatus;
    }

    public void setExecutionStatus(String executionStatus) {
        this.executionStatus = executionStatus;
    }

    public String getOrderStatus() {
        return orderStatus;
    }

    public void setOrderStatus(String orderStatus) {
        this.orderStatus = orderStatus;
    }
}
