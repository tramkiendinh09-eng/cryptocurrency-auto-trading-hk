package com.ruoyi.dca.service.decision.impl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.dca.domain.decision.AgentConclusion;
import com.ruoyi.dca.domain.decision.AgentMessage;
import com.ruoyi.dca.domain.decision.AgentObservation;
import com.ruoyi.dca.domain.decision.AgentRun;
import com.ruoyi.dca.domain.decision.DecisionAction;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.decision.FeatureSnapshot;
import com.ruoyi.dca.domain.decision.SignalEvent;
import com.ruoyi.dca.domain.decision.SignalScore;
import com.ruoyi.dca.domain.decision.SignalWindowState;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.mapper.decision.DecisionAuditMapper;
import com.ruoyi.dca.service.decision.IDecisionAuditService;
import com.ruoyi.dca.support.TradeExecutionStatusNormalizer;
import com.ruoyi.dca.support.TradeRuntimeTimeUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class DecisionAuditServiceImpl implements IDecisionAuditService {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    @Autowired
    private DecisionAuditMapper decisionAuditMapper;

    @Override
    public void saveDecisionRun(DecisionRun decisionRun) {
        if (decisionRun.getTraceId() == null || decisionRun.getTraceId().isBlank()) {
            decisionRun.setTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        if (decisionRun.getSummaryReason() == null) {
            decisionRun.setSummaryReason("");
        }
        String executionStatus = decisionRun.getExecutionStatus();
        String orderStatus = decisionRun.getOrderStatus();
        if ((executionStatus == null || executionStatus.isBlank())
            && (orderStatus == null || orderStatus.isBlank())
            && "SKIP".equalsIgnoreCase(decisionRun.getAction())) {
            executionStatus = "skipped";
            orderStatus = "SKIPPED";
        }
        TradeExecutionStatusNormalizer.StatusPair statusPair = TradeExecutionStatusNormalizer.normalize(
            executionStatus,
            orderStatus
        );
        decisionRun.setExecutionStatus(statusPair.executionStatus());
        decisionRun.setOrderStatus(statusPair.orderStatus());
        decisionRun.setCreatedAt(normalizeCreatedAt(decisionRun.getCreatedAt(), null));
        decisionRun.setTradeMemoryStatusJson(writeJson(decisionRun.getTradeMemoryStatus()));
        decisionRun.setLifecycleStatusJson(writeJson(decisionRun.getLifecycleStatus()));

        decisionAuditMapper.insertDecisionRun(decisionRun);
        persistFeatureSnapshot(decisionRun);
        persistDecisionActions(decisionRun);
        persistSignalEvents(decisionRun);
        persistSignalWindowStates(decisionRun);
        Map<String, Long> agentRunIdsByName = persistAgentRunsAndObservations(decisionRun);
        persistAgentConclusions(decisionRun);
        persistAgentMessages(decisionRun, agentRunIdsByName);
    }

    @Override
    public List<DecisionRun> listDecisionRuns(String executionStatus, String orderStatus) {
        List<DecisionRun> decisionRuns;
        if (hasDecisionStatusFilters(executionStatus, orderStatus)) {
            decisionRuns = decisionAuditMapper.selectDecisionRuns(executionStatus, orderStatus);
        } else {
            decisionRuns = decisionAuditMapper.selectDecisionRunsBase();
            attachLatestExchangeOrders(decisionRuns);
        }
        attachFeatureSnapshots(decisionRuns);
        attachAgentMessages(decisionRuns);
        return decisionRuns;
    }

    @Override
    public List<AgentMessage> listRecentSupervisorDecisions(String symbol, String mode, String excludeTraceId, Integer limit) {
        String normalizedSymbol = symbol == null ? "" : symbol.trim().toUpperCase();
        if (normalizedSymbol.isBlank()) {
            return List.of();
        }
        String normalizedMode = mode == null ? "" : mode.trim();
        String normalizedExcludeTraceId = excludeTraceId == null ? "" : excludeTraceId.trim();
        int normalizedLimit = limit == null ? 2 : Math.max(1, Math.min(limit, 30));
        List<AgentMessage> messageRows = decisionAuditMapper.selectRecentSupervisorDecisionMessages(
            normalizedSymbol,
            normalizedMode,
            normalizedExcludeTraceId,
            normalizedLimit
        );
        if (messageRows == null) {
            messageRows = List.of();
        }
        int fallbackLimit = Math.min(Math.max(normalizedLimit * 3, normalizedLimit + 2), 30);
        List<DecisionRun> decisionRuns = decisionAuditMapper.selectRecentSupervisorDecisionRuns(
            normalizedSymbol,
            normalizedMode,
            normalizedExcludeTraceId,
            fallbackLimit
        );
        if (decisionRuns == null) {
            decisionRuns = List.of();
        }
        Map<String, AgentMessage> mergedByTraceId = new LinkedHashMap<>();
        List<AgentMessage> merged = new ArrayList<>();
        for (AgentMessage messageRow : messageRows) {
            addRecentSupervisorDecisionMessage(merged, mergedByTraceId, messageRow);
        }
        for (DecisionRun decisionRun : decisionRuns) {
            addRecentSupervisorDecisionMessage(
                merged,
                mergedByTraceId,
                buildFallbackSupervisorDecisionMessage(decisionRun)
            );
        }
        merged.sort(Comparator.comparing(this::sortKeyForRecentSupervisorDecision).reversed());
        if (merged.size() <= normalizedLimit) {
            return merged;
        }
        return new ArrayList<>(merged.subList(0, normalizedLimit));
    }

    private void persistSignalEvents(DecisionRun decisionRun) {
        if (decisionRun.getSignalEvents() == null) {
            return;
        }
        for (SignalEvent signalEvent : decisionRun.getSignalEvents()) {
            if (signalEvent.getTraceId() == null || signalEvent.getTraceId().isBlank()) {
                signalEvent.setTraceId(decisionRun.getTraceId());
            }
            if (signalEvent.getSymbol() == null || signalEvent.getSymbol().isBlank()) {
                signalEvent.setSymbol(decisionRun.getSymbol());
            }
            signalEvent.setCreatedAt(normalizeCreatedAt(signalEvent.getCreatedAt(), decisionRun.getCreatedAt()));
            decisionAuditMapper.insertSignalEvent(signalEvent);
            persistSignalScore(signalEvent, decisionRun.getTraceId());
        }
    }

    private void persistFeatureSnapshot(DecisionRun decisionRun) {
        FeatureSnapshot featureSnapshot = decisionRun.getFeatureSnapshot();
        boolean hasAuditSidePayload = (decisionRun.getMarketSourceConfig() != null && !decisionRun.getMarketSourceConfig().isEmpty())
            || (decisionRun.getShortTermMemory() != null && !decisionRun.getShortTermMemory().isEmpty())
            || (decisionRun.getLongTermMemory() != null && !decisionRun.getLongTermMemory().isEmpty())
            || (decisionRun.getMemoryUsage() != null && !decisionRun.getMemoryUsage().isEmpty())
            || (decisionRun.getTradeMemoryStatus() != null && !decisionRun.getTradeMemoryStatus().isEmpty())
            || (decisionRun.getLifecycleStatus() != null && !decisionRun.getLifecycleStatus().isEmpty());
        if (featureSnapshot == null && hasAuditSidePayload) {
            featureSnapshot = new FeatureSnapshot();
            decisionRun.setFeatureSnapshot(featureSnapshot);
        }
        if (featureSnapshot == null) {
            return;
        }
        if (featureSnapshot.getTraceId() == null || featureSnapshot.getTraceId().isBlank()) {
            featureSnapshot.setTraceId(decisionRun.getTraceId());
        }
        if (featureSnapshot.getSymbol() == null || featureSnapshot.getSymbol().isBlank()) {
            featureSnapshot.setSymbol(decisionRun.getSymbol());
        }
        if (featureSnapshot.getEventStrength() == null || featureSnapshot.getEventStrength().isBlank()) {
            featureSnapshot.setEventStrength(decisionRun.getEventStrength());
        }
        Map<String, Object> snapshot = featureSnapshot.getSnapshot();
        if (decisionRun.getMarketSourceConfig() != null && !decisionRun.getMarketSourceConfig().isEmpty()) {
            snapshot.put("marketSourceConfig", decisionRun.getMarketSourceConfig());
        }
        if (decisionRun.getShortTermMemory() != null && !decisionRun.getShortTermMemory().isEmpty()) {
            snapshot.put("shortTermMemory", decisionRun.getShortTermMemory());
        }
        if (decisionRun.getLongTermMemory() != null && !decisionRun.getLongTermMemory().isEmpty()) {
            snapshot.put("longTermMemory", decisionRun.getLongTermMemory());
        }
        if (decisionRun.getMemoryUsage() != null && !decisionRun.getMemoryUsage().isEmpty()) {
            snapshot.put("memoryUsage", decisionRun.getMemoryUsage());
        }
        if (decisionRun.getTradeMemoryStatus() != null && !decisionRun.getTradeMemoryStatus().isEmpty()) {
            snapshot.put("tradeMemoryStatus", decisionRun.getTradeMemoryStatus());
        }
        if (decisionRun.getLifecycleStatus() != null && !decisionRun.getLifecycleStatus().isEmpty()) {
            snapshot.put("lifecycleStatus", decisionRun.getLifecycleStatus());
        }
        featureSnapshot.setSnapshot(snapshot);
        featureSnapshot.setSnapshotJson(writeJson(featureSnapshot.getSnapshot()));
        featureSnapshot.setCreatedAt(normalizeCreatedAt(featureSnapshot.getCreatedAt(), decisionRun.getCreatedAt()));
        decisionAuditMapper.insertFeatureSnapshot(featureSnapshot);
    }

    private void persistSignalScore(SignalEvent signalEvent, String traceId) {
        if (signalEvent.getScore() == null) {
            return;
        }
        SignalScore signalScore = new SignalScore();
        signalScore.setSignalEventId(signalEvent.getId());
        signalScore.setTraceId(traceId);
        signalScore.setSignalType(signalEvent.getSignalType());
        signalScore.setScore(BigDecimal.valueOf(signalEvent.getScore()));
        signalScore.setCreatedAt(normalizeCreatedAt(signalEvent.getCreatedAt(), null));
        decisionAuditMapper.insertSignalScore(signalScore);
    }

    private void persistSignalWindowStates(DecisionRun decisionRun) {
        if (decisionRun.getSignalWindowStates() == null || decisionRun.getSignalWindowStates().isEmpty()) {
            return;
        }
        String signalWindowSymbol = resolveSignalWindowSymbol(decisionRun);
        if (signalWindowSymbol != null && !signalWindowSymbol.isBlank()) {
            decisionAuditMapper.deactivateExpiredSignalWindowStates(
                signalWindowSymbol,
                TradeRuntimeTimeUtils.nowSqlDateTime()
            );
        }
        for (SignalWindowState signalWindowState : decisionRun.getSignalWindowStates()) {
            if (signalWindowState.getTraceId() == null || signalWindowState.getTraceId().isBlank()) {
                signalWindowState.setTraceId(decisionRun.getTraceId());
            }
            if (signalWindowState.getSymbol() == null || signalWindowState.getSymbol().isBlank()) {
                signalWindowState.setSymbol(decisionRun.getSymbol());
            }
            normalizeSignalWindowTimes(signalWindowState);
            signalWindowState.setCreatedAt(normalizeCreatedAt(signalWindowState.getCreatedAt(), decisionRun.getCreatedAt()));
            decisionAuditMapper.insertSignalWindowState(signalWindowState);
        }
    }

    private void normalizeSignalWindowTimes(SignalWindowState signalWindowState) {
        signalWindowState.setOpenedAt(TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(signalWindowState.getOpenedAt()));
        signalWindowState.setExpiresAt(TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(signalWindowState.getExpiresAt()));
        signalWindowState.setLastEventAt(TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(signalWindowState.getLastEventAt()));
        signalWindowState.setLastConfirmedAt(TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(signalWindowState.getLastConfirmedAt()));
        signalWindowState.setCombineUntilAt(TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(signalWindowState.getCombineUntilAt()));
    }

    private String resolveSignalWindowSymbol(DecisionRun decisionRun) {
        if (decisionRun.getSymbol() != null && !decisionRun.getSymbol().isBlank()) {
            return decisionRun.getSymbol();
        }
        if (decisionRun.getSignalWindowStates() == null) {
            return null;
        }
        for (SignalWindowState signalWindowState : decisionRun.getSignalWindowStates()) {
            if (signalWindowState == null || signalWindowState.getSymbol() == null || signalWindowState.getSymbol().isBlank()) {
                continue;
            }
            return signalWindowState.getSymbol();
        }
        return null;
    }

    private Map<String, Long> persistAgentRunsAndObservations(DecisionRun decisionRun) {
        Map<String, Long> agentRunIdsByName = new LinkedHashMap<>();
        if (decisionRun.getAgentRuns() != null) {
            for (AgentRun agentRun : decisionRun.getAgentRuns()) {
                if (agentRun.getTraceId() == null || agentRun.getTraceId().isBlank()) {
                    agentRun.setTraceId(decisionRun.getTraceId());
                }
                if (agentRun.getSymbol() == null || agentRun.getSymbol().isBlank()) {
                    agentRun.setSymbol(decisionRun.getSymbol());
                }
                if (agentRun.getEventStrength() == null || agentRun.getEventStrength().isBlank()) {
                    agentRun.setEventStrength(decisionRun.getEventStrength());
                }
                if (agentRun.getStatus() == null || agentRun.getStatus().isBlank()) {
                    agentRun.setStatus("completed");
                }
                agentRun.setCreatedAt(normalizeCreatedAt(agentRun.getCreatedAt(), decisionRun.getCreatedAt()));
                decisionAuditMapper.insertAgentRun(agentRun);
                agentRunIdsByName.put(agentRun.getAgentName(), agentRun.getId());
            }
        }
        if (decisionRun.getAgentObservations() == null) {
            return agentRunIdsByName;
        }
        for (AgentObservation agentObservation : decisionRun.getAgentObservations()) {
            if (agentObservation.getTraceId() == null || agentObservation.getTraceId().isBlank()) {
                agentObservation.setTraceId(decisionRun.getTraceId());
            }
            agentObservation.setCreatedAt(normalizeCreatedAt(agentObservation.getCreatedAt(), decisionRun.getCreatedAt()));
            if ((agentObservation.getAgentRunId() == null || agentObservation.getAgentRunId() == 0L)
                && agentObservation.getAgentName() != null) {
                Long agentRunId = agentRunIdsByName.get(agentObservation.getAgentName());
                if (agentRunId != null) {
                    agentObservation.setAgentRunId(agentRunId);
                }
            }
            decisionAuditMapper.insertAgentObservation(agentObservation);
        }
        return agentRunIdsByName;
    }

    private void persistAgentConclusions(DecisionRun decisionRun) {
        if (decisionRun.getAgentConclusions() == null) {
            return;
        }
        for (AgentConclusion agentConclusion : decisionRun.getAgentConclusions()) {
            if (agentConclusion.getTraceId() == null || agentConclusion.getTraceId().isBlank()) {
                agentConclusion.setTraceId(decisionRun.getTraceId());
            }
            agentConclusion.setCreatedAt(normalizeCreatedAt(agentConclusion.getCreatedAt(), decisionRun.getCreatedAt()));
            decisionAuditMapper.insertAgentConclusion(agentConclusion);
        }
    }

    private void persistAgentMessages(DecisionRun decisionRun, Map<String, Long> agentRunIdsByName) {
        if (decisionRun.getAgentMessages() == null) {
            return;
        }
        for (AgentMessage agentMessage : decisionRun.getAgentMessages()) {
            if (agentMessage.getTraceId() == null || agentMessage.getTraceId().isBlank()) {
                agentMessage.setTraceId(decisionRun.getTraceId());
            }
            agentMessage.setCreatedAt(normalizeCreatedAt(agentMessage.getCreatedAt(), decisionRun.getCreatedAt()));
            if ((agentMessage.getAgentRunId() == null || agentMessage.getAgentRunId() == 0L)
                && agentMessage.getSpeakerAgent() != null) {
                Long agentRunId = agentRunIdsByName.get(agentMessage.getSpeakerAgent());
                if (agentRunId == null) {
                    agentRunId = agentRunIdsByName.get(normalizeAgentRunName(agentMessage.getSpeakerAgent()));
                }
                if (agentRunId != null) {
                    agentMessage.setAgentRunId(agentRunId);
                }
            }
            decisionAuditMapper.insertAgentMessage(agentMessage);
        }
    }

    private String normalizeAgentRunName(String agentName) {
        if (agentName == null || agentName.isBlank()) {
            return "";
        }
        return agentName.replace("_agent", "");
    }

    private void persistDecisionActions(DecisionRun decisionRun) {
        if (decisionRun.getDecisionActions() == null) {
            return;
        }
        for (DecisionAction decisionAction : decisionRun.getDecisionActions()) {
            if (decisionAction.getTraceId() == null || decisionAction.getTraceId().isBlank()) {
                decisionAction.setTraceId(decisionRun.getTraceId());
            }
            if (decisionAction.getDecisionRunId() == null) {
                decisionAction.setDecisionRunId(decisionRun.getId());
            }
            if (decisionAction.getAction() == null || decisionAction.getAction().isBlank()) {
                decisionAction.setAction(decisionRun.getAction());
            }
            TradeExecutionStatusNormalizer.StatusPair statusPair = TradeExecutionStatusNormalizer.normalize(
                decisionAction.getExecutionStatus(),
                decisionAction.getOrderStatus()
            );
            decisionAction.setExecutionStatus(statusPair.executionStatus());
            decisionAction.setOrderStatus(statusPair.orderStatus());
            decisionAction.setCreatedAt(normalizeCreatedAt(decisionAction.getCreatedAt(), decisionRun.getCreatedAt()));
            decisionAuditMapper.insertDecisionAction(decisionAction);
        }
    }

    private void attachFeatureSnapshots(List<DecisionRun> decisionRuns) {
        if (decisionRuns == null || decisionRuns.isEmpty()) {
            return;
        }
        List<String> traceIds = new ArrayList<>();
        for (DecisionRun decisionRun : decisionRuns) {
            if (decisionRun == null || decisionRun.getTraceId() == null || decisionRun.getTraceId().isBlank()) {
                continue;
            }
            traceIds.add(decisionRun.getTraceId());
        }
        if (traceIds.isEmpty()) {
            return;
        }
        List<FeatureSnapshot> featureSnapshots = decisionAuditMapper.selectLatestFeatureSnapshotsByTraceIds(traceIds);
        if (featureSnapshots == null || featureSnapshots.isEmpty()) {
            return;
        }
        Map<String, FeatureSnapshot> featureSnapshotByTraceId = new LinkedHashMap<>();
        for (FeatureSnapshot featureSnapshot : featureSnapshots) {
            if (featureSnapshot == null || featureSnapshot.getTraceId() == null || featureSnapshot.getTraceId().isBlank()) {
                continue;
            }
            Map<String, Object> snapshot = readJsonMap(featureSnapshot.getSnapshotJson());
            featureSnapshot.setSnapshot(snapshot);
            featureSnapshotByTraceId.put(featureSnapshot.getTraceId(), featureSnapshot);
        }
        for (DecisionRun decisionRun : decisionRuns) {
            if (decisionRun == null || decisionRun.getTraceId() == null || decisionRun.getTraceId().isBlank()) {
                continue;
            }
            FeatureSnapshot featureSnapshot = featureSnapshotByTraceId.get(decisionRun.getTraceId());
            if (featureSnapshot == null) {
                continue;
            }
            decisionRun.setFeatureSnapshot(featureSnapshot);
            if (decisionRun.getEventStrength() == null || decisionRun.getEventStrength().isBlank()) {
                decisionRun.setEventStrength(featureSnapshot.getEventStrength());
            }
            Map<String, Object> marketSourceConfig = readMarketSourceConfig(featureSnapshot.getSnapshot());
            if (!marketSourceConfig.isEmpty()) {
                decisionRun.setMarketSourceConfig(marketSourceConfig);
            }
            Map<String, Object> snapshot = featureSnapshot.getSnapshot();
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
    }

    private void addRecentSupervisorDecisionMessage(List<AgentMessage> merged,
                                                    Map<String, AgentMessage> mergedByTraceId,
                                                    AgentMessage candidate) {
        if (candidate == null) {
            return;
        }
        String traceId = candidate.getTraceId() == null ? "" : candidate.getTraceId().trim();
        if (!traceId.isBlank() && mergedByTraceId.containsKey(traceId)) {
            return;
        }
        merged.add(candidate);
        if (!traceId.isBlank()) {
            mergedByTraceId.put(traceId, candidate);
        }
    }

    private AgentMessage buildFallbackSupervisorDecisionMessage(DecisionRun decisionRun) {
        if (decisionRun == null || decisionRun.getTraceId() == null || decisionRun.getTraceId().isBlank()) {
            return null;
        }
        Map<String, Object> payload = new LinkedHashMap<>();
        if (decisionRun.getAction() != null && !decisionRun.getAction().isBlank()) {
            payload.put("action", decisionRun.getAction());
        }
        if (decisionRun.getConfidence() != null) {
            payload.put("confidence", decisionRun.getConfidence());
        }
        if (decisionRun.getSummaryReason() != null && !decisionRun.getSummaryReason().isBlank()) {
            payload.put("summary_reason", decisionRun.getSummaryReason());
        }
        if (payload.isEmpty()) {
            return null;
        }
        AgentMessage fallback = new AgentMessage();
        fallback.setTraceId(decisionRun.getTraceId());
        fallback.setSpeakerAgent("supervisor_agent");
        fallback.setTargetAgent("");
        fallback.setMessageType("final_decision");
        fallback.setTemplateCode(decisionRun.getResolvedTemplateCode());
        fallback.setModelCode(decisionRun.getModelCode());
        fallback.setContentJson(writeJson(payload));
        fallback.setSummaryText(decisionRun.getSummaryReason());
        fallback.setCreatedAt(normalizeCreatedAt(decisionRun.getCreatedAt(), null));
        return fallback;
    }

    private String sortKeyForRecentSupervisorDecision(AgentMessage agentMessage) {
        if (agentMessage == null) {
            return "";
        }
        String createdAt = normalizeCreatedAt(agentMessage.getCreatedAt(), null);
        if (createdAt != null && !createdAt.isBlank()) {
            return createdAt;
        }
        return "";
    }

    private boolean hasDecisionStatusFilters(String executionStatus, String orderStatus) {
        return executionStatus != null && !executionStatus.isBlank()
            || orderStatus != null && !orderStatus.isBlank();
    }

    private void attachLatestExchangeOrders(List<DecisionRun> decisionRuns) {
        if (decisionRuns == null || decisionRuns.isEmpty()) {
            return;
        }
        List<String> traceIds = new ArrayList<>();
        for (DecisionRun decisionRun : decisionRuns) {
            if (decisionRun == null || decisionRun.getTraceId() == null || decisionRun.getTraceId().isBlank()) {
                continue;
            }
            traceIds.add(decisionRun.getTraceId());
        }
        if (traceIds.isEmpty()) {
            return;
        }
        List<ExchangeOrder> exchangeOrders = decisionAuditMapper.selectLatestExchangeOrdersByTraceIds(traceIds);
        Map<String, ExchangeOrder> exchangeOrderByTraceId = new LinkedHashMap<>();
        if (exchangeOrders != null) {
            for (ExchangeOrder exchangeOrder : exchangeOrders) {
                if (exchangeOrder == null || exchangeOrder.getTraceId() == null || exchangeOrder.getTraceId().isBlank()) {
                    continue;
                }
                exchangeOrderByTraceId.put(exchangeOrder.getTraceId(), exchangeOrder);
            }
        }
        for (DecisionRun decisionRun : decisionRuns) {
            if (decisionRun == null) {
                continue;
            }
            ExchangeOrder exchangeOrder = exchangeOrderByTraceId.get(decisionRun.getTraceId());
            String resolvedOrderStatus = resolveDecisionOrderStatus(decisionRun, exchangeOrder);
            decisionRun.setExecutionStatus(resolveDecisionExecutionStatus(decisionRun, exchangeOrder, resolvedOrderStatus));
            decisionRun.setOrderStatus(resolvedOrderStatus);
        }
    }

    private String resolveDecisionExecutionStatus(DecisionRun decisionRun,
                                                  ExchangeOrder exchangeOrder,
                                                  String resolvedOrderStatus) {
        String storedExecutionStatus = TradeExecutionStatusNormalizer.normalizeBusinessStatus(decisionRun.getExecutionStatus());
        if (!storedExecutionStatus.isEmpty()) {
            return storedExecutionStatus;
        }
        String exchangeExecutionStatus = exchangeOrder == null
            ? ""
            : TradeExecutionStatusNormalizer.normalizeBusinessStatus(exchangeOrder.getExecutionStatus());
        if (!exchangeExecutionStatus.isEmpty()) {
            return exchangeExecutionStatus;
        }
        String derivedExecutionStatus = TradeExecutionStatusNormalizer.businessStatusFromOrderStatus(resolvedOrderStatus);
        if (!derivedExecutionStatus.isEmpty()) {
            return derivedExecutionStatus;
        }
        return "pending";
    }

    private String resolveDecisionOrderStatus(DecisionRun decisionRun, ExchangeOrder exchangeOrder) {
        return firstNonBlank(
            decisionRun == null ? null : decisionRun.getOrderStatus(),
            exchangeOrder == null ? null : exchangeOrder.getOrderStatus()
        );
    }

    private String firstNonBlank(String primaryValue, String fallbackValue) {
        if (primaryValue != null && !primaryValue.isBlank()) {
            return primaryValue.trim();
        }
        if (fallbackValue != null && !fallbackValue.isBlank()) {
            return fallbackValue.trim();
        }
        return null;
    }

    private void attachAgentMessages(List<DecisionRun> decisionRuns) {
        if (decisionRuns == null || decisionRuns.isEmpty()) {
            return;
        }
        List<String> traceIds = new ArrayList<>();
        for (DecisionRun decisionRun : decisionRuns) {
            if (decisionRun == null || decisionRun.getTraceId() == null || decisionRun.getTraceId().isBlank()) {
                continue;
            }
            traceIds.add(decisionRun.getTraceId());
        }
        if (traceIds.isEmpty()) {
            return;
        }
        List<AgentMessage> agentMessages = decisionAuditMapper.selectAgentMessagesByTraceIds(traceIds);
        if (agentMessages == null || agentMessages.isEmpty()) {
            return;
        }
        Map<String, List<AgentMessage>> messagesByTraceId = new LinkedHashMap<>();
        for (AgentMessage agentMessage : agentMessages) {
            if (agentMessage == null || agentMessage.getTraceId() == null || agentMessage.getTraceId().isBlank()) {
                continue;
            }
            messagesByTraceId.computeIfAbsent(agentMessage.getTraceId(), ignored -> new ArrayList<>()).add(agentMessage);
        }
        for (DecisionRun decisionRun : decisionRuns) {
            if (decisionRun == null || decisionRun.getTraceId() == null || decisionRun.getTraceId().isBlank()) {
                continue;
            }
            List<AgentMessage> resolvedMessages = messagesByTraceId.get(decisionRun.getTraceId());
            if (resolvedMessages != null) {
                decisionRun.setAgentMessages(resolvedMessages);
            }
        }
    }

    private String normalizeCreatedAt(String createdAt, String fallbackCreatedAt) {
        String normalized = TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(createdAt);
        if (isDatabaseCreatedAt(normalized)) {
            return normalized;
        }
        normalized = TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(fallbackCreatedAt);
        if (isDatabaseCreatedAt(normalized)) {
            return normalized;
        }
        return TradeRuntimeTimeUtils.nowSqlDateTime();
    }

    private boolean isDatabaseCreatedAt(String createdAt) {
        return createdAt != null && !createdAt.isBlank() && !createdAt.matches("^-?\\d+$");
    }

    private String writeJson(Object value) {
        try {
            return OBJECT_MAPPER.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("Failed to serialize feature snapshot", ex);
        }
    }

    private Map<String, Object> readJsonMap(String json) {
        if (json == null || json.isBlank()) {
            return new LinkedHashMap<>();
        }
        try {
            Map<String, Object> parsed = OBJECT_MAPPER.readValue(json, new TypeReference<Map<String, Object>>() {});
            return parsed == null ? new LinkedHashMap<>() : new LinkedHashMap<>(parsed);
        } catch (JsonProcessingException ex) {
            return new LinkedHashMap<>();
        }
    }

    private Map<String, Object> readMarketSourceConfig(Map<String, Object> snapshot) {
        if (snapshot == null || snapshot.isEmpty()) {
            return new LinkedHashMap<>();
        }
        Object rawValue = snapshot.get("marketSourceConfig");
        if (!(rawValue instanceof Map<?, ?>)) {
            rawValue = snapshot.get("market_source_config");
        }
        if (!(rawValue instanceof Map<?, ?> mapValue)) {
            return new LinkedHashMap<>();
        }
        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : mapValue.entrySet()) {
            if (entry.getKey() == null) {
                continue;
            }
            normalized.put(String.valueOf(entry.getKey()), entry.getValue());
        }
        return normalized;
    }
}

