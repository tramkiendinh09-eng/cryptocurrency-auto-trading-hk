package com.ruoyi.dca.utils;

import com.ruoyi.dca.service.IAuditAiCallLogService;
import com.ruoyi.dca.service.IAuditOperationLogService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.verifyNoInteractions;

@ExtendWith(MockitoExtension.class)
class AuditLogUtilsTest {

    @Mock
    private IAuditOperationLogService auditOperationLogService;

    @Mock
    private IAuditAiCallLogService auditAiCallLogService;

    @InjectMocks
    private AuditLogUtils auditLogUtils;

    @Test
    void recordTriggerDoesNotCallLegacyTriggerPersistence() {
        assertThatCode(() -> auditLogUtils.recordTrigger(
            11L,
            7L,
            "runtime_event",
            new BigDecimal("64000"),
            new BigDecimal("62000"),
            new BigDecimal("-3.12"),
            new BigDecimal("-2.50"),
            1,
            "triggered",
            "legacy",
            "{}"
        )).doesNotThrowAnyException();

        verifyNoInteractions(auditOperationLogService, auditAiCallLogService);
    }
}
