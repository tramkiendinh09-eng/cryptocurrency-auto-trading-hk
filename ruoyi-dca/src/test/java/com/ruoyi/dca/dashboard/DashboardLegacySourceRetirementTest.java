package com.ruoyi.dca.dashboard;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

class DashboardLegacySourceRetirementTest {

    private static final Path DASHBOARD_SERVICE =
        Path.of("src", "main", "java", "com", "ruoyi", "dca", "service", "impl", "DashboardServiceImpl.java");

    @Test
    void dashboardServiceSourceNoLongerCarriesLegacyDcaChartSemantics() throws IOException {
        String source = Files.readString(DASHBOARD_SERVICE, StandardCharsets.UTF_8);

        assertThat(source)
            .doesNotContain("dca_day")
            .doesNotContain("scheduled")
            .doesNotContain("big_drop")
            .doesNotContain("big_rise")
            .doesNotContain("createTriggerQuery(")
            .doesNotContain("buildRuntimeOverview(")
            .doesNotContain("getTriggerCountByDaysAgo(");
    }
}
