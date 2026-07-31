package com.ruoyi.dca.domain.memory;

import java.util.Date;

public class AgentMemoryUsage {
    private Long id;
    private String traceId;
    private String symbol;
    private Long memoryId;
    private String agentCode;
    private String usageContextJson;
    private String outcomeJson;
    private Date createdAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getTraceId() { return traceId; }
    public void setTraceId(String traceId) { this.traceId = traceId; }
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public Long getMemoryId() { return memoryId; }
    public void setMemoryId(Long memoryId) { this.memoryId = memoryId; }
    public String getAgentCode() { return agentCode; }
    public void setAgentCode(String agentCode) { this.agentCode = agentCode; }
    public String getUsageContextJson() { return usageContextJson; }
    public void setUsageContextJson(String usageContextJson) { this.usageContextJson = usageContextJson; }
    public String getOutcomeJson() { return outcomeJson; }
    public void setOutcomeJson(String outcomeJson) { this.outcomeJson = outcomeJson; }
    public Date getCreatedAt() { return createdAt; }
    public void setCreatedAt(Date createdAt) { this.createdAt = createdAt; }
}
