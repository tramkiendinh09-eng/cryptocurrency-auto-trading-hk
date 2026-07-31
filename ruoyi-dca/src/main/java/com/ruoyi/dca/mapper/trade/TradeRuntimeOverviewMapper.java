package com.ruoyi.dca.mapper.trade;

import com.ruoyi.dca.domain.decision.AgentConclusion;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.decision.SignalEvent;
import com.ruoyi.dca.domain.decision.SignalWindowState;
import com.ruoyi.dca.domain.event.EventRaw;
import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.risk.RiskGuardHit;
import com.ruoyi.dca.domain.trade.TradeActionSummary;
import org.apache.ibatis.annotations.Param;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

public interface TradeRuntimeOverviewMapper {

    Long countEventRaws();

    Long countSignalEvents();

    Long countDecisionRuns();

    Long countRiskGuardHits();

    Long countActivePositions();

    BigDecimal sumTotalUnrealizedPnl();

    PnlSnapshot selectLatestPnlSnapshot();

    DecisionRun selectLatestDecisionRun();

    List<EventRaw> selectRecentEventRaws(@Param("limit") int limit);

    List<SignalEvent> selectRecentSignalEvents(@Param("limit") int limit);

    List<SignalWindowState> selectActiveSignalWindows(@Param("limit") int limit, @Param("currentTime") String currentTime);

    List<AgentConclusion> selectRecentAgentConclusions(@Param("limit") int limit);

    List<DecisionRun> selectRecentDecisionRuns(@Param("limit") int limit);

    List<RiskGuardHit> selectRecentRiskGuardHits(@Param("limit") int limit);

    List<ExchangeFill> selectRecentExchangeFills(@Param("limit") int limit);

    List<TradeActionSummary> selectRecentTradeActionSummaries(@Param("limit") int limit);

    List<TradeActionSummary> selectTradeActionSummariesAfter(@Param("createdAt") String createdAt);

    List<ExchangeOrder> selectRecentExchangeOrders(@Param("limit") int limit);

    List<PositionSnapshot> selectRecentPositionSnapshots(@Param("limit") int limit);

    List<Map<String, Object>> selectExecutionStatusCounts();

    Long countCooldownBlockedDecisionRuns();

    Long countBudgetBlockedDecisionRuns();
}
