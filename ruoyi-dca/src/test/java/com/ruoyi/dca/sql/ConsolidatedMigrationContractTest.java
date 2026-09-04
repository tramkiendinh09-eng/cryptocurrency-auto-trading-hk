package com.ruoyi.dca.sql;

import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

class ConsolidatedMigrationContractTest {

    private static final Path SQL = Path.of("..", "sql", "ai_trading.sql").normalize();

    /**
     * `sql/ai_trading.sql` 从未随仓库提交——上游把它加进了 .gitignore，README 声称
     * 保留的两个引导脚本也没提交。于是本类所有用例在任何一份克隆上都恒为
     * FileNotFoundException，长期红着被当成"已知失败"，反过来掩盖同一套件里
     * 真正的新失败（本轮排查数据清理任务时，正是"日志里只有一行泛泛的错误"
     * 让它藏了几天）。
     *
     * 改成显式 skip：文件在就照常校验，不在就跳过并说明原因。本部署的 schema
     * 是从 mapper/实体反推重建的，真实来源在 sql/trade_runtime_boot_min.sql
     * 与 sql/migrations/ 下。
     */
    @BeforeEach
    void requireConsolidatedSql() {
        Assumptions.assumeTrue(
            Files.exists(SQL),
            "sql/ai_trading.sql 未随仓库提交（上游 .gitignore 掉了），跳过合并 SQL 契约校验"
        );
    }

    @Test
    void consolidatedSqlDefinesExecutionCredentialAndScopeTables() throws IOException {
        String sql = Files.readString(SQL);

        assertThat(sql).containsIgnoringCase("CREATE TABLE `trade_symbol_scope`");
        assertThat(sql).containsIgnoringCase("exchange_code");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `exchange_account_binding`");
        assertThat(sql).containsIgnoringCase("account_id");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `exchange_account`");
        assertThat(sql).containsIgnoringCase("passphrase_ciphertext");
        assertThat(sql).containsIgnoringCase("api_base_url");
        assertThat(sql).containsIgnoringCase("testnet");
        assertThat(sql).containsIgnoringCase("demo_trading");
    }

    @Test
    void consolidatedSqlDefinesTypedEventReplayAndDispatchAuditTables() throws IOException {
        String sql = Files.readString(SQL);

        assertThat(sql).containsIgnoringCase("CREATE TABLE `event_raw`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `market_event`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `news_event`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `onchain_event`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `social_event`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `decision_run`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `decision_action`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `feature_snapshot`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `signal_score`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `signal_window_state`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `agent_run`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `agent_observation`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `position_snapshot`");
        assertThat(sql).containsIgnoringCase("INDEX `idx_position_snapshot_scope_latest`");
        assertThat(sql).doesNotContainIgnoringCase("UNIQUE INDEX `uk_position_snapshot_scope`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `replay_session`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `replay_event`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `paper_trade_order`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `shadow_decision_log`");
        assertThat(sql).containsIgnoringCase("dispatch_mode");
        assertThat(sql).containsIgnoringCase("selected_agents_json");
        assertThat(sql).containsIgnoringCase("combination_match_json");
        assertThat(sql).containsIgnoringCase("active_signal_refs_json");
    }

    @Test
    void consolidatedSqlDefinesPromptBindingAndAgentProfileSchema() throws IOException {
        String sql = Files.readString(SQL);

        assertThat(sql).containsIgnoringCase("CREATE TABLE `trade_prompt_binding`");
        assertThat(sql).containsIgnoringCase("binding_scope");
        assertThat(sql).containsIgnoringCase("output_schema_code");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `trade_agent_profile`");
        assertThat(sql).containsIgnoringCase("agent_code");
        assertThat(sql).containsIgnoringCase("structured_schema_code");
        assertThat(sql).containsIgnoringCase("`deliberation_enabled`");
        assertThat(sql).containsIgnoringCase("`deliberation_max_rounds`");
        assertThat(sql).containsIgnoringCase("`deliberation_fail_open`");
        assertThat(sql).containsIgnoringCase("CREATE TABLE `agent_message`");
        assertThat(sql).containsIgnoringCase("speaker_agent");
        assertThat(sql).containsIgnoringCase("message_type");
        assertThat(sql).containsIgnoringCase("`route_max_concurrency`");
        assertThat(sql).containsIgnoringCase("`route_scheduler_mode`");
    }

    @Test
    void consolidatedSqlSeedsSupervisorPromptWithPositionTimeContext() throws IOException {
        String sql = Files.readString(SQL);

        assertThat(sql).contains("当前持仓开仓时间：{current_position_opened_at}");
        assertThat(sql).contains("当前决策时间：{current_time}");
        assertThat(sql).contains("当前持仓时长（分钟）：{current_position_holding_minutes}");
    }

    @Test
    void consolidatedSqlPersistsPeakAccountEquityInPnlSnapshots() throws IOException {
        String sql = Files.readString(SQL);

        assertThat(sql).containsIgnoringCase("CREATE TABLE `pnl_snapshot`");
        assertThat(sql).containsIgnoringCase("`peak_account_equity` decimal(20, 8) NOT NULL DEFAULT 0.00000000");
    }


}
