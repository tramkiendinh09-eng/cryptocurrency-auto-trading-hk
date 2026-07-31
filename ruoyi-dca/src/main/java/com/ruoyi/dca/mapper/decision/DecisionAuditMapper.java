package com.ruoyi.dca.mapper.decision;

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
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface DecisionAuditMapper {

    int insertSignalEvent(SignalEvent signalEvent);

    int insertFeatureSnapshot(FeatureSnapshot featureSnapshot);

    int insertSignalScore(SignalScore signalScore);

    int insertSignalWindowState(SignalWindowState signalWindowState);

    int deactivateExpiredSignalWindowStates(@Param("symbol") String symbol,
                                            @Param("currentTime") String currentTime);

    int insertAgentRun(AgentRun agentRun);

    int insertAgentObservation(AgentObservation agentObservation);

    int insertAgentConclusion(AgentConclusion agentConclusion);

    int insertAgentMessage(AgentMessage agentMessage);

    int insertDecisionRun(DecisionRun decisionRun);

    int insertDecisionAction(DecisionAction decisionAction);

    List<DecisionRun> selectDecisionRunsBase();

    List<DecisionRun> selectDecisionRuns(@Param("executionStatus") String executionStatus,
                                         @Param("orderStatus") String orderStatus);

    List<ExchangeOrder> selectLatestExchangeOrdersByTraceIds(@Param("traceIds") List<String> traceIds);

    List<FeatureSnapshot> selectLatestFeatureSnapshotsByTraceIds(@Param("traceIds") List<String> traceIds);

    List<AgentMessage> selectAgentMessagesByTraceIds(@Param("traceIds") List<String> traceIds);

    List<AgentMessage> selectRecentSupervisorDecisionMessages(@Param("symbol") String symbol,
                                                              @Param("mode") String mode,
                                                              @Param("excludeTraceId") String excludeTraceId,
                                                              @Param("limit") Integer limit);

    List<DecisionRun> selectRecentSupervisorDecisionRuns(@Param("symbol") String symbol,
                                                         @Param("mode") String mode,
                                                         @Param("excludeTraceId") String excludeTraceId,
                                                         @Param("limit") Integer limit);
}

