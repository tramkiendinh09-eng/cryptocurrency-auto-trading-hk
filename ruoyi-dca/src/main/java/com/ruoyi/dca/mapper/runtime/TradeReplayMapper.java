package com.ruoyi.dca.mapper.runtime;

import com.ruoyi.dca.domain.NotifyRecord;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.decision.SignalEvent;
import com.ruoyi.dca.domain.event.EventRaw;
import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.replay.PaperTradeOrder;
import com.ruoyi.dca.domain.replay.ReplayEvent;
import com.ruoyi.dca.domain.replay.ReplaySession;
import com.ruoyi.dca.domain.replay.ShadowDecisionLog;
import com.ruoyi.dca.domain.risk.RiskGuardHit;
import com.ruoyi.dca.domain.trade.TradeActionSummary;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface TradeReplayMapper {

    int insertReplaySession(ReplaySession replaySession);

    int updateReplaySession(ReplaySession replaySession);

    int insertReplayEvent(ReplayEvent replayEvent);

    int insertPaperTradeOrder(PaperTradeOrder paperTradeOrder);

    int insertShadowDecisionLog(ShadowDecisionLog shadowDecisionLog);

    List<ReplaySession> selectReplaySessions();

    List<ReplayEvent> selectReplayEvents(@Param("sessionId") Long sessionId);

    List<PaperTradeOrder> selectPaperTradeOrders();

    List<ShadowDecisionLog> selectShadowDecisionLogs();

    ReplaySession selectReplaySessionById(@Param("id") Long id);

    List<EventRaw> selectEventRawsByTraceId(@Param("traceId") String traceId);

    List<SignalEvent> selectSignalEventsByTraceId(@Param("traceId") String traceId);

    DecisionRun selectDecisionRunByTraceId(@Param("traceId") String traceId);

    ExchangeOrder selectLatestExchangeOrderByTraceId(@Param("traceId") String traceId);

    List<ExchangeFill> selectExchangeFillsByTraceId(@Param("traceId") String traceId);

    List<RiskGuardHit> selectRiskGuardHitsByTraceId(@Param("traceId") String traceId);

    PositionSnapshot selectLatestPositionSnapshotByTraceId(@Param("traceId") String traceId);

    PnlSnapshot selectLatestPnlSnapshotByTraceId(@Param("traceId") String traceId);

    TradeActionSummary selectTradeActionSummaryByTraceId(@Param("traceId") String traceId);

    List<NotifyRecord> selectNotifyRecordsByTraceId(@Param("traceId") String traceId);

    ShadowDecisionLog selectLatestShadowDecisionLogByTraceId(@Param("traceId") String traceId);
}
