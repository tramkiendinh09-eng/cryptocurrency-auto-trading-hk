package com.ruoyi.dca.sql;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Disabled;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

@Disabled("Replaced by consolidated ai_trading.sql contract tests")
class SplitBootstrapSqlContractTest {

    private static final Path RUOYI_BOOT_SQL = Path.of("..", "sql", "ruoyi_boot_min.sql");
    private static final Path TRADE_BOOT_SQL = Path.of("..", "sql", "trade_runtime_boot_min.sql");
    private static final Path SQL_DIR = Path.of("..", "sql");

    @Test
    void minimalRuoyiBootstrapKeepsOnlyFrameworkTablesNeededForTradeConsole() throws IOException {
        String sql = Files.readString(RUOYI_BOOT_SQL, StandardCharsets.UTF_8);

        assertThat(sql)
            .contains("最小 RuoYi 框架初始化")
            .contains("CREATE TABLE `sys_config`")
            .contains("CREATE TABLE `sys_dept`")
            .contains("CREATE TABLE `sys_dict_type`")
            .contains("CREATE TABLE `sys_dict_data`")
            .contains("CREATE TABLE `sys_logininfor`")
            .contains("CREATE TABLE `sys_menu`")
            .contains("CREATE TABLE `sys_oper_log`")
            .contains("CREATE TABLE `sys_post`")
            .contains("CREATE TABLE `sys_role`")
            .contains("CREATE TABLE `sys_role_dept`")
            .contains("CREATE TABLE `sys_role_menu`")
            .contains("CREATE TABLE `sys_user`")
            .contains("CREATE TABLE `sys_user_post`")
            .contains("CREATE TABLE `sys_user_role`")
            .contains("INSERT INTO `sys_menu` VALUES (5,")
            .contains("INSERT INTO `sys_menu` VALUES (2110,")
            .contains("INSERT INTO `sys_menu` VALUES (2130,")
            .contains("INSERT INTO `sys_menu` VALUES (2147,")
            .contains("INSERT INTO `sys_menu` VALUES (2151,")
            .contains("INSERT INTO `sys_menu` VALUES (2155,")
            .contains("INSERT INTO `sys_user` VALUES (1,")
            .contains("INSERT INTO `sys_role` VALUES (1,")
            .contains("INSERT INTO `sys_role_menu` VALUES (1, 2130)")
            .doesNotContain("CREATE TABLE `sys_job`")
            .doesNotContain("CREATE TABLE `sys_job_log`")
            .doesNotContain("CREATE TABLE `sys_notice`")
            .doesNotContain("CREATE TABLE `sys_notice_read`")
            .doesNotContain("CREATE TABLE `gen_table`")
            .doesNotContain("CREATE TABLE `gen_table_column`")
            .doesNotContain("CREATE TABLE `QRTZ_");
    }

