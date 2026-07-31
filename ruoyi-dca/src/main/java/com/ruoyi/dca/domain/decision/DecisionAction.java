package com.ruoyi.dca.domain.decision;

import com.fasterxml.jackson.annotation.JsonAlias;

/**
 * 决策动作实体类
 *
 * 记录交易决策执行后的动作信息，包括动作类型、方向、订单引用和执行状态等。
 * 用于追踪和审计每次决策的执行结果。
 *
 * @author ruoyi-dca
 */
public class DecisionAction {
    /** 主键ID */
    private Long id;

    /** 决策运行ID */
    private Long decisionRunId;

    /** 追踪ID */
    private String traceId;

    /** 动作类型：OPEN_LONG/OPEN_SHORT/CLOSE/REDUCE/HOLD/SKIP */
    private String action;

    /** 交易方向：long/short */
    private String side;

    /** 订单引用 */
    private String orderRef;

    /** 执行状态：filled/pending/failed/blocked */
    private String executionStatus;

    /** 订单状态：NEW/FILLED/PARTIALLY_FILLED/CANCELED */
    private String orderStatus;

    /** 创建时间 */
    private String createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getDecisionRunId() {
        return decisionRunId;
    }

    @JsonAlias("decision_run_id")
    public void setDecisionRunId(Long decisionRunId) {
        this.decisionRunId = decisionRunId;
    }

    public String getTraceId() {
        return traceId;
    }

    @JsonAlias("trace_id")
    public void setTraceId(String traceId) {
        this.traceId = traceId;
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

    public String getOrderRef() {
        return orderRef;
    }

    @JsonAlias("order_ref")
    public void setOrderRef(String orderRef) {
        this.orderRef = orderRef;
    }

    public String getExecutionStatus() {
        return executionStatus;
    }

    @JsonAlias("execution_status")
    public void setExecutionStatus(String executionStatus) {
        this.executionStatus = executionStatus;
    }

    public String getOrderStatus() {
        return orderStatus;
    }

    @JsonAlias("order_status")
    public void setOrderStatus(String orderStatus) {
        this.orderStatus = orderStatus;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}
