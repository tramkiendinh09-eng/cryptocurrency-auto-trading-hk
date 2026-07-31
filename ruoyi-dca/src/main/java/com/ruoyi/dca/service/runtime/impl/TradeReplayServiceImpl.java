package com.ruoyi.dca.service.runtime.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.dca.domain.NotifyRecord;
import com.ruoyi.dca.domain.dto.TaskDTO;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.decision.FeatureSnapshot;
import com.ruoyi.dca.domain.decision.SignalEvent;
import com.ruoyi.dca.domain.event.EventRaw;
import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.replay.PaperTradeOrder;
import com.ruoyi.dca.domain.replay.ReplayComparison;
import com.ruoyi.dca.domain.replay.ReplayEvent;
import com.ruoyi.dca.domain.replay.ReplaySession;
import com.ruoyi.dca.domain.replay.ReplayTraceSource;
import com.ruoyi.dca.domain.replay.ShadowDecisionLog;
import com.ruoyi.dca.domain.replay.TraceAuditDetail;
import com.ruoyi.dca.domain.replay.TraceAuditEvent;
import com.ruoyi.dca.domain.replay.TraceAuditSummary;
import com.ruoyi.dca.domain.risk.RiskGuardHit;
import com.ruoyi.dca.mapper.decision.DecisionAuditMapper;
import com.ruoyi.dca.mapper.runtime.TradeReplayMapper;
import com.ruoyi.dca.service.ITaskQueueService;
import com.ruoyi.dca.service.runtime.ITradeReplayService;
import com.ruoyi.dca.support.TradeExecutionStatusNormalizer;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class TradeReplayServiceImpl implements ITradeReplayService {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    @Autowired
    private TradeReplayMapper tradeReplayMapper;

    @Autowired
    private DecisionAuditMapper decisionAuditMapper;

    @Autowired
    private ITaskQueueService taskQueueService;

    @Override
    public void recordReplaySession(ReplaySession replaySession) {
        if (replaySession.getStatus() == null || replaySession.getStatus().isBlank()) {
            replaySession.setStatus("running");
        }
        if (replaySession.getReplayTraceId() == null || replaySession.getReplayTraceId().isBlank()) {
            replaySession.setReplayTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        tradeReplayMapper.insertReplaySession(replaySession);
    }

    @Override
    public void updateReplaySession(ReplaySession replaySession) {
        tradeReplayMapper.updateReplaySession(replaySession);
    }

    @Override
    public void recordReplayEvent(ReplayEvent replayEvent) {
        if (replayEvent.getTraceId() == null || replayEvent.getTraceId().isBlank()) {
            replayEvent.setTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        tradeReplayMapper.insertReplayEvent(replayEvent);
    }

    @Override
    public void recordPaperTradeOrder(PaperTradeOrder paperTradeOrder) {
        if (paperTradeOrder.getTraceId() == null || paperTradeOrder.getTraceId().isBlank()) {
            paperTradeOrder.setTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        TradeExecutionStatusNormalizer.StatusPair statusPair = TradeExecutionStatusNormalizer.normalize(
            paperTradeOrder.getExecutionStatus(),
            paperTradeOrder.getOrderStatus()
        );
        paperTradeOrder.setStatus(statusPair.executionStatus());
        paperTradeOrder.setExecutionStatus(statusPair.executionStatus());
        paperTradeOrder.setOrderStatus(statusPair.orderStatus());
        tradeReplayMapper.insertPaperTradeOrder(paperTradeOrder);
    }

    @Override
    public void recordShadowDecisionLog(ShadowDecisionLog shadowDecisionLog) {
        if (shadowDecisionLog.getTraceId() == null || shadowDecisionLog.getTraceId().isBlank()) {
            shadowDecisionLog.setTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        TradeExecutionStatusNormalizer.StatusPair statusPair = TradeExecutionStatusNormalizer.normalize(
            shadowDecisionLog.getExecutionStatus(),
            shadowDecisionLog.getOrderStatus()
        );
        shadowDecisionLog.setExecutionStatus(statusPair.executionStatus());
        shadowDecisionLog.setOrderStatus(statusPair.orderStatus());
        tradeReplayMapper.insertShadowDecisionLog(shadowDecisionLog);
    }

    @Override
    public List<ReplaySession> listReplaySessions() {
        return tradeReplayMapper.selectReplaySessions();
    }

    @Override
    public List<ReplayEvent> listReplayEvents(Long sessionId) {
        return tradeReplayMapper.selectReplayEvents(sessionId);
    }

    @Override
    public List<PaperTradeOrder> listPaperTradeOrders() {
        return tradeReplayMapper.selectPaperTradeOrders();
    }

    @Override
    public List<ShadowDecisionLog> listShadowDecisionLogs() {
        return tradeReplayMapper.selectShadowDecisionLogs();
    }

    @Override
    public ReplayTraceSource getReplaySource(String traceId) {
        List<EventRaw> eventRaws = tradeReplayMapper.selectEventRawsByTraceId(traceId);
        List<SignalEvent> signalEvents = tradeReplayMapper.selectSignalEventsByTraceId(traceId);
        DecisionRun decisionRun = tradeReplayMapper.selectDecisionRunByTraceId(traceId);
        ExchangeOrder exchangeOrder = tradeReplayMapper.selectLatestExchangeOrderByTraceId(traceId);

        ReplayTraceSource source = new ReplayTraceSource();
        source.setTraceId(traceId);
        source.setMode(firstNonBlank(
            decisionRun != null ? decisionRun.getMode() : null,
            exchangeOrder != null ? exchangeOrder.getMode() : null,
            "paper"
        ));
        source.setEventBundle(buildEventBundle(eventRaws, signalEvents));
        source.setSymbol(firstNonBlank(
            decisionRun != null ? decisionRun.getSymbol() : null,
            exchangeOrder != null ? exchangeOrder.getSymbol() : null,
            !eventRaws.isEmpty() ? eventRaws.get(0).getSymbol() : null,
            !signalEvents.isEmpty() ? signalEvents.get(0).getSymbol() : null,
            ""
        ));
        source.setExchangeCode(firstNonBlank(
            exchangeOrder != null ? exchangeOrder.getExchangeCode() : null,
            !eventRaws.isEmpty() ? eventRaws.get(0).getExchangeCode() : null,
            "binance"
        ));
        return source;
    }

    @Override
    public TraceAuditDetail getTraceAuditDetail(String traceId) {
        List<EventRaw> eventRaws = tradeReplayMapper.selectEventRawsByTraceId(traceId);
        DecisionRun decisionRun = tradeReplayMapper.selectDecisionRunByTraceId(traceId);
        hydrateDecisionRunFromFeatureSnapshot(decisionRun);
        ExchangeOrder exchangeOrder = tradeReplayMapper.selectLatestExchangeOrderByTraceId(traceId);
        List<ExchangeFill> fills = tradeReplayMapper.selectExchangeFillsByTraceId(traceId);
        List<RiskGuardHit> riskHits = tradeReplayMapper.selectRiskGuardHitsByTraceId(traceId);
        var tradeSummary = tradeReplayMapper.selectTradeActionSummaryByTraceId(traceId);
        PositionSnapshot positionSnapshot = tradeReplayMapper.selectLatestPositionSnapshotByTraceId(traceId);
        PnlSnapshot pnlSnapshot = tradeReplayMapper.selectLatestPnlSnapshotByTraceId(traceId);
        List<NotifyRecord> notifications = tradeReplayMapper.selectNotifyRecordsByTraceId(traceId);

        TraceAuditDetail detail = new TraceAuditDetail();
        detail.setSummary(buildTraceAuditSummary(traceId, eventRaws, decisionRun, exchangeOrder, fills, riskHits, notifications));
        detail.setEvents(buildTraceAuditEvents(eventRaws));
        detail.setDecision(decisionRun);
        detail.setRiskHits(riskHits);
        detail.setOrder(exchangeOrder);
        detail.setFills(fills);
        detail.setTradeSummary(tradeSummary);
        detail.setPositionSnapshot(positionSnapshot);
        detail.setPnlSnapshot(pnlSnapshot);
        detail.setNotifications(notifications);
        return detail;
    }

    private void hydrateDecisionRunFromFeatureSnapshot(DecisionRun decisionRun) {
        if (decisionRun == null || decisionRun.getTraceId() == null || decisionRun.getTraceId().isBlank()) {
            return;
        }
        List<FeatureSnapshot> featureSnapshots = decisionAuditMapper.selectLatestFeatureSnapshotsByTraceIds(
            List.of(decisionRun.getTraceId())
        );
        if (featureSnapshots == null || featureSnapshots.isEmpty()) {
            return;
        }
        FeatureSnapshot featureSnapshot = featureSnapshots.get(0);
        if (featureSnapshot == null) {
            return;
        }
        Map<String, Object> snapshot = payloadMap(featureSnapshot.getSnapshotJson(), null);
        featureSnapshot.setSnapshot(snapshot);
        decisionRun.setFeatureSnapshot(featureSnapshot);

        Object shortTermMemory = snapshot.get("shortTermMemory");
        if (shortTermMemory instanceof Map<?, ?> shortTermMap && !shortTermMap.isEmpty()) {
            decisionRun.setShortTermMemory(new LinkedHashMap<>((Map<String, Object>) shortTermMap));
        }
        Object longTermMemory = snapshot.get("longTermMemory");
        if (longTermMemory instanceof Map<?, ?> longTermMap && !longTermMap.isEmpty()) {
            decisionRun.setLongTermMemory(new LinkedHashMap<>((Map<String, Object>) longTermMap));
        }
        Object memoryUsage = snapshot.get("memoryUsage");
        if (memoryUsage instanceof Map<?, ?> usageMap && !usageMap.isEmpty()) {
            decisionRun.setMemoryUsage(new LinkedHashMap<>((Map<String, Object>) usageMap));
        }
        Object tradeMemoryStatus = snapshot.get("tradeMemoryStatus");
        if (tradeMemoryStatus instanceof Map<?, ?> tradeMemoryStatusMap && !tradeMemoryStatusMap.isEmpty()) {
            decisionRun.setTradeMemoryStatus(new LinkedHashMap<>((Map<String, Object>) tradeMemoryStatusMap));
        }
        Object lifecycleStatus = snapshot.get("lifecycleStatus");
        if (lifecycleStatus instanceof Map<?, ?> lifecycleStatusMap && !lifecycleStatusMap.isEmpty()) {
            decisionRun.setLifecycleStatus(new LinkedHashMap<>((Map<String, Object>) lifecycleStatusMap));
        }
    }

    @Override
    public ReplayComparison getReplayComparison(Long sessionId) {
        ReplaySession session = tradeReplayMapper.selectReplaySessionById(sessionId);
        ReplayComparison comparison = new ReplayComparison();
        comparison.setSessionId(sessionId);
        if (session == null) {
            return comparison;
        }
        comparison.setSourceTraceId(session.getSourceTraceId());
        comparison.setReplayTraceId(session.getReplayTraceId());

        DecisionRun originalDecision = tradeReplayMapper.selectDecisionRunByTraceId(session.getSourceTraceId());
        ShadowDecisionLog replayDecision = tradeReplayMapper.selectLatestShadowDecisionLogByTraceId(session.getReplayTraceId());
        ExchangeOrder originalOrder = tradeReplayMapper.selectLatestExchangeOrderByTraceId(session.getSourceTraceId());
        ExchangeOrder replayOrder = tradeReplayMapper.selectLatestExchangeOrderByTraceId(session.getReplayTraceId());
        List<RiskGuardHit> originalRiskHits = tradeReplayMapper.selectRiskGuardHitsByTraceId(session.getSourceTraceId());
        List<RiskGuardHit> replayRiskHits = tradeReplayMapper.selectRiskGuardHitsByTraceId(session.getReplayTraceId());

        Map<String, Object> originalDecisionMap = decisionMap(originalDecision, originalOrder);
        Map<String, Object> replayDecisionMap = shadowDecisionMap(replayDecision);
        Map<String, Object> originalOrderMap = orderMap(originalOrder);
        Map<String, Object> replayOrderMap = orderMap(replayOrder);

        comparison.setOriginalDecision(originalDecisionMap);
        comparison.setReplayDecision(replayDecisionMap);
        comparison.setOriginalOrder(originalOrderMap);
        comparison.setReplayOrder(replayOrderMap);
        comparison.setOriginalRiskHits(originalRiskHits);
        comparison.setReplayRiskHits(replayRiskHits);
        comparison.setActionMatched(sameValue(originalDecisionMap.get("action"), replayDecisionMap.get("action")));
        comparison.setExecutionStatusChanged(!sameValue(originalDecisionMap.get("executionStatus"), replayDecisionMap.get("executionStatus")));
        comparison.setOrderStatusChanged(!sameValue(originalDecisionMap.get("orderStatus"), replayDecisionMap.get("orderStatus")));
        return comparison;
    }

    @Override
    public ReplaySession dispatchReplay(String traceId) {
        ReplayTraceSource source = getReplaySource(traceId);
        if (source.getEventBundle() == null || source.getEventBundle().isEmpty()) {
            throw new IllegalArgumentException("Replay source not found for traceId=" + traceId);
        }
        ReplaySession session = new ReplaySession();
        session.setSessionName("replay-" + traceId);
        session.setSymbol(source.getSymbol());
        session.setExchangeCode(source.getExchangeCode());
        session.setMode("shadow");
        session.setSourceType("trace");
        session.setStatus("queued");
        session.setSourceTraceId(traceId);
        recordReplaySession(session);

        TaskDTO task = new TaskDTO();
        task.setTaskType("TRADE_RUNTIME_REPLAY");
        task.setPriority(1);
        task.setTaskData(Map.of(
            "sessionId", session.getId(),
            "sourceTraceId", traceId
        ));
        taskQueueService.pushPriorityTask(task);
        return session;
    }

    private List<Map<String, Object>> buildEventBundle(List<EventRaw> eventRaws, List<SignalEvent> signalEvents) {
        List<Map<String, Object>> bundle = new ArrayList<>();
        for (EventRaw eventRaw : eventRaws) {
            bundle.add(payloadMap(eventRaw.getPayloadJson(), eventRaw.getEventType()));
        }
        if (!bundle.isEmpty()) {
            return bundle;
        }
        for (SignalEvent signalEvent : signalEvents) {
            bundle.add(payloadMap(signalEvent.getFeatureJson(), signalEvent.getSignalType()));
        }
        return bundle;
    }

    private TraceAuditSummary buildTraceAuditSummary(
        String traceId,
        List<EventRaw> eventRaws,
        DecisionRun decisionRun,
        ExchangeOrder exchangeOrder,
        List<ExchangeFill> fills,
        List<RiskGuardHit> riskHits,
        List<NotifyRecord> notifications
    ) {
        TraceAuditSummary summary = new TraceAuditSummary();
        summary.setTraceId(traceId);
        summary.setSymbol(firstNonBlank(
            decisionRun != null ? decisionRun.getSymbol() : null,
            exchangeOrder != null ? exchangeOrder.getSymbol() : null,
            !eventRaws.isEmpty() ? eventRaws.get(0).getSymbol() : null
        ));
        summary.setExchangeCode(firstNonBlank(
            exchangeOrder != null ? exchangeOrder.getExchangeCode() : null,
            !eventRaws.isEmpty() ? eventRaws.get(0).getExchangeCode() : null,
            "binance"
        ));
        summary.setMode(firstNonBlank(
            decisionRun != null ? decisionRun.getMode() : null,
            exchangeOrder != null ? exchangeOrder.getMode() : null,
            "paper"
        ));
        summary.setAction(decisionRun != null ? decisionRun.getAction() : "");
        summary.setConfidence(decisionRun != null ? decisionRun.getConfidence() : null);
        summary.setExecutionStatus(firstNonBlank(
            decisionRun != null ? decisionRun.getExecutionStatus() : null,
            exchangeOrder != null ? exchangeOrder.getExecutionStatus() : null,
            exchangeOrder != null ? exchangeOrder.getStatus() : null
        ));
        summary.setOrderStatus(firstNonBlank(
            decisionRun != null ? decisionRun.getOrderStatus() : null,
            exchangeOrder != null ? exchangeOrder.getOrderStatus() : null
        ));
        summary.setCreatedAt(firstNonBlank(
            decisionRun != null ? decisionRun.getCreatedAt() : null,
            exchangeOrder != null ? exchangeOrder.getCreatedAt() : null,
            !eventRaws.isEmpty() ? eventRaws.get(0).getCreatedAt() : null
        ));
        summary.setEventCount(eventRaws.size());
        summary.setRiskHitCount(riskHits.size());
        summary.setFillCount(fills.size());
        summary.setNotifyCount(notifications.size());
        return summary;
    }

    private List<TraceAuditEvent> buildTraceAuditEvents(List<EventRaw> eventRaws) {
        List<TraceAuditEvent> events = new ArrayList<>();
        for (EventRaw eventRaw : eventRaws) {
            Map<String, Object> payload = payloadMap(eventRaw.getPayloadJson(), eventRaw.getEventType());
            TraceAuditEvent event = new TraceAuditEvent();
            event.setId(eventRaw.getId());
            event.setEventType(firstNonBlank(eventRaw.getEventType(), stringValue(payload.get("event_type"))));
            event.setSymbol(firstNonBlank(eventRaw.getSymbol(), stringValue(payload.get("symbol"))));
            event.setExchangeCode(firstNonBlank(eventRaw.getExchangeCode(), stringValue(payload.get("exchange"))));
            event.setCreatedAt(eventRaw.getCreatedAt());
            event.setRawJson(eventRaw.getPayloadJson());
            event.setPayload(payload);
            event.setDisplayTitle(resolveEventDisplayTitle(event.getEventType(), payload));
            event.setDisplaySubtitle(resolveEventDisplaySubtitle(event.getEventType(), payload));
            events.add(event);
        }
        return events;
    }

    private Map<String, Object> payloadMap(String payloadJson, String defaultEventType) {
        Map<String, Object> payload = new LinkedHashMap<>();
        if (payloadJson != null && !payloadJson.isBlank()) {
            try {
                payload.putAll(OBJECT_MAPPER.readValue(payloadJson, new TypeReference<Map<String, Object>>() { }));
            } catch (Exception ignored) {
                payload.put("payload_json", payloadJson);
            }
        }
        if (!payload.containsKey("event_type") && defaultEventType != null && !defaultEventType.isBlank()) {
            payload.put("event_type", defaultEventType);
        }
        return payload;
    }

    private String resolveEventDisplayTitle(String eventType, Map<String, Object> payload) {
        if ("news".equalsIgnoreCase(eventType) || "social".equalsIgnoreCase(eventType)) {
            return firstNonBlank(stringValue(payload.get("headline")), stringValue(payload.get("title")), eventType);
        }
        if ("onchain".equalsIgnoreCase(eventType)) {
            return firstNonBlank(
                stringValue(payload.get("wallet")),
                stringValue(payload.get("address")),
                "onchain"
            );
        }
        if ("market_tick".equalsIgnoreCase(eventType)) {
            return firstNonBlank("price=" + stringValue(payload.get("price")), "market_tick");
        }
        if ("source_health".equalsIgnoreCase(eventType)) {
            return firstNonBlank(stringValue(payload.get("source_type")), "source_health");
        }
        return firstNonBlank(stringValue(payload.get("headline")), stringValue(payload.get("event_type")), eventType);
    }

    private String resolveEventDisplaySubtitle(String eventType, Map<String, Object> payload) {
        if ("news".equalsIgnoreCase(eventType) || "social".equalsIgnoreCase(eventType)) {
            return firstNonBlank(stringValue(payload.get("source")), stringValue(payload.get("event_time")));
        }
        if ("onchain".equalsIgnoreCase(eventType)) {
            return firstNonBlank(stringValue(payload.get("flow")), stringValue(payload.get("amountUsd")), stringValue(payload.get("amount_usd")));
        }
        if ("market_tick".equalsIgnoreCase(eventType)) {
            return firstNonBlank(stringValue(payload.get("volume")), stringValue(payload.get("exchange")));
        }
        if ("source_health".equalsIgnoreCase(eventType)) {
            return firstNonBlank(stringValue(payload.get("source_status")), stringValue(payload.get("reason")));
        }
        return "";
    }

    private Map<String, Object> decisionMap(DecisionRun decisionRun, ExchangeOrder exchangeOrder) {
        Map<String, Object> payload = new LinkedHashMap<>();
        if (decisionRun != null) {
            payload.put("traceId", decisionRun.getTraceId());
            payload.put("symbol", decisionRun.getSymbol());
            payload.put("mode", decisionRun.getMode());
            payload.put("action", decisionRun.getAction());
            payload.put("confidence", decisionRun.getConfidence());
            payload.put("modelCode", decisionRun.getModelCode());
            payload.put("modelProvider", decisionRun.getModelProvider());
            payload.put("promptSource", decisionRun.getPromptSource());
            payload.put("bindingTemplateCode", decisionRun.getBindingTemplateCode());
            payload.put("fallbackTemplateCode", decisionRun.getFallbackTemplateCode());
            payload.put("resolvedTemplateCode", decisionRun.getResolvedTemplateCode());
            payload.put("promptTemplateFallbackUsed", decisionRun.getPromptTemplateFallbackUsed());
            payload.put("summaryReason", decisionRun.getSummaryReason());
            payload.put("executionStatus", decisionRun.getExecutionStatus());
            payload.put("orderStatus", decisionRun.getOrderStatus());
        }
        if (exchangeOrder != null) {
            payload.putIfAbsent("side", exchangeOrder.getSide());
            payload.putIfAbsent("executionStatus", exchangeOrder.getExecutionStatus());
            payload.putIfAbsent("orderStatus", exchangeOrder.getOrderStatus());
        }
        return payload;
    }

    private Map<String, Object> shadowDecisionMap(ShadowDecisionLog shadowDecisionLog) {
        Map<String, Object> payload = new LinkedHashMap<>();
        if (shadowDecisionLog == null) {
            return payload;
        }
        payload.put("traceId", shadowDecisionLog.getTraceId());
        payload.put("symbol", shadowDecisionLog.getSymbol());
        payload.put("mode", shadowDecisionLog.getMode());
        payload.put("action", shadowDecisionLog.getAction());
        payload.put("side", shadowDecisionLog.getSide());
        payload.put("confidence", shadowDecisionLog.getConfidence());
        payload.put("modelCode", shadowDecisionLog.getModelCode());
        payload.put("modelProvider", shadowDecisionLog.getModelProvider());
        payload.put("promptSource", shadowDecisionLog.getPromptSource());
        payload.put("bindingTemplateCode", shadowDecisionLog.getBindingTemplateCode());
        payload.put("fallbackTemplateCode", shadowDecisionLog.getFallbackTemplateCode());
        payload.put("resolvedTemplateCode", shadowDecisionLog.getResolvedTemplateCode());
        payload.put("promptTemplateFallbackUsed", shadowDecisionLog.getPromptTemplateFallbackUsed());
        payload.put("summaryReason", shadowDecisionLog.getSummaryReason());
        payload.put("executionStatus", shadowDecisionLog.getExecutionStatus());
        payload.put("orderStatus", shadowDecisionLog.getOrderStatus());
        return payload;
    }

    private Map<String, Object> orderMap(ExchangeOrder exchangeOrder) {
        Map<String, Object> payload = new LinkedHashMap<>();
        if (exchangeOrder == null) {
            return payload;
        }
        payload.put("traceId", exchangeOrder.getTraceId());
        payload.put("exchangeCode", exchangeOrder.getExchangeCode());
        payload.put("symbol", exchangeOrder.getSymbol());
        payload.put("side", exchangeOrder.getSide());
        payload.put("mode", exchangeOrder.getMode());
        payload.put("orderRef", exchangeOrder.getOrderRef());
        payload.put("action", exchangeOrder.getAction());
        payload.put("orderType", exchangeOrder.getOrderType());
        payload.put("positionSide", exchangeOrder.getPositionSide());
        payload.put("reduceOnly", exchangeOrder.getReduceOnly());
        payload.put("tdMode", exchangeOrder.getTdMode());
        payload.put("leverage", exchangeOrder.getLeverage());
        payload.put("limitPrice", exchangeOrder.getLimitPrice());
        payload.put("quantityBase", exchangeOrder.getQuantityBase());
        payload.put("okxEnhancedExecution", exchangeOrder.getOkxEnhancedExecution());
        payload.put("executionStatus", exchangeOrder.getExecutionStatus());
        payload.put("orderStatus", exchangeOrder.getOrderStatus());
        return payload;
    }

    private String firstNonBlank(String... values) {
        if (values == null) {
            return "";
        }
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return "";
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private boolean sameValue(Object left, Object right) {
        return String.valueOf(left == null ? "" : left).equals(String.valueOf(right == null ? "" : right));
    }
}
