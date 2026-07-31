package com.ruoyi.dca.sql;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class ConsolidatedSqlBootstrapContractTest {

    private static final Path SQL = Path.of("..", "sql", "ai_trading.sql");
    private static final Path SQL_DIR = Path.of("..", "sql");

    @Test
    void consolidatedSqlKeepsFrameworkAndRuntimeSchemasTogether() throws IOException {
        String sql = Files.readString(SQL, StandardCharsets.UTF_8);

        assertThat(sql)
            .contains("CREATE TABLE `sys_menu`")
            .contains("CREATE TABLE `sys_role`")
            .contains("CREATE TABLE `sys_role_menu`")
            .contains("CREATE TABLE `sys_user`")
            .contains("CREATE TABLE `ai_model_config`")
            .contains("CREATE TABLE `market_api_config`")
            .contains("CREATE TABLE `notify_channel`")
            .contains("CREATE TABLE `notify_template`")
            .contains("CREATE TABLE `notify_record`")
            .contains("CREATE TABLE `trade_runtime_config`")
            .contains("CREATE TABLE `trade_strategy`")
            .contains("CREATE TABLE `trade_notify_policy`")
            .contains("CREATE TABLE `trade_notify_policy_channel`")
            .contains("CREATE TABLE `trade_prompt_binding`")
            .contains("CREATE TABLE `trade_agent_profile`")
            .contains("CREATE TABLE `trade_position_guard`")
            .contains("CREATE TABLE `decision_run`")
            .contains("CREATE TABLE `exchange_order`")
            .contains("CREATE TABLE `exchange_fill`")
            .contains("CREATE TABLE `position_snapshot`");
    }

    @Test
    void consolidatedSqlSeedsRuntimeReferencesWithoutDanglingDefaults() throws IOException {
        String sql = Files.readString(SQL, StandardCharsets.UTF_8);

        assertThat(sql).contains("INSERT INTO `ai_model_config` VALUES (6, 'deepseek-reasoner'");
        assertThat(sql).doesNotContain("api.okinto.com");
        assertThat(sql).contains("\\\"aiModelId\\\":6");
        assertThat(sql).contains("INSERT INTO `notify_channel` VALUES (1, 1, 'email', '通用渠道'");
        assertThat(sql).contains("INSERT INTO `notify_template` VALUES (1, '运行时风险通知', 'notify.runtime.risk.v1'");
        assertThat(sql).contains("\\\"channels\\\": [\\\"runtime_console\\\"]");
        assertThat(sql).contains("INSERT INTO `trade_notify_policy` VALUES (1, 'runtime-critical-events', 'GLOBAL', NULL, '[\\\"risk_guard_hit\\\", \\\"source_health\\\", \\\"execution_failed\\\"]', '[\\\"WARN\\\", \\\"ERROR\\\"]', '[\\\"shadow\\\", \\\"live\\\"]', 60, 'notify.runtime.risk.v1', 1,");
    }

    @Test
    void consolidatedSqlKeepsCurrentEventGatedRuntimePolicyShape() throws IOException {
        String sql = Files.readString(SQL, StandardCharsets.UTF_8);

        assertThat(sql)
            .contains("\\\"triggerMode\\\": \\\"EVENT_GATED\\\"")
            .contains("\\\"targetDispatchMode\\\": \\\"LLM_ALLOWED\\\"")
            .contains("\\\"signalMemoryPolicy\\\"")
            .contains("\\\"llmBudgetPolicy\\\"")
            .doesNotContain("\"upgradeTo\"");
    }

    @Test
    void consolidatedSqlKeepsAgentProfileAsDefaultExecutionConfigOwner() throws IOException {
        String sql = Files.readString(SQL, StandardCharsets.UTF_8);

        assertThat(sql)
            .contains("`default_model_id` bigint NULL DEFAULT NULL")
            .contains("`default_template_code` varchar(64)")
            .contains("`default_output_schema_code` varchar(64)")
            .contains("INSERT INTO `trade_agent_profile` VALUES (1, 'supervisor_agent', 'Supervisor Agent', 'HYBRID'")
            .contains("INSERT INTO `trade_agent_profile` VALUES (2, 'market_agent', 'Market Agent', 'LLM'")
            .contains("INSERT INTO `trade_agent_profile` VALUES (3, 'news_agent', 'News Agent', 'LLM'")
            .contains("INSERT INTO `trade_agent_profile` VALUES (4, 'onchain_agent', 'Onchain Agent', 'LLM'")
            .contains("INSERT INTO `trade_agent_profile` VALUES (5, 'social_agent', 'Social Agent', 'LLM'")
            .contains("'trade.supervisor.v1'")
            .contains("'trade.market.v1'")
            .contains("'trade.news.v1'")
            .contains("'trade.onchain.v1'")
            .contains("'trade.social.v1'")
            .doesNotContain("INSERT INTO `trade_prompt_binding` VALUES");

        assertThat(sql)
            .contains("`template_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL")
            .contains("`output_schema_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL");
    }

    @Test
    void consolidatedSqlSeedsOkxMarketWebsocketWithSupplementalChannels() throws IOException {
        String sql = Files.readString(SQL, StandardCharsets.UTF_8);

        assertThat(sql)
            .contains("`ws_stream_name_template` text")
            .contains("OKX_SWAP_TICKER_WS")
            .contains("/ws/v5/public")
            .contains("\\\"channel\\\":\\\"tickers\\\"")
            .contains("\\\"channel\\\":\\\"mark-price\\\"")
            .contains("\\\"channel\\\":\\\"funding-rate\\\"")
            .contains("\\\"channel\\\":\\\"open-interest\\\"")
            .contains("\\\"channel\\\":\\\"liquidation-orders\\\"")
            .contains("'OKX', 'FUTURES', 'wss://ws.okx.com:8443', '/ws/v5/public'");
    }

    @Test
    void sqlDirectoryKeepsSingleConsolidatedBootstrapScript() throws IOException {
        try (var stream = Files.list(SQL_DIR)) {
            List<String> bootstrapScripts = stream
                .map(path -> path.getFileName().toString())
                .filter(name -> name.equals("ai_trading.sql"))
                .sorted()
                .toList();
            assertThat(bootstrapScripts).containsExactly("ai_trading.sql");
        }
    }
}