    @Test
    void minimalTradeBootstrapKeepsRuntimeMainlineTablesAndDefaultSeeds() throws IOException {
        String sql = Files.readString(TRADE_BOOT_SQL, StandardCharsets.UTF_8);

        assertThat(sql)
            .contains("最小自动交易系统初始化")
            .contains("CREATE TABLE `ai_model_config`")
            .contains("CREATE TABLE `market_api_config`")
            .contains("`version_no` int NOT NULL DEFAULT 1")
            .contains("`transport_type` varchar(16)")
            .contains("`vendor_code` varchar(32)")
            .contains("`market_scope` varchar(16)")
            .contains("`ws_base_url` varchar(255)")
            .contains("`ws_stream_name_template` text")
            .contains("`doc_reference_url` varchar(500)")
            .contains("CREATE TABLE `market_data_config`")
            .contains("CREATE TABLE `market_collect_task`")
            .contains("CREATE TABLE `market_data`")
            .contains("CREATE TABLE `market_data_collect_log`")
            .contains("CREATE TABLE `prompt_template`")
            .contains("CREATE TABLE `notify_channel`")
            .contains("CREATE TABLE `notify_record`")
            .contains("CREATE TABLE `risk_check_config`")
            .contains("CREATE TABLE `risk_check_log`")
            .contains("CREATE TABLE `card_key`")
            .contains("CREATE TABLE `audit_ai_call_log`")
            .contains("CREATE TABLE `audit_operation_log`")
            .contains("CREATE TABLE `audit_strategy_trigger`")
            .contains("CREATE TABLE `dca_strategy`")
            .contains("CREATE TABLE `dca_record`")
            .contains("CREATE TABLE `dca_user_portfolio`")
            .contains("CREATE TABLE `trade_runtime_config`")
            .contains("CREATE TABLE `trade_strategy`")
            .contains("CREATE TABLE `trade_strategy_version`")
            .contains("CREATE TABLE `trade_symbol_scope`")
            .contains("CREATE TABLE `exchange_account`")
            .contains("CREATE TABLE `exchange_account_binding`")
            .contains("CREATE TABLE `trade_data_source_binding`")
            .contains("CREATE TABLE `trade_notify_policy`")
            .contains("CREATE TABLE `trade_notify_policy_channel`")
            .contains("CREATE TABLE `trade_prompt_binding`")
            .contains("CREATE TABLE `trade_agent_profile`")
            .contains("CREATE TABLE `trade_account_snapshot`")
            .contains("CREATE TABLE `trade_account_position_snapshot`")
            .contains("CREATE TABLE `trade_data_source_health_log`")
            .contains("CREATE TABLE `event_raw`")
            .contains("CREATE TABLE `market_event`")
            .contains("CREATE TABLE `news_event`")
            .contains("CREATE TABLE `onchain_event`")
            .contains("CREATE TABLE `social_event`")
            .contains("CREATE TABLE `signal_event`")
            .contains("CREATE TABLE `feature_snapshot`")
            .contains("CREATE TABLE `signal_score`")
            .contains("CREATE TABLE `signal_window_state`")
            .contains("CREATE TABLE `agent_run`")
            .contains("CREATE TABLE `agent_observation`")
            .contains("CREATE TABLE `agent_message`")
            .contains("CREATE TABLE `agent_conclusion`")
            .contains("CREATE TABLE `decision_run`")
            .contains("CREATE TABLE `decision_action`")
            .contains("CREATE TABLE `risk_guard_hit`")
            .contains("CREATE TABLE `order_request`")
            .contains("CREATE TABLE `exchange_order`")
            .contains("CREATE TABLE `exchange_fill`")
            .contains("CREATE TABLE `position_snapshot`")
            .contains("CREATE TABLE `position_change_log`")
            .contains("CREATE TABLE `pnl_snapshot`")
            .contains("CREATE TABLE `replay_session`")
            .contains("CREATE TABLE `replay_event`")
            .contains("CREATE TABLE `paper_trade_order`")
            .contains("CREATE TABLE `shadow_decision_log`")
            .contains("`deliberation_enabled`")
            .contains("`route_scheduler_mode`")
            .contains("`prompt_template_fallback_used`")
            .contains("`source_type`")
            .contains("`signal_type`")
            .contains("`strength_score`")
            .contains("`dedupe_key`")
            .contains("`dispatch_mode`")
            .contains("`selected_agents_json`")
            .contains("`combination_match_json`")
            .contains("`active_signal_refs_json`")
            .contains("\"triggerMode\":\"EVENT_GATED\"")
            .contains("\"ruleOnlyPriceChangePct\":1.0")
            .contains("\"ruleOnlyScoreThreshold\":0.7")
            .contains("\"signalMemoryPolicy\"")
            .contains("\"llmBudgetPolicy\"")
            .contains("\"targetDispatchMode\":\"LLM_ALLOWED\"")
            .doesNotContain("\"upgradeTo\"")
            .contains("BINANCE_FUTURES_TICKER_WS")
            .contains("trade.supervisor.v1")
            .contains("trade.supervisor.fallback")
            .contains("trade.market.v1")
            .contains("trade.news.v1")
            .contains("trade.onchain.v1")
            .contains("trade.social.v1")
            .contains("supervisor_agent")
            .contains("market_agent")
            .contains("news_agent")
            .contains("onchain_agent")
            .contains("social_agent")
            .contains("btc-event-shadow")
            .doesNotContain("CREATE TABLE `market_data_history`")
            .doesNotContain("ADD COLUMN IF NOT EXISTS");
    }

    @Test
    void sqlDirectoryKeepsOnlyTwoBootstrapScripts() throws IOException {
        try (var stream = Files.list(SQL_DIR)) {
            List<String> entries = stream
                .map(path -> path.getFileName().toString())
                .sorted()
                .toList();

            assertThat(entries).containsExactly("ruoyi_boot_min.sql", "trade_runtime_boot_min.sql");
        }
    }
}
