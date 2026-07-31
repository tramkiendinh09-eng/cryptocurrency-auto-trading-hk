package com.ruoyi.dca.domain.memory;

import java.math.BigDecimal;
import java.util.Date;

public class AgentMemory {
    private Long id;
    private String memoryKey;
    private String agentCode;
    private String symbol;
    private String memoryType;
    private String marketRegime;
    private String eventTagsJson;
    private String direction;
    private String action;
    private String lessonText;
    private String evidenceJson;
    private String outcomeJson;
    private BigDecimal qualityScore;
    private BigDecimal confidence;
    private Integer usageCount;
    private Integer winCount;
    private Integer lossCount;
    private Date lastUsedAt;
    private String sourceTraceId;
    private Boolean enabled;
    private Date createdAt;
    private Date updatedAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getMemoryKey() { return memoryKey; }
    public void setMemoryKey(String memoryKey) { this.memoryKey = memoryKey; }
    public String getAgentCode() { return agentCode; }
    public void setAgentCode(String agentCode) { this.agentCode = agentCode; }
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public String getMemoryType() { return memoryType; }
    public void setMemoryType(String memoryType) { this.memoryType = memoryType; }
    public String getMarketRegime() { return marketRegime; }
    public void setMarketRegime(String marketRegime) { this.marketRegime = marketRegime; }
    public String getEventTagsJson() { return eventTagsJson; }
    public void setEventTagsJson(String eventTagsJson) { this.eventTagsJson = eventTagsJson; }
    public String getDirection() { return direction; }
    public void setDirection(String direction) { this.direction = direction; }
    public String getAction() { return action; }
    public void setAction(String action) { this.action = action; }
    public String getLessonText() { return lessonText; }
    public void setLessonText(String lessonText) { this.lessonText = lessonText; }
    public String getEvidenceJson() { return evidenceJson; }
    public void setEvidenceJson(String evidenceJson) { this.evidenceJson = evidenceJson; }
    public String getOutcomeJson() { return outcomeJson; }
    public void setOutcomeJson(String outcomeJson) { this.outcomeJson = outcomeJson; }
    public BigDecimal getQualityScore() { return qualityScore; }
    public void setQualityScore(BigDecimal qualityScore) { this.qualityScore = qualityScore; }
    public BigDecimal getConfidence() { return confidence; }
    public void setConfidence(BigDecimal confidence) { this.confidence = confidence; }
    public Integer getUsageCount() { return usageCount; }
    public void setUsageCount(Integer usageCount) { this.usageCount = usageCount; }
    public Integer getWinCount() { return winCount; }
    public void setWinCount(Integer winCount) { this.winCount = winCount; }
    public Integer getLossCount() { return lossCount; }
    public void setLossCount(Integer lossCount) { this.lossCount = lossCount; }
    public Date getLastUsedAt() { return lastUsedAt; }
    public void setLastUsedAt(Date lastUsedAt) { this.lastUsedAt = lastUsedAt; }
    public String getSourceTraceId() { return sourceTraceId; }
    public void setSourceTraceId(String sourceTraceId) { this.sourceTraceId = sourceTraceId; }
    public Boolean getEnabled() { return enabled; }
    public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    public Date getCreatedAt() { return createdAt; }
    public void setCreatedAt(Date createdAt) { this.createdAt = createdAt; }
    public Date getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Date updatedAt) { this.updatedAt = updatedAt; }
}
