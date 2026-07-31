package com.ruoyi.dca.domain.replay;

import com.ruoyi.dca.domain.NotifyRecord;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.risk.RiskGuardHit;
import com.ruoyi.dca.domain.trade.TradeActionSummary;

import java.util.ArrayList;
import java.util.List;

public class TraceAuditDetail {
    private TraceAuditSummary summary;
    private List<TraceAuditEvent> events = new ArrayList<>();
    private DecisionRun decision;
    private List<RiskGuardHit> riskHits = new ArrayList<>();
    private ExchangeOrder order;
    private List<ExchangeFill> fills = new ArrayList<>();
    private TradeActionSummary tradeSummary;
    private PositionSnapshot positionSnapshot;
    private PnlSnapshot pnlSnapshot;
    private List<NotifyRecord> notifications = new ArrayList<>();

    public TraceAuditSummary getSummary() {
        return summary;
    }

    public void setSummary(TraceAuditSummary summary) {
        this.summary = summary;
    }

    public List<TraceAuditEvent> getEvents() {
        return events;
    }

    public void setEvents(List<TraceAuditEvent> events) {
        this.events = events == null ? new ArrayList<>() : new ArrayList<>(events);
    }

    public DecisionRun getDecision() {
        return decision;
    }

    public void setDecision(DecisionRun decision) {
        this.decision = decision;
    }

    public List<RiskGuardHit> getRiskHits() {
        return riskHits;
    }

    public void setRiskHits(List<RiskGuardHit> riskHits) {
        this.riskHits = riskHits == null ? new ArrayList<>() : new ArrayList<>(riskHits);
    }

    public ExchangeOrder getOrder() {
        return order;
    }

    public void setOrder(ExchangeOrder order) {
        this.order = order;
    }

    public List<ExchangeFill> getFills() {
        return fills;
    }

    public void setFills(List<ExchangeFill> fills) {
        this.fills = fills == null ? new ArrayList<>() : new ArrayList<>(fills);
    }

    public TradeActionSummary getTradeSummary() {
        return tradeSummary;
    }

    public void setTradeSummary(TradeActionSummary tradeSummary) {
        this.tradeSummary = tradeSummary;
    }

    public PositionSnapshot getPositionSnapshot() {
        return positionSnapshot;
    }

    public void setPositionSnapshot(PositionSnapshot positionSnapshot) {
        this.positionSnapshot = positionSnapshot;
    }

    public PnlSnapshot getPnlSnapshot() {
        return pnlSnapshot;
    }

    public void setPnlSnapshot(PnlSnapshot pnlSnapshot) {
        this.pnlSnapshot = pnlSnapshot;
    }

    public List<NotifyRecord> getNotifications() {
        return notifications;
    }

    public void setNotifications(List<NotifyRecord> notifications) {
        this.notifications = notifications == null ? new ArrayList<>() : new ArrayList<>(notifications);
    }
}
