package com.ruoyi.dca.domain.trade;

public class TradeDataSourceHealthLog {
    private Long id;
    private Long sourceId;
    private String checkType;
    private String status;
    private Long latencyMs;
    private String responseExcerpt;
    private String errorMessage;
    private String checkedAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getSourceId() { return sourceId; }
    public void setSourceId(Long sourceId) { this.sourceId = sourceId; }
    public String getCheckType() { return checkType; }
    public void setCheckType(String checkType) { this.checkType = checkType; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Long getLatencyMs() { return latencyMs; }
    public void setLatencyMs(Long latencyMs) { this.latencyMs = latencyMs; }
    public String getResponseExcerpt() { return responseExcerpt; }
    public void setResponseExcerpt(String responseExcerpt) { this.responseExcerpt = responseExcerpt; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public String getCheckedAt() { return checkedAt; }
    public void setCheckedAt(String checkedAt) { this.checkedAt = checkedAt; }
}
