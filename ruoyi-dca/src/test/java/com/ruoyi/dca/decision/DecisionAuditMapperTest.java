package com.ruoyi.dca.decision;

import com.ruoyi.dca.domain.decision.DecisionAction;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.decision.FeatureSnapshot;
import com.ruoyi.dca.domain.decision.AgentMessage;
import com.ruoyi.dca.domain.decision.AgentObservation;
import com.ruoyi.dca.domain.decision.AgentRun;
import com.ruoyi.dca.domain.decision.SignalEvent;
import com.ruoyi.dca.domain.decision.SignalScore;
import com.ruoyi.dca.domain.decision.SignalWindowState;
import com.ruoyi.dca.mapper.decision.DecisionAuditMapper;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.annotation.MapperScan;
import org.mybatis.spring.boot.test.autoconfigure.MybatisTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.core.io.ClassPathResource;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.util.StreamUtils;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@MybatisTest
@ContextConfiguration(classes = DecisionAuditMapperTest.TestApplication.class)
@TestPropertySource(properties = "mybatis.mapper-locations=classpath*:mapper/dca/decision/*.xml")
@Sql(statements = {
    "drop table if exists agent_observation",
    "drop table if exists agent_message",
    "drop table if exists agent_run",
    "drop table if exists signal_window_state",
    "drop table if exists signal_score",
    "drop table if exists feature_snapshot",
    "drop table if exists signal_event",
    "drop table if exists decision_action",
    "drop table if exists exchange_order",
    "drop table if exists decision_run",
    "create table signal_event (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "symbol varchar(32)," +
        "signal_type varchar(32)," +
        "feature_json varchar(2048)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table feature_snapshot (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "symbol varchar(32)," +
        "event_strength varchar(16)," +
        "snapshot_json varchar(4096)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table signal_score (" +
        "id bigint auto_increment primary key," +
        "signal_event_id bigint," +
        "trace_id varchar(64)," +
        "signal_type varchar(32)," +
        "score decimal(10,4)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table signal_window_state (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "symbol varchar(32)," +
        "window_key varchar(128)," +
        "source_type varchar(32)," +
        "signal_type varchar(32)," +
        "direction varchar(16)," +
        "strength_score decimal(10,4)," +
        "decay_score decimal(10,4)," +
        "opened_at varchar(32)," +
        "expires_at varchar(32)," +
        "last_event_at varchar(32)," +
        "last_confirmed_at varchar(32)," +
        "dedupe_key varchar(128)," +
        "combine_until_at varchar(32)," +
        "is_active boolean," +
        "state_json varchar(4096)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table agent_run (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "symbol varchar(32)," +
        "agent_name varchar(32)," +
        "event_strength varchar(16)," +
        "status varchar(32)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table agent_observation (" +
        "id bigint auto_increment primary key," +
        "agent_run_id bigint," +
        "trace_id varchar(64)," +
        "agent_name varchar(32)," +
        "observation_type varchar(64)," +
        "observation_json varchar(4096)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table agent_message (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "agent_run_id bigint," +
        "round_no integer," +
        "speaker_agent varchar(64)," +
        "target_agent varchar(64)," +
        "message_type varchar(32)," +
        "template_code varchar(128)," +
        "model_code varchar(64)," +
        "content_json varchar(4096)," +
        "summary_text varchar(512)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table decision_run (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "symbol varchar(32)," +
        "mode varchar(16)," +
        "action varchar(32)," +
        "confidence integer," +
        "summary_reason varchar(255)," +
        "model_code varchar(64)," +
        "model_provider varchar(64)," +
        "prompt_source varchar(32)," +
        "binding_template_code varchar(128)," +
        "fallback_template_code varchar(128)," +
        "resolved_template_code varchar(128)," +
        "prompt_template_fallback_used boolean," +
        "trigger_reason varchar(255)," +
        "trigger_source varchar(64)," +
        "dispatch_mode varchar(32)," +
        "selected_agents_json varchar(2048)," +
        "combination_match_json varchar(2048)," +
        "active_signal_refs_json varchar(2048)," +
        "cooldown_blocked boolean," +
        "budget_blocked boolean," +
        "execution_status varchar(32)," +
        "order_status varchar(32)," +
        "trade_memory_status_json varchar(2048)," +
        "lifecycle_status_json varchar(2048)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table decision_action (" +
        "id bigint auto_increment primary key," +
        "decision_run_id bigint," +
        "trace_id varchar(64)," +
        "action varchar(32)," +
        "side varchar(16)," +
        "order_ref varchar(64)," +
        "execution_status varchar(32)," +
        "order_status varchar(32)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table exchange_order (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "exchange_code varchar(32)," +
        "symbol varchar(32)," +
        "side varchar(16)," +
        "mode varchar(16)," +
        "order_ref varchar(64)," +
        "status varchar(32)," +
        "order_status varchar(32)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create index idx_exchange_order_trace_id_id on exchange_order (trace_id, id)",
    "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status) values " +
        "('t-join', 'BTCUSDT', 'paper', 'OPEN_LONG', 82, 'trend confirmed', 'gpt-4.1', 'openai', 'template', 'trade.supervisor.v1', 'trade.supervisor.fallback', 'trade.supervisor.v1', false, null, null)",
    "insert into exchange_order (trace_id, exchange_code, symbol, side, mode, order_ref, status, order_status) values " +
        "('t-join', 'binance', 'BTCUSDT', 'BUY', 'paper', 'ord-1', 'pending', 'PENDING')",
    "insert into exchange_order (trace_id, exchange_code, symbol, side, mode, order_ref, status, order_status) values " +
        "('t-join', 'binance', 'BTCUSDT', 'BUY', 'paper', 'ord-2', 'filled', 'FILLED')",
    "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status) values " +
        "('t-order-only', 'SOLUSDT', 'live', 'OPEN_SHORT', 77, 'risk accepted', 'gpt-4.1-mini', 'openai', 'inline', 'trade.supervisor.v1', 'trade.supervisor.fallback', '', true, null, null)",
    "insert into exchange_order (trace_id, exchange_code, symbol, side, mode, order_ref, status, order_status) values " +
        "('t-order-only', 'okx', 'SOLUSDT', 'SELL', 'live', 'ord-3', null, 'BLOCKED')",
    "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status) values " +
        "('t-fallback', 'ETHUSDT', 'shadow', 'SKIP', 0, 'no execution order row', 'heuristic-v1', 'internal', 'inline', '', '', '', true, 'skipped', 'SKIPPED')"
})
class DecisionAuditMapperTest {

