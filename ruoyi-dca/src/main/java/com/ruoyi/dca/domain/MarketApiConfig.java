package com.ruoyi.dca.domain;

import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;

/**
 * 市场 API 配置对象 market_api_config
 */
public class MarketApiConfig extends BaseEntity {

    private static final long serialVersionUID = 1L;

    private Long id;
    private Integer versionNo;
    @Excel(name = "配置名称")
    private String configName;
    @Excel(name = "数据分类")
    private String dataCategory;
    private String dataSubType;
    private String transportType;
    private String vendorCode;
    private String marketScope;
    @Excel(name = "API名称")
    private String apiName;
    private String apiUrl;
    private String wsBaseUrl;
    private String wsPath;
    private String wsStreamNameTemplate;
    private Boolean wsCombinedEnabled;
    private Boolean wsSymbolLowercase;
    private Integer wsPingIntervalSeconds;
    private Integer wsPongTimeoutSeconds;
    private Integer wsConnectionTtlHours;
    private Integer wsMaxStreamsPerConnection;
    private Integer wsControlMessagesPerSecond;
    private String docReferenceUrl;
    private String httpMethod;
    private String requestHeaders;
    private String requestBody;
    private String responsePath;
    private String fieldMapping;
    @Excel(name = "超时时间")
    private Integer timeout;
    @Excel(name = "是否启用")
    private String enabled;
    @Excel(name = "优先级")
    private Integer priority;
    private Integer retryCount;
    private Integer retryInterval;
    private String dataTransform;
    private String useProxy;
    private String proxyUrl;
    private String applySymbols;
    @Excel(name = "备注")
    private String remark;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Integer getVersionNo() {
        return versionNo;
    }

    public void setVersionNo(Integer versionNo) {
        this.versionNo = versionNo;
    }

    public String getConfigName() {
        return configName;
    }

    public void setConfigName(String configName) {
        this.configName = configName;
    }

    public String getDataCategory() {
        return dataCategory;
    }

    public void setDataCategory(String dataCategory) {
        this.dataCategory = dataCategory;
    }

    public String getDataSubType() {
        return dataSubType;
    }

    public void setDataSubType(String dataSubType) {
        this.dataSubType = dataSubType;
    }

    public String getTransportType() {
        return transportType;
    }

    public void setTransportType(String transportType) {
        this.transportType = transportType;
    }

    public String getVendorCode() {
        return vendorCode;
    }

    public void setVendorCode(String vendorCode) {
        this.vendorCode = vendorCode;
    }

    public String getMarketScope() {
        return marketScope;
    }

    public void setMarketScope(String marketScope) {
        this.marketScope = marketScope;
    }

    public String getApiName() {
        return apiName;
    }

    public void setApiName(String apiName) {
        this.apiName = apiName;
    }

    public String getApiUrl() {
        return apiUrl;
    }

    public void setApiUrl(String apiUrl) {
        this.apiUrl = apiUrl;
    }

    public String getWsBaseUrl() {
        return wsBaseUrl;
    }

    public void setWsBaseUrl(String wsBaseUrl) {
        this.wsBaseUrl = wsBaseUrl;
    }

    public String getWsPath() {
        return wsPath;
    }

    public void setWsPath(String wsPath) {
        this.wsPath = wsPath;
    }

    public String getWsStreamNameTemplate() {
        return wsStreamNameTemplate;
    }

    public void setWsStreamNameTemplate(String wsStreamNameTemplate) {
        this.wsStreamNameTemplate = wsStreamNameTemplate;
    }

    public Boolean getWsCombinedEnabled() {
        return wsCombinedEnabled;
    }

    public void setWsCombinedEnabled(Boolean wsCombinedEnabled) {
        this.wsCombinedEnabled = wsCombinedEnabled;
    }

    public Boolean getWsSymbolLowercase() {
        return wsSymbolLowercase;
    }

    public void setWsSymbolLowercase(Boolean wsSymbolLowercase) {
        this.wsSymbolLowercase = wsSymbolLowercase;
    }

