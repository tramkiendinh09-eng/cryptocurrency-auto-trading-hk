package com.ruoyi.dca.runtime;

import com.ruoyi.dca.domain.trade.TradeRuntimeConfig;
import com.ruoyi.dca.mapper.task.TradeDataCleanupMapper;
import com.ruoyi.dca.service.trade.ITradeRuntimeConfigService;
import com.ruoyi.dca.task.TradeDataCleanupTask;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.scheduling.annotation.Scheduled;

import java.lang.reflect.Method;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TradeDataCleanupTaskTest {

    @Mock
    private TradeDataCleanupMapper cleanupMapper;

    @Mock
    private ITradeRuntimeConfigService runtimeConfigService;

    @InjectMocks
    private TradeDataCleanupTask cleanupTask;

    @Test
    void cleanExpiredEventAndSignalDataRunsAtBeijing1030EveryDay() throws Exception {
        Method method = TradeDataCleanupTask.class.getMethod("cleanExpiredEventAndSignalData");
        Scheduled scheduled = method.getAnnotation(Scheduled.class);

        assertThat(scheduled).isNotNull();
        assertThat(scheduled.cron()).isEqualTo("0 30 10 * * ?");
        assertThat(scheduled.zone()).isEqualTo("Asia/Shanghai");
    }

    @Test
    void cleanExpiredEventAndSignalDataDeletesOnlyEventAndSignalTablesUsingRuntimeRetention() {
        TradeRuntimeConfig runtimeConfig = new TradeRuntimeConfig();
        runtimeConfig.setEventRetentionDays(7);
        when(runtimeConfigService.getCurrentConfig()).thenReturn(runtimeConfig);
        when(cleanupMapper.deleteSignalScoresBefore(anyString())).thenReturn(2);
        when(cleanupMapper.deleteSignalEventsBefore(anyString())).thenReturn(3);
        when(cleanupMapper.deleteExpiredSignalWindowStatesBefore(anyString())).thenReturn(4);
        when(cleanupMapper.deleteMarketEventsBefore(anyString())).thenReturn(5);
        when(cleanupMapper.deleteMarketKlineSnapshotsBefore(anyString())).thenReturn(6);
        when(cleanupMapper.deleteMarketMetricSnapshotsBefore(anyString())).thenReturn(7);
        when(cleanupMapper.deleteNewsEventsBefore(anyString())).thenReturn(8);
        when(cleanupMapper.deleteOnchainEventsBefore(anyString())).thenReturn(9);
        when(cleanupMapper.deleteSocialEventsBefore(anyString())).thenReturn(10);
        when(cleanupMapper.deleteEventRawsBefore(anyString())).thenReturn(11);

        int deletedRows = cleanupTask.cleanExpiredEventAndSignalData();

        assertThat(deletedRows).isEqualTo(65);
        ArgumentCaptor<String> cutoffCaptor = ArgumentCaptor.forClass(String.class);
        verify(cleanupMapper).deleteSignalScoresBefore(cutoffCaptor.capture());
        String cutoffTime = cutoffCaptor.getValue();
        assertThat(cutoffTime).matches("\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}");
        verify(cleanupMapper).deleteSignalEventsBefore(cutoffTime);
        verify(cleanupMapper).deleteExpiredSignalWindowStatesBefore(cutoffTime);
        verify(cleanupMapper).deleteMarketEventsBefore(cutoffTime);
        verify(cleanupMapper).deleteMarketKlineSnapshotsBefore(cutoffTime);
        verify(cleanupMapper).deleteMarketMetricSnapshotsBefore(cutoffTime);
        verify(cleanupMapper).deleteNewsEventsBefore(cutoffTime);
        verify(cleanupMapper).deleteOnchainEventsBefore(cutoffTime);
        verify(cleanupMapper).deleteSocialEventsBefore(cutoffTime);
        verify(cleanupMapper).deleteEventRawsBefore(cutoffTime);

        InOrder order = inOrder(cleanupMapper);
        order.verify(cleanupMapper).deleteSignalScoresBefore(cutoffTime);
        order.verify(cleanupMapper).deleteSignalEventsBefore(cutoffTime);
    }
}