    @SpringBootApplication
    @MapperScan("com.ruoyi.dca.mapper.decision")
    static class TestApplication {
    }

    @Autowired
    private DecisionAuditMapper decisionAuditMapper;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void selectDecisionRunsIncludesLatestExecutionState() {
        List<DecisionRun> runs = decisionAuditMapper.selectDecisionRuns(null, null);

        assertThat(runs).hasSize(3);
        DecisionRun joined = runs.stream()
            .filter(run -> "t-join".equals(run.getTraceId()))
            .findFirst()
            .orElseThrow();
        assertThat(joined.getExecutionStatus()).isEqualTo("filled");
        assertThat(joined.getOrderStatus()).isEqualTo("FILLED");
        assertThat(joined.getModelCode()).isEqualTo("gpt-4.1");
        assertThat(joined.getModelProvider()).isEqualTo("openai");
        assertThat(joined.getPromptSource()).isEqualTo("template");
        assertThat(joined.getBindingTemplateCode()).isEqualTo("trade.supervisor.v1");
        assertThat(joined.getFallbackTemplateCode()).isEqualTo("trade.supervisor.fallback");
        assertThat(joined.getResolvedTemplateCode()).isEqualTo("trade.supervisor.v1");
        assertThat(joined.getPromptTemplateFallbackUsed()).isFalse();

        DecisionRun orderOnly = runs.stream()
            .filter(run -> "t-order-only".equals(run.getTraceId()))
            .findFirst()
            .orElseThrow();
        assertThat(orderOnly.getExecutionStatus()).isEqualTo("blocked");
        assertThat(orderOnly.getOrderStatus()).isEqualTo("BLOCKED");
    }

    @Test
    void selectDecisionRunsFiltersByExecutionStatus() {
        List<DecisionRun> runs = decisionAuditMapper.selectDecisionRuns("filled", null);

        assertThat(runs).hasSize(1);
        assertThat(runs.get(0).getTraceId()).isEqualTo("t-join");
    }

    @Test
    void selectDecisionRunsSqlAvoidsCorrelatedLatestOrderSubquery() throws IOException {
        String xml = StreamUtils.copyToString(
            new ClassPathResource("mapper/dca/decision/DecisionAuditMapper.xml").getInputStream(),
            StandardCharsets.UTF_8
        );

        assertThat(xml).doesNotContain("where inner_eo.trace_id = dr.trace_id");
        assertThat(xml).contains("select trace_id, max(id) as latest_id");
    }

