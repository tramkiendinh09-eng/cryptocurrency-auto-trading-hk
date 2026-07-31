package com.ruoyi.dca.domain.decision;

import com.fasterxml.jackson.annotation.JsonAlias;

/**
 * Agent运行实体类
 *
 * 记录单个Agent的运行信息，包括Agent名称、事件强度、运行状态等。
 * 用于追踪和审计各专业Agent的执行情况。
 *
 * @author ruoyi-dca
 */
public class AgentRun {
    /** 主键ID */
    private Long id;

    /** 追踪ID */
    private String traceId;

    /** 交易品种 */
    private String symbol;

    /** Agent名称：market_agent/news_agent/onchain_agent/social_agent */
    private String agentName;

    /** 事件强度 */
    private String eventStrength;

    /** 运行状态：success/failed/timeout */
    private String status;

    /** 创建时间 */
    private String createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTraceId() {
        return traceId;
    }

    @JsonAlias("trace_id")
    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getAgentName() {
        return agentName;
    }

    @JsonAlias("agent_name")
    public void setAgentName(String agentName) {
        this.agentName = agentName;
    }

    public String getEventStrength() {
        return eventStrength;
    }

    @JsonAlias("event_strength")
    public void setEventStrength(String eventStrength) {
        this.eventStrength = eventStrength;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}
