package com.ruoyi.dca.service;

import java.util.Arrays;
import java.util.Set;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class DashboardServiceContractTest {

    @Test
    void dashboardServiceInterfaceOnlyExposesRuntimeOverviewContracts() {
        Set<String> methodNames = Arrays.stream(IDashboardService.class.getDeclaredMethods())
            .map(method -> method.getName())
            .collect(Collectors.toSet());

        assertThat(methodNames)
            .containsExactlyInAnyOrder("getOverview", "getOverviewMap");
    }
}