    @Test
    void insertDecisionRunPersistsExecutionStatusPair() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("t-insert");
        decisionRun.setSymbol("SOLUSDT");
        decisionRun.setMode("paper");
        decisionRun.setAction("OPEN_LONG");
        decisionRun.setConfidence(74);
        decisionRun.setSummaryReason("breakout");
        decisionRun.setModelCode("gpt-4.1");
        decisionRun.setModelProvider("openai");
        decisionRun.setPromptSource("template");
        decisionRun.setBindingTemplateCode("trade.supervisor.v2");
        decisionRun.setFallbackTemplateCode("trade.supervisor.fallback");
        decisionRun.setResolvedTemplateCode("trade.supervisor.v2");
        decisionRun.setPromptTemplateFallbackUsed(Boolean.FALSE);
        decisionRun.setTriggerReason("strong_news_then_break");
        decisionRun.setTriggerSource("news");
        decisionRun.setDispatchMode("LLM_ALLOWED");
        decisionRun.setSelectedAgentsJson("[\"news_agent\",\"market_agent\",\"supervisor_agent\"]");
        decisionRun.setCombinationMatchJson("{\"code\":\"strong_news_then_break\"}");
        decisionRun.setActiveSignalRefsJson("[\"news:BTCUSDT:headline-1\"]");
        decisionRun.setCooldownBlocked(Boolean.FALSE);
        decisionRun.setBudgetBlocked(Boolean.FALSE);
        decisionRun.setExecutionStatus("filled");
        decisionRun.setOrderStatus("FILLED");

        decisionAuditMapper.insertDecisionRun(decisionRun);

        List<String> stored = jdbcTemplate.query(
            "select model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, trigger_reason, trigger_source, dispatch_mode, selected_agents_json, combination_match_json, active_signal_refs_json, cooldown_blocked, budget_blocked, execution_status, order_status from decision_run where trace_id = ?",
            (rs, rowNum) -> rs.getString("model_code") + "|" + rs.getString("model_provider") + "|" + rs.getString("prompt_source")
                + "|" + rs.getString("binding_template_code") + "|" + rs.getString("fallback_template_code")
                + "|" + rs.getString("resolved_template_code") + "|" + rs.getBoolean("prompt_template_fallback_used")
                + "|" + rs.getString("trigger_reason") + "|" + rs.getString("trigger_source") + "|" + rs.getString("dispatch_mode")
                + "|" + rs.getString("selected_agents_json") + "|" + rs.getString("combination_match_json")
                + "|" + rs.getString("active_signal_refs_json") + "|" + rs.getBoolean("cooldown_blocked")
                + "|" + rs.getBoolean("budget_blocked")
                + "|" + rs.getString("execution_status") + "|" + rs.getString("order_status"),
            "t-insert"
        );

