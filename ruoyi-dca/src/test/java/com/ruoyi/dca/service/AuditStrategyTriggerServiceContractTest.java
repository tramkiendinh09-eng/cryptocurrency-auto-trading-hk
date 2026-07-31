package com.ruoyi.dca.service;

import com.ruoyi.dca.service.impl.AuditStrategyTriggerServiceImpl;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;

import static org.assertj.core.api.Assertions.assertThat;

class AuditStrategyTriggerServiceContractTest {

    @Test
    void legacyTriggerServiceContractDoesNotExposeCrudOrWriteMethods() {
        assertThat(IAuditStrategyTriggerService.class.getDeclaredMethods())
            .extracting(Method::getName)
            .containsExactlyInAnyOrder(
                "selectTriggerStatistics",
                "selectUserTriggerStatistics",
                "selectStrategyTriggerStatistics",
                "cleanExpiredLogs"
            );

        assertThat(AuditStrategyTriggerServiceImpl.class.getDeclaredMethods())
            .extracting(Method::getName)
            .doesNotContain(
                "selectAuditStrategyTriggerById",
                "selectAuditStrategyTriggerList",
                "insertAuditStrategyTrigger",
                "updateAuditStrategyTrigger",
                "deleteAuditStrategyTriggerByIds",
                "deleteAuditStrategyTriggerById",
                "recordTrigger"
            );
    }
}
