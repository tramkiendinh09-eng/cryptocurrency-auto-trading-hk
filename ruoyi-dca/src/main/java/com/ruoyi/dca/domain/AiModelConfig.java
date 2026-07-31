package com.ruoyi.dca.domain;

import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;
import org.apache.commons.lang3.builder.ToStringBuilder;
import org.apache.commons.lang3.builder.ToStringStyle;
import java.math.BigDecimal;

/**
 * AI模型配置对象 ai_model_config
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class AiModelConfig extends BaseEntity {
    private static final long serialVersionUID = 1L;

    /** 主键ID */
    private Long id;

    /** 模型唯一标识 */
    @Excel(name = "模型标识")
    private String modelKey;

    /** 模型代码: gpt-4/gpt-3.5-turbo/deepseek-chat */
    @Excel(name = "模型代码")
    private String modelCode;

    /** 模型名称 */
    @Excel(name = "模型名称")
    private String modelName;

    /** 模型提供商: openai/deepseek/anthropic */
    @Excel(name = "模型提供商")
    private String provider;

    /** API端点 */
    private String apiEndpoint;

    /** API Base URL */
    private String apiBaseUrl;

    /** API Key */
    private String apiKey;

    /** 加密后的API密钥 */
    private String apiKeyEncrypted;

    /** API版本 */
    private String apiVersion;

    /** 模型版本 */
    private String modelVersion;

    /** 每日调用次数限制 */
    @Excel(name = "每日调用限制")
    private Integer dailyLimit;

    /** 每月Token限制 */
    @Excel(name = "每月Token限制")
    private Long monthlyTokenLimit;

    /** 超时时间(秒) */
    @Excel(name = "超时时间")
    private Integer timeoutSeconds;

    /** 重试次数 */
    @Excel(name = "重试次数")
    private Integer retryTimes;

    /** 优先级 */
    @Excel(name = "优先级")
    private Integer priority;

    /** 最高温度 */
    @Excel(name = "最高温度")
    private BigDecimal maxTemperature;

    /** 温度参数 */
    private BigDecimal temperature;

    /** Top-P参数 */
    private BigDecimal topP;

    /** 最大Token数 */
    @Excel(name = "最大Token")
    private Integer maxTokens;

    /** 是否启用: 0禁用 1启用 */
    @Excel(name = "是否启用")
    private Integer isEnabled;

    /** 是否默认: 0否 1是 */
    @Excel(name = "是否默认")
    private Integer isDefault;

    /** 描述 */
    @Excel(name = "描述")
    private String description;

    /** 当前使用次数 */
    @Excel(name = "使用次数")
    private Integer usageCount;

    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
    }

    public void setModelKey(String modelKey) {
        this.modelKey = modelKey;
    }

    public String getModelKey() {
        return modelKey;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelCode(String modelCode) {
        this.modelCode = modelCode;
    }

    public String getModelCode() {
        return modelCode;
    }

    public void setProvider(String provider) {
        this.provider = provider;
    }

    public String getProvider() {
        return provider;
    }

    public void setApiEndpoint(String apiEndpoint) {
        this.apiEndpoint = apiEndpoint;
    }

    public String getApiEndpoint() {
        return apiEndpoint;
    }

    public void setApiBaseUrl(String apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
    }

    public String getApiBaseUrl() {
        return apiBaseUrl;
    }

    public void setApiKey(String apiKey) {
        this.apiKey = apiKey;
    }

    public String getApiKey() {
        return apiKey;
    }

    public void setApiKeyEncrypted(String apiKeyEncrypted) {
        this.apiKeyEncrypted = apiKeyEncrypted;
    }

    public String getApiKeyEncrypted() {
        return apiKeyEncrypted;
    }

    public void setApiVersion(String apiVersion) {
        this.apiVersion = apiVersion;
    }

    public String getApiVersion() {
        return apiVersion;
    }

    public void setModelVersion(String modelVersion) {
        this.modelVersion = modelVersion;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public void setDailyLimit(Integer dailyLimit) {
        this.dailyLimit = dailyLimit;
    }

    public Integer getDailyLimit() {
        return dailyLimit;
    }

    public void setMonthlyTokenLimit(Long monthlyTokenLimit) {
        this.monthlyTokenLimit = monthlyTokenLimit;
    }

    public Long getMonthlyTokenLimit() {
        return monthlyTokenLimit;
    }

    public void setTimeoutSeconds(Integer timeoutSeconds) {
        this.timeoutSeconds = timeoutSeconds;
    }

    public Integer getTimeoutSeconds() {
        return timeoutSeconds;
    }

    public void setRetryTimes(Integer retryTimes) {
        this.retryTimes = retryTimes;
    }

    public Integer getRetryTimes() {
        return retryTimes;
    }

    public void setPriority(Integer priority) {
        this.priority = priority;
    }

    public Integer getPriority() {
        return priority;
    }

    public void setMaxTemperature(BigDecimal maxTemperature) {
        this.maxTemperature = maxTemperature;
    }

    public BigDecimal getMaxTemperature() {
        return maxTemperature;
    }

    public void setTemperature(BigDecimal temperature) {
        this.temperature = temperature;
    }

    public BigDecimal getTemperature() {
        return temperature;
    }

    public void setTopP(BigDecimal topP) {
        this.topP = topP;
    }

    public BigDecimal getTopP() {
        return topP;
    }

    public void setMaxTokens(Integer maxTokens) {
        this.maxTokens = maxTokens;
    }

    public Integer getMaxTokens() {
        return maxTokens;
    }

    public void setIsEnabled(Integer isEnabled) {
        this.isEnabled = isEnabled;
    }

    public Integer getIsEnabled() {
        return isEnabled;
    }

    public void setIsDefault(Integer isDefault) {
        this.isDefault = isDefault;
    }

    public Integer getIsDefault() {
        return isDefault;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }

    public void setUsageCount(Integer usageCount) {
        this.usageCount = usageCount;
    }

    public Integer getUsageCount() {
        return usageCount;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this, ToStringStyle.MULTI_LINE_STYLE)
            .append("id", getId())
            .append("modelKey", getModelKey())
            .append("modelCode", getModelCode())
            .append("modelName", getModelName())
            .append("provider", getProvider())
            .append("apiEndpoint", getApiEndpoint())
            .append("apiBaseUrl", getApiBaseUrl())
            .append("apiKey", getApiKey())
            .append("apiKeyEncrypted", getApiKeyEncrypted())
            .append("apiVersion", getApiVersion())
            .append("modelVersion", getModelVersion())
            .append("dailyLimit", getDailyLimit())
            .append("monthlyTokenLimit", getMonthlyTokenLimit())
            .append("timeoutSeconds", getTimeoutSeconds())
            .append("retryTimes", getRetryTimes())
            .append("priority", getPriority())
            .append("maxTemperature", getMaxTemperature())
            .append("temperature", getTemperature())
            .append("topP", getTopP())
            .append("maxTokens", getMaxTokens())
            .append("isEnabled", getIsEnabled())
            .append("isDefault", getIsDefault())
            .append("description", getDescription())
            .append("usageCount", getUsageCount())
            .append("remark", getRemark())
            .append("createBy", getCreateBy())
            .append("createTime", getCreateTime())
            .append("updateBy", getUpdateBy())
            .append("updateTime", getUpdateTime())
            .toString();
    }
}