        assertThat(stored).containsExactly(
            "gpt-4.1|openai|template|trade.supervisor.v2|trade.supervisor.fallback|trade.supervisor.v2|false|strong_news_then_break|news|LLM_ALLOWED|[\"news_agent\",\"market_agent\",\"supervisor_agent\"]|{\"code\":\"strong_news_then_break\"}|[\"news:BTCUSDT:headline-1\"]|false|false|filled|FILLED"
        );
    }

    @Test
    void insertDecisionActionPersistsTraceAndStatusPair() {
        DecisionAction decisionAction = new DecisionAction();
        decisionAction.setDecisionRunId(1L);
        decisionAction.setTraceId("t-action-1");
        decisionAction.setAction("OPEN_LONG");
        decisionAction.setSide("long");
        decisionAction.setOrderRef("paper-BTCUSDT");
        decisionAction.setExecutionStatus("filled");
        decisionAction.setOrderStatus("FILLED");

        decisionAuditMapper.insertDecisionAction(decisionAction);

        List<String> stored = jdbcTemplate.query(
            "select trace_id, action, side, order_ref, execution_status, order_status from decision_action where trace_id = ?",
            (rs, rowNum) -> rs.getString("trace_id") + "|" + rs.getString("action") + "|" + rs.getString("side")
                + "|" + rs.getString("order_ref") + "|" + rs.getString("execution_status") + "|" + rs.getString("order_status"),
            "t-action-1"
        );

        assertThat(stored).containsExactly("t-action-1|OPEN_LONG|long|paper-BTCUSDT|filled|FILLED");
    }

    @Test
    void insertFeatureSnapshotPersistsSnapshotJsonAndEventStrength() {
        FeatureSnapshot featureSnapshot = new FeatureSnapshot();
        featureSnapshot.setTraceId("t-feature-1");
        featureSnapshot.setSymbol("BTCUSDT");
        featureSnapshot.setEventStrength("strong");
        featureSnapshot.setSnapshotJson("{\"price_change_pct\":6.4}");

        decisionAuditMapper.insertFeatureSnapshot(featureSnapshot);

        List<String> stored = jdbcTemplate.query(
            "select trace_id, symbol, event_strength, snapshot_json from feature_snapshot where trace_id = ?",
            (rs, rowNum) -> rs.getString("trace_id") + "|" + rs.getString("symbol")
                + "|" + rs.getString("event_strength") + "|" + rs.getString("snapshot_json"),
            "t-feature-1"
        );

        assertThat(stored).containsExactly("t-feature-1|BTCUSDT|strong|{\"price_change_pct\":6.4}");
    }

    @Test
    void insertSignalScorePersistsSignalEventReferenceAndScore() {
        SignalEvent signalEvent = new SignalEvent();
        signalEvent.setTraceId("t-score-1");
        signalEvent.setSymbol("ETHUSDT");
        signalEvent.setSignalType("news");
        signalEvent.setFeatureJson("{\"event_type\":\"news\"}");
        decisionAuditMapper.insertSignalEvent(signalEvent);

        SignalScore signalScore = new SignalScore();
        signalScore.setSignalEventId(signalEvent.getId());
        signalScore.setTraceId("t-score-1");
        signalScore.setSignalType("news");
        signalScore.setScore(java.math.BigDecimal.valueOf(0.82));

        decisionAuditMapper.insertSignalScore(signalScore);

        List<String> stored = jdbcTemplate.query(
            "select trace_id, signal_type, score from signal_score where trace_id = ?",
            (rs, rowNum) -> rs.getString("trace_id") + "|" + rs.getString("signal_type") + "|" + rs.getBigDecimal("score"),
            "t-score-1"
        );

        assertThat(stored).containsExactly("t-score-1|news|0.8200");
    }

    @Test
    void insertSignalWindowStatePersistsWindowPayload() {
        SignalWindowState signalWindowState = new SignalWindowState();
        signalWindowState.setTraceId("t-window-1");
        signalWindowState.setSymbol("SOLUSDT");
        signalWindowState.setWindowKey("social:SOLUSDT:15m");
        signalWindowState.setSourceType("social");
        signalWindowState.setSignalType("panic");
        signalWindowState.setDirection("bearish");
        signalWindowState.setStrengthScore(new java.math.BigDecimal("0.8200"));
        signalWindowState.setDecayScore(new java.math.BigDecimal("0.7100"));
        signalWindowState.setOpenedAt("2026-04-17T10:00:00Z");
        signalWindowState.setExpiresAt("2026-04-17T10:15:00Z");
        signalWindowState.setLastEventAt("2026-04-17T10:02:00Z");
        signalWindowState.setLastConfirmedAt("2026-04-17T10:03:00Z");
        signalWindowState.setDedupeKey("social:panic:sol");
        signalWindowState.setCombineUntilAt("2026-04-17T10:15:00Z");
        signalWindowState.setActive(Boolean.TRUE);
        signalWindowState.setStateJson("{\"count\":3}");

        decisionAuditMapper.insertSignalWindowState(signalWindowState);

        List<String> stored = jdbcTemplate.query(
            "select trace_id, symbol, window_key, source_type, signal_type, direction, strength_score, decay_score, opened_at, expires_at, last_event_at, last_confirmed_at, dedupe_key, combine_until_at, is_active, state_json from signal_window_state where trace_id = ?",
            (rs, rowNum) -> rs.getString("trace_id") + "|" + rs.getString("symbol")
                + "|" + rs.getString("window_key") + "|" + rs.getString("source_type") + "|" + rs.getString("signal_type")
                + "|" + rs.getString("direction") + "|" + rs.getBigDecimal("strength_score")
                + "|" + rs.getBigDecimal("decay_score") + "|" + rs.getString("opened_at")
                + "|" + rs.getString("expires_at") + "|" + rs.getString("last_event_at")
                + "|" + rs.getString("last_confirmed_at") + "|" + rs.getString("dedupe_key")
                + "|" + rs.getString("combine_until_at") + "|" + rs.getBoolean("is_active")
                + "|" + rs.getString("state_json"),
            "t-window-1"
        );

        assertThat(stored).containsExactly(
            "t-window-1|SOLUSDT|social:SOLUSDT:15m|social|panic|bearish|0.8200|0.7100|2026-04-17T10:00:00Z|2026-04-17T10:15:00Z|2026-04-17T10:02:00Z|2026-04-17T10:03:00Z|social:panic:sol|2026-04-17T10:15:00Z|true|{\"count\":3}"
        );
    }

    @Test
    void deactivateExpiredSignalWindowStatesOnlyFlipsExpiredActiveRowsForSymbol() {
        jdbcTemplate.update(
            "insert into signal_window_state (trace_id, symbol, window_key, expires_at, is_active, state_json) values (?, ?, ?, ?, ?, ?)",
            "t-window-expired",
            "BTCUSDT",
            "market:BTCUSDT:15m",
            "2026-04-17 10:00:00",
            true,
            "{\"count\":1}"
        );
        jdbcTemplate.update(
            "insert into signal_window_state (trace_id, symbol, window_key, expires_at, is_active, state_json) values (?, ?, ?, ?, ?, ?)",
            "t-window-future",
            "BTCUSDT",
            "news:BTCUSDT:15m",
            "2026-04-17 12:00:00",
            true,
            "{\"count\":2}"
        );
        jdbcTemplate.update(
            "insert into signal_window_state (trace_id, symbol, window_key, expires_at, is_active, state_json) values (?, ?, ?, ?, ?, ?)",
            "t-window-other-symbol",
            "ETHUSDT",
            "market:ETHUSDT:15m",
            "2026-04-17 10:00:00",
            true,
            "{\"count\":3}"
        );
        jdbcTemplate.update(
            "insert into signal_window_state (trace_id, symbol, window_key, expires_at, is_active, state_json) values (?, ?, ?, ?, ?, ?)",
            "t-window-inactive",
            "BTCUSDT",
            "social:BTCUSDT:15m",
            "2026-04-17 09:00:00",
            false,
            "{\"count\":4}"
        );

        int updated = decisionAuditMapper.deactivateExpiredSignalWindowStates("BTCUSDT", "2026-04-17 11:00:00");

        assertThat(updated).isEqualTo(1);
        List<String> stored = jdbcTemplate.query(
            "select trace_id, is_active from signal_window_state where trace_id in (?, ?, ?, ?) order by trace_id asc",
            (rs, rowNum) -> rs.getString("trace_id") + "|" + rs.getBoolean("is_active"),
            "t-window-expired",
            "t-window-future",
            "t-window-inactive",
            "t-window-other-symbol"
        );

        assertThat(stored).containsExactly(
            "t-window-expired|false",
            "t-window-future|true",
            "t-window-inactive|false",
            "t-window-other-symbol|true"
        );
    }

    @Test
    void insertAgentRunPersistsAgentExecutionAuditRow() {
        AgentRun agentRun = new AgentRun();
        agentRun.setTraceId("t-agent-run-1");
        agentRun.setSymbol("BTCUSDT");
        agentRun.setAgentName("market");
        agentRun.setEventStrength("strong");
        agentRun.setStatus("completed");

        decisionAuditMapper.insertAgentRun(agentRun);

        List<String> stored = jdbcTemplate.query(
            "select trace_id, symbol, agent_name, event_strength, status from agent_run where trace_id = ?",
            (rs, rowNum) -> rs.getString("trace_id") + "|" + rs.getString("symbol")
                + "|" + rs.getString("agent_name") + "|" + rs.getString("event_strength") + "|" + rs.getString("status"),
            "t-agent-run-1"
        );

        assertThat(stored).containsExactly("t-agent-run-1|BTCUSDT|market|strong|completed");
    }

    @Test
    void insertAgentObservationPersistsObservationWithRunReference() {
        AgentRun agentRun = new AgentRun();
        agentRun.setTraceId("t-agent-obs-1");
        agentRun.setSymbol("ETHUSDT");
        agentRun.setAgentName("news");
        agentRun.setStatus("completed");
        decisionAuditMapper.insertAgentRun(agentRun);

        AgentObservation observation = new AgentObservation();
        observation.setAgentRunId(agentRun.getId());
        observation.setTraceId("t-agent-obs-1");
        observation.setAgentName("news");
        observation.setObservationType("event_context");
        observation.setObservationJson("{\"headline\":\"ETF inflow\"}");

        decisionAuditMapper.insertAgentObservation(observation);

        List<String> stored = jdbcTemplate.query(
            "select agent_run_id, trace_id, agent_name, observation_type, observation_json from agent_observation where trace_id = ?",
            (rs, rowNum) -> rs.getLong("agent_run_id") + "|" + rs.getString("trace_id") + "|" + rs.getString("agent_name")
                + "|" + rs.getString("observation_type") + "|" + rs.getString("observation_json"),
            "t-agent-obs-1"
        );

        assertThat(stored).containsExactly(agentRun.getId() + "|t-agent-obs-1|news|event_context|{\"headline\":\"ETF inflow\"}");
    }

    @Test
    void insertAgentMessagePersistsStructuredDeliberationRow() {
        AgentRun agentRun = new AgentRun();
        agentRun.setTraceId("t-agent-msg-1");
        agentRun.setSymbol("BTCUSDT");
        agentRun.setAgentName("market");
        agentRun.setStatus("completed");
        decisionAuditMapper.insertAgentRun(agentRun);

        AgentMessage agentMessage = new AgentMessage();
        agentMessage.setTraceId("t-agent-msg-1");
        agentMessage.setAgentRunId(agentRun.getId());
        agentMessage.setRoundNo(1);
        agentMessage.setSpeakerAgent("market_agent");
        agentMessage.setTargetAgent("news_agent");
        agentMessage.setMessageType("revision");
        agentMessage.setTemplateCode("trade.market.v1");
        agentMessage.setModelCode("gpt-4.1");
        agentMessage.setContentJson("{\"stance\":\"maintain\"}");
        agentMessage.setSummaryText("market maintains bearish stance");

        decisionAuditMapper.insertAgentMessage(agentMessage);

        List<String> stored = jdbcTemplate.query(
            "select trace_id, agent_run_id, round_no, speaker_agent, target_agent, message_type, template_code, model_code, content_json, summary_text from agent_message where trace_id = ?",
            (rs, rowNum) -> rs.getString("trace_id") + "|" + rs.getLong("agent_run_id") + "|" + rs.getInt("round_no")
                + "|" + rs.getString("speaker_agent") + "|" + rs.getString("target_agent") + "|" + rs.getString("message_type")
                + "|" + rs.getString("template_code") + "|" + rs.getString("model_code") + "|" + rs.getString("content_json")
                + "|" + rs.getString("summary_text"),
            "t-agent-msg-1"
        );

        assertThat(stored).containsExactly(
            "t-agent-msg-1|" + agentRun.getId()
                + "|1|market_agent|news_agent|revision|trade.market.v1|gpt-4.1|{\"stance\":\"maintain\"}|market maintains bearish stance"
        );
    }

    @Test
    void selectDecisionRunsFallsBackToStoredDecisionExecutionState() {
        List<DecisionRun> runs = decisionAuditMapper.selectDecisionRuns("skipped", "SKIPPED");

        assertThat(runs).hasSize(1);
        assertThat(runs.get(0).getTraceId()).isEqualTo("t-fallback");
        assertThat(runs.get(0).getExecutionStatus()).isEqualTo("skipped");
        assertThat(runs.get(0).getOrderStatus()).isEqualTo("SKIPPED");
    }

    @Test
    void selectDecisionRunsDerivesExecutionStatusFromOrderStatusWhenBusinessStatusIsMissing() {
        List<DecisionRun> runs = decisionAuditMapper.selectDecisionRuns("blocked", "BLOCKED");

        assertThat(runs).hasSize(1);
        assertThat(runs.get(0).getTraceId()).isEqualTo("t-order-only");
        assertThat(runs.get(0).getExecutionStatus()).isEqualTo("blocked");
        assertThat(runs.get(0).getOrderStatus()).isEqualTo("BLOCKED");
    }

    @Test
    void selectLatestFeatureSnapshotsByTraceIdsReturnsNewestRowPerTrace() {
        jdbcTemplate.update(
            "insert into feature_snapshot (trace_id, symbol, event_strength, snapshot_json) values (?, ?, ?, ?)",
            "t-join",
            "BTCUSDT",
            "normal",
            "{\"version\":1}"
        );
        jdbcTemplate.update(
            "insert into feature_snapshot (trace_id, symbol, event_strength, snapshot_json) values (?, ?, ?, ?)",
            "t-join",
            "BTCUSDT",
            "strong",
            "{\"version\":2,\"marketSourceConfig\":{\"vendorCode\":\"BINANCE\"}}"
        );
        jdbcTemplate.update(
            "insert into feature_snapshot (trace_id, symbol, event_strength, snapshot_json) values (?, ?, ?, ?)",
            "t-order-only",
            "SOLUSDT",
            "normal",
            "{\"version\":3}"
        );

        List<FeatureSnapshot> snapshots = decisionAuditMapper.selectLatestFeatureSnapshotsByTraceIds(List.of("t-join", "t-order-only"));

        assertThat(snapshots).hasSize(2);
        FeatureSnapshot joinSnapshot = snapshots.stream()
            .filter(snapshot -> "t-join".equals(snapshot.getTraceId()))
            .findFirst()
            .orElseThrow();
        assertThat(joinSnapshot.getEventStrength()).isEqualTo("strong");
        assertThat(joinSnapshot.getSnapshotJson()).contains("\"version\":2");

        FeatureSnapshot orderOnlySnapshot = snapshots.stream()
            .filter(snapshot -> "t-order-only".equals(snapshot.getTraceId()))
            .findFirst()
            .orElseThrow();
        assertThat(orderOnlySnapshot.getSnapshotJson()).contains("\"version\":3");
    }

    @Test
    void selectAgentMessagesByTraceIdsReturnsOrderedTranscriptRows() {
        jdbcTemplate.update(
            "insert into agent_message (trace_id, agent_run_id, round_no, speaker_agent, target_agent, message_type, template_code, model_code, content_json, summary_text) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "t-join",
            11L,
            0,
            "market_agent",
            "news_agent",
            "proposal",
            "trade.market.v1",
            "gpt-4.1",
            "{\"stance\":\"bearish\"}",
            "market opens bearish"
        );
        jdbcTemplate.update(
            "insert into agent_message (trace_id, agent_run_id, round_no, speaker_agent, target_agent, message_type, template_code, model_code, content_json, summary_text) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "t-join",
            12L,
            1,
            "news_agent",
            "market_agent",
            "revision",
            "trade.news.v1",
            "gpt-4.1-mini",
            "{\"stance\":\"neutral\"}",
            "news softens conviction"
        );

        List<AgentMessage> messages = decisionAuditMapper.selectAgentMessagesByTraceIds(List.of("t-join"));

        assertThat(messages).hasSize(2);
        assertThat(messages)
            .extracting(AgentMessage::getRoundNo, AgentMessage::getSpeakerAgent, AgentMessage::getMessageType)
            .containsExactly(
                org.assertj.core.groups.Tuple.tuple(0, "market_agent", "proposal"),
                org.assertj.core.groups.Tuple.tuple(1, "news_agent", "revision")
            );
    }

    @Test
    void selectRecentSupervisorDecisionMessagesBySymbolAndModeReturnsNewestRowsExcludingTrace() {
        jdbcTemplate.update(
            "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "trace-history-1",
            "BTCUSDT",
            "paper",
            "SKIP",
            40,
            "wait_for_breakout",
            "gpt-4.1",
            "openai",
            "template",
            "trade.supervisor.v1",
            "trade.supervisor.fallback",
            "trade.supervisor.v1",
            false,
            "skipped",
            "SKIPPED"
        );
        jdbcTemplate.update(
            "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "trace-history-2",
            "BTCUSDT",
            "paper",
            "HOLD",
            58,
            "hold_range_short",
            "gpt-4.1",
            "openai",
            "template",
            "trade.supervisor.v1",
            "trade.supervisor.fallback",
            "trade.supervisor.v1",
            false,
            "pending",
            "PENDING"
        );
        jdbcTemplate.update(
            "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "trace-other-symbol",
            "ETHUSDT",
            "paper",
            "HOLD",
            70,
            "other_symbol",
            "gpt-4.1",
            "openai",
            "template",
            "trade.supervisor.v1",
            "trade.supervisor.fallback",
            "trade.supervisor.v1",
            false,
            "pending",
            "PENDING"
        );
        jdbcTemplate.update(
            "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "trace-history-live",
            "BTCUSDT",
            "live",
            "HOLD",
            73,
            "other_mode",
            "gpt-4.1",
            "openai",
            "template",
            "trade.supervisor.v1",
            "trade.supervisor.fallback",
            "trade.supervisor.v1",
            false,
            "pending",
            "PENDING"
        );
        jdbcTemplate.update(
            "insert into agent_message (trace_id, agent_run_id, round_no, speaker_agent, target_agent, message_type, template_code, model_code, content_json, summary_text, created_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TIMESTAMP '2026-05-18 09:00:00')",
            "trace-history-1",
            21L,
            2,
            "supervisor_agent",
            "",
            "final_decision",
            "trade.supervisor.v1",
            "gpt-4.1",
            "{\"action\":\"SKIP\"}",
            "wait_for_breakout"
        );
        jdbcTemplate.update(
            "insert into agent_message (trace_id, agent_run_id, round_no, speaker_agent, target_agent, message_type, template_code, model_code, content_json, summary_text, created_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TIMESTAMP '2026-05-18 10:00:00')",
            "trace-history-2",
            22L,
            3,
            "supervisor_agent",
            "",
            "final_decision",
            "trade.supervisor.v1",
            "gpt-4.1",
            "{\"action\":\"HOLD\"}",
            "hold_range_short"
        );
        jdbcTemplate.update(
            "insert into agent_message (trace_id, agent_run_id, round_no, speaker_agent, target_agent, message_type, template_code, model_code, content_json, summary_text, created_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TIMESTAMP '2026-05-18 09:00:00')",
            "trace-other-symbol",
            23L,
            1,
            "supervisor_agent",
            "",
            "final_decision",
            "trade.supervisor.v1",
            "gpt-4.1",
            "{\"action\":\"HOLD\"}",
            "other_symbol"
        );
        jdbcTemplate.update(
            "insert into agent_message (trace_id, agent_run_id, round_no, speaker_agent, target_agent, message_type, template_code, model_code, content_json, summary_text, created_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TIMESTAMP '2026-05-18 10:30:00')",
            "trace-history-live",
            25L,
            1,
            "supervisor_agent",
            "",
            "final_decision",
            "trade.supervisor.v1",
            "gpt-4.1",
            "{\"action\":\"HOLD\"}",
            "other_mode"
        );
        jdbcTemplate.update(
            "insert into agent_message (trace_id, agent_run_id, round_no, speaker_agent, target_agent, message_type, template_code, model_code, content_json, summary_text, created_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TIMESTAMP '2026-05-18 11:00:00')",
            "trace-current",
            24L,
            4,
            "supervisor_agent",
            "",
            "final_decision",
            "trade.supervisor.v1",
            "gpt-4.1",
            "{\"action\":\"CLOSE\"}",
            "exclude_current"
        );
        jdbcTemplate.update(
            "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "trace-current",
            "BTCUSDT",
            "paper",
            "CLOSE",
            90,
            "exclude_current",
            "gpt-4.1",
            "openai",
            "template",
            "trade.supervisor.v1",
            "trade.supervisor.fallback",
            "trade.supervisor.v1",
            false,
            "filled",
            "FILLED"
        );

        List<AgentMessage> messages = decisionAuditMapper.selectRecentSupervisorDecisionMessages("BTCUSDT", "paper", "trace-current", 2);

        assertThat(messages).hasSize(2);
        assertThat(messages)
            .extracting(AgentMessage::getTraceId, AgentMessage::getContentJson)
            .containsExactly(
                org.assertj.core.groups.Tuple.tuple("trace-history-2", "{\"action\":\"HOLD\"}"),
                org.assertj.core.groups.Tuple.tuple("trace-history-1", "{\"action\":\"SKIP\"}")
            );
    }

    @Test
    void selectRecentSupervisorDecisionRunsBySymbolAndModeReturnsNewestRowsExcludingTrace() {
        jdbcTemplate.update(
            "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status, created_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TIMESTAMP '2026-05-18 09:00:00')",
            "trace-run-1",
            "SOLUSDT",
            "paper",
            "SKIP",
            41,
            "wait_for_breakout",
            "gpt-4.1",
            "openai",
            "template",
            "trade.supervisor.v1",
            "trade.supervisor.fallback",
            "trade.supervisor.v1",
            false,
            "skipped",
            "SKIPPED"
        );
        jdbcTemplate.update(
            "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status, created_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TIMESTAMP '2026-05-18 10:00:00')",
            "trace-run-2",
            "SOLUSDT",
            "paper",
            "HOLD",
            65,
            "hold_range_short",
            "gpt-4.1",
            "openai",
            "template",
            "trade.supervisor.v1",
            "trade.supervisor.fallback",
            "trade.supervisor.v1",
            false,
            "pending",
            "PENDING"
        );
        jdbcTemplate.update(
            "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status, created_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TIMESTAMP '2026-05-18 11:00:00')",
            "trace-run-live",
            "SOLUSDT",
            "live",
            "CLOSE",
            90,
            "other_mode",
            "gpt-4.1",
            "openai",
            "template",
            "trade.supervisor.v1",
            "trade.supervisor.fallback",
            "trade.supervisor.v1",
            false,
            "filled",
            "FILLED"
        );
        jdbcTemplate.update(
            "insert into decision_run (trace_id, symbol, mode, action, confidence, summary_reason, model_code, model_provider, prompt_source, binding_template_code, fallback_template_code, resolved_template_code, prompt_template_fallback_used, execution_status, order_status, created_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TIMESTAMP '2026-05-18 12:00:00')",
            "trace-current",
            "SOLUSDT",
            "paper",
            "NO_ACTION",
            0,
            "exclude_current",
            "gpt-4.1",
            "openai",
            "template",
            "trade.supervisor.v1",
            "trade.supervisor.fallback",
            "trade.supervisor.v1",
            false,
            "blocked",
            "BLOCKED"
        );

        List<DecisionRun> runs = decisionAuditMapper.selectRecentSupervisorDecisionRuns("SOLUSDT", "paper", "trace-current", 2);

        assertThat(runs).hasSize(2);
        assertThat(runs)
            .extracting(DecisionRun::getTraceId, DecisionRun::getAction, DecisionRun::getSummaryReason)
            .containsExactly(
                org.assertj.core.groups.Tuple.tuple("trace-run-2", "HOLD", "hold_range_short"),
                org.assertj.core.groups.Tuple.tuple("trace-run-1", "SKIP", "wait_for_breakout")
            );
    }
}