    public Integer getWsPingIntervalSeconds() {
        return wsPingIntervalSeconds;
    }

    public void setWsPingIntervalSeconds(Integer wsPingIntervalSeconds) {
        this.wsPingIntervalSeconds = wsPingIntervalSeconds;
    }

    public Integer getWsPongTimeoutSeconds() {
        return wsPongTimeoutSeconds;
    }

    public void setWsPongTimeoutSeconds(Integer wsPongTimeoutSeconds) {
        this.wsPongTimeoutSeconds = wsPongTimeoutSeconds;
    }

    public Integer getWsConnectionTtlHours() {
        return wsConnectionTtlHours;
    }

    public void setWsConnectionTtlHours(Integer wsConnectionTtlHours) {
        this.wsConnectionTtlHours = wsConnectionTtlHours;
    }

    public Integer getWsMaxStreamsPerConnection() {
        return wsMaxStreamsPerConnection;
    }

    public void setWsMaxStreamsPerConnection(Integer wsMaxStreamsPerConnection) {
        this.wsMaxStreamsPerConnection = wsMaxStreamsPerConnection;
    }

    public Integer getWsControlMessagesPerSecond() {
        return wsControlMessagesPerSecond;
    }

    public void setWsControlMessagesPerSecond(Integer wsControlMessagesPerSecond) {
        this.wsControlMessagesPerSecond = wsControlMessagesPerSecond;
    }

    public String getDocReferenceUrl() {
        return docReferenceUrl;
    }

    public void setDocReferenceUrl(String docReferenceUrl) {
        this.docReferenceUrl = docReferenceUrl;
    }

    public String getHttpMethod() {
        return httpMethod;
    }

    public void setHttpMethod(String httpMethod) {
        this.httpMethod = httpMethod;
    }

    public String getRequestHeaders() {
        return requestHeaders;
    }

    public void setRequestHeaders(String requestHeaders) {
        this.requestHeaders = requestHeaders;
    }

    public String getRequestBody() {
        return requestBody;
    }

    public void setRequestBody(String requestBody) {
        this.requestBody = requestBody;
    }

    public String getResponsePath() {
        return responsePath;
    }

    public void setResponsePath(String responsePath) {
        this.responsePath = responsePath;
    }

    public String getFieldMapping() {
        return fieldMapping;
    }

    public void setFieldMapping(String fieldMapping) {
        this.fieldMapping = fieldMapping;
    }

    public Integer getTimeout() {
        return timeout;
    }

    public void setTimeout(Integer timeout) {
        this.timeout = timeout;
    }

    public String getEnabled() {
        return enabled;
    }

    public void setEnabled(String enabled) {
        this.enabled = enabled;
    }

    public Integer getPriority() {
        return priority;
    }

    public void setPriority(Integer priority) {
        this.priority = priority;
    }

    public Integer getRetryCount() {
        return retryCount;
    }

    public void setRetryCount(Integer retryCount) {
        this.retryCount = retryCount;
    }

    public Integer getRetryInterval() {
        return retryInterval;
    }

    public void setRetryInterval(Integer retryInterval) {
        this.retryInterval = retryInterval;
    }

    public String getDataTransform() {
        return dataTransform;
    }

    public void setDataTransform(String dataTransform) {
        this.dataTransform = dataTransform;
    }

    public String getUseProxy() {
        return useProxy;
    }

    public void setUseProxy(String useProxy) {
        this.useProxy = useProxy;
    }

    public String getProxyUrl() {
        return proxyUrl;
    }

    public void setProxyUrl(String proxyUrl) {
        this.proxyUrl = proxyUrl;
    }

    public String getApplySymbols() {
        return applySymbols;
    }

    public void setApplySymbols(String applySymbols) {
        this.applySymbols = applySymbols;
    }

    public String getRemark() {
        return remark;
    }

    public void setRemark(String remark) {
        this.remark = remark;
    }
}
