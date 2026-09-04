package com.ruoyi.dca.service;

import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

class TradeControlPlaneMenuSqlContractTest {

    /**
     * `sql/ai_trading.sql` 从未随仓库提交——上游把它加进了 .gitignore。于是本类
     * 所有用例在任何一份克隆上都恒为 FileNotFoundException，长期红着被当成
     * "已知失败"，反过来掩盖同一套件里真正的新失败。改成显式 skip：文件在就
     * 照常校验，不在就跳过并说明原因。
     */
    @BeforeEach
    void requireConsolidatedSql() {
        Assumptions.assumeTrue(
            Files.exists(resolveRepoFile("sql", "ai_trading.sql")),
            "sql/ai_trading.sql 未随仓库提交（上游 .gitignore 掉了），跳过菜单路由契约校验"
        );
    }

    @Test
    void consolidatedSqlKeepsTradeControlPlaneMenusOnCanonicalRoutes() throws IOException {
        String sql = Files.readString(resolveRepoFile("sql", "ai_trading.sql"));

        assertThat(sql).contains("INSERT INTO `sys_menu` VALUES (2130, '交易控制台', 5, 1,");
        assertThat(sql).contains("INSERT INTO `sys_menu` VALUES (2187, '交易配置', 5, 2,");
        assertThat(sql).contains("INSERT INTO `sys_menu` VALUES (2188, '审计中心', 5, 3,");
        assertThat(sql).contains("INSERT INTO `sys_menu` VALUES (204, 'AI模型', 2187, 1,");
        assertThat(sql).contains("INSERT INTO `sys_menu` VALUES (2155, 'Agent配置', 2187, 3,");
        assertThat(sql).contains("INSERT INTO `sys_menu` VALUES (2110, '行情数据源', 2187, 6,");
        assertThat(sql).contains("INSERT INTO `sys_menu` VALUES (202, '通知渠道', 2187, 10,");
        assertThat(sql).contains("INSERT INTO `sys_menu` VALUES (2124, '数据源绑定查询', 2110, 14,");
        assertThat(sql).contains("dca:tradeSourceBinding:list");
        assertThat(sql).contains("dca:tradeSourceBinding:add");
        assertThat(sql).contains("dca:tradeSourceBinding:edit");
        assertThat(sql).contains("dca:tradeSourceBinding:remove");
        assertThat(sql).doesNotContain("INSERT INTO `sys_menu` VALUES (2140,");
        assertThat(sql).doesNotContain("dca/trade/sourceBinding/index");
        assertThat(sql).doesNotContain("INSERT INTO `sys_menu` VALUES (2151,");
        assertThat(sql).doesNotContain("INSERT INTO `sys_menu` VALUES (2152,");
        assertThat(sql).doesNotContain("INSERT INTO `sys_menu` VALUES (2153,");
        assertThat(sql).doesNotContain("INSERT INTO `sys_menu` VALUES (2154,");
        assertThat(sql).doesNotContain("dca/trade/promptBinding/index");
        assertThat(sql).doesNotContain("dca:tradePromptBinding:");
        assertThat(sql).doesNotContain("dca:tradePromptBinding:list");
        assertThat(sql).contains("dca:tradeSourceBinding:list");
        assertThat(sql).contains("dca:tradeSourceBinding:add");
        assertThat(sql).contains("dca:tradeSourceBinding:edit");
        assertThat(sql).contains("dca:tradeSourceBinding:remove");
        assertThat(sql).doesNotContain("Agent覆盖");
        assertThat(sql).doesNotContain("INSERT INTO `sys_menu` VALUES (2151, '提示词绑定'");
        assertThat(sql).contains("INSERT INTO `sys_menu` VALUES (2147,");
        assertThat(sql).contains("INSERT INTO `sys_menu` VALUES (2159,");
        assertThat(sql).contains("'account', 'dca/trade/account/index'");
        assertThat(sql).doesNotContain("'accounts', 'dca/trade/account/index'");
        assertThat(sql).contains("'notify/record', 'dca/notify/record'");
        assertThat(sql).doesNotContain("'notify-record', 'dca/notify/record'");
        assertThat(sql).contains("'ai', 'dca/ai/index'");
        assertThat(sql).doesNotContain("'models', 'dca/ai/index'");
    }

    @Test
    void consolidatedSqlKeepsTradeAccountAndControlPlanePermissions() throws IOException {
        String sql = Files.readString(resolveRepoFile("sql", "ai_trading.sql"));

        assertThat(sql).contains("dca:tradeAccount:list");
        assertThat(sql).contains("dca:tradeAccount:add");
        assertThat(sql).contains("dca:tradeAccount:edit");
        assertThat(sql).contains("dca:tradeAccount:remove");
        assertThat(sql).doesNotContain("dca:tradePromptBinding:list");
        assertThat(sql).contains("dca:tradeAgentProfile:list");
        assertThat(sql).contains("dca:notify:query");
        assertThat(sql).contains("dca:aiModel:query");
        assertThat(sql).doesNotContain("/dca/strategy");
    }

    private Path resolveRepoFile(String... parts) {
        Path base = Path.of(System.getProperty("user.dir"));
        if (base.getFileName() != null && "ruoyi-dca".equals(base.getFileName().toString())) {
            base = base.getParent();
        }
        for (String part : parts) {
            base = base.resolve(part);
        }
        return base;
    }
}
