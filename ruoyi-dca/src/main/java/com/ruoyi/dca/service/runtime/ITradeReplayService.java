package com.ruoyi.dca.service.runtime;

import com.ruoyi.dca.domain.replay.PaperTradeOrder;
import com.ruoyi.dca.domain.replay.ReplayComparison;
import com.ruoyi.dca.domain.replay.ReplayEvent;
import com.ruoyi.dca.domain.replay.ReplaySession;
import com.ruoyi.dca.domain.replay.ReplayTraceSource;
import com.ruoyi.dca.domain.replay.ShadowDecisionLog;
import com.ruoyi.dca.domain.replay.TraceAuditDetail;

import java.util.List;

public interface ITradeReplayService {

    void recordReplaySession(ReplaySession replaySession);

    void recordReplayEvent(ReplayEvent replayEvent);

    void recordPaperTradeOrder(PaperTradeOrder paperTradeOrder);

    void recordShadowDecisionLog(ShadowDecisionLog shadowDecisionLog);

    List<ReplaySession> listReplaySessions();

    List<ReplayEvent> listReplayEvents(Long sessionId);

    List<PaperTradeOrder> listPaperTradeOrders();

    List<ShadowDecisionLog> listShadowDecisionLogs();

    ReplayTraceSource getReplaySource(String traceId);

    TraceAuditDetail getTraceAuditDetail(String traceId);

    ReplayComparison getReplayComparison(Long sessionId);

    void updateReplaySession(ReplaySession replaySession);

    ReplaySession dispatchReplay(String traceId);
}
