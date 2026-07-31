package com.ruoyi.dca.service.decision;

import com.ruoyi.dca.domain.decision.AgentMessage;
import com.ruoyi.dca.domain.decision.DecisionRun;

import java.util.List;

public interface IDecisionAuditService {

    void saveDecisionRun(DecisionRun decisionRun);

    List<DecisionRun> listDecisionRuns(String executionStatus, String orderStatus);

    List<AgentMessage> listRecentSupervisorDecisions(String symbol, String mode, String excludeTraceId, Integer limit);
}

