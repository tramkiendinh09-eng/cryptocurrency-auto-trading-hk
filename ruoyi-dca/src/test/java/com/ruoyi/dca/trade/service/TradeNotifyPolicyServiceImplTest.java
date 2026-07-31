package com.ruoyi.dca.trade.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.NotifyChannel;
import com.ruoyi.dca.domain.NotifyTemplate;
import com.ruoyi.dca.domain.trade.TradeNotifyPolicy;
import com.ruoyi.dca.domain.trade.TradeNotifyPolicyChannel;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.mapper.NotifyChannelMapper;
import com.ruoyi.dca.mapper.trade.TradeNotifyPolicyMapper;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.INotifyTemplateService;
import com.ruoyi.dca.service.trade.impl.TradeNotifyPolicyServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TradeNotifyPolicyServiceImplTest {

    @Mock
    private TradeNotifyPolicyMapper tradeNotifyPolicyMapper;

    @Mock
    private TradeStrategyMapper tradeStrategyMapper;

    @Mock
    private NotifyChannelMapper notifyChannelMapper;

    @Mock
    private INotifyTemplateService notifyTemplateService;

    @Spy
    private ObjectMapper objectMapper;

    @InjectMocks
    private TradeNotifyPolicyServiceImpl tradeNotifyPolicyService;

    @Test
    void insertTradeNotifyPolicyNormalizesScopesAndPersistsChannelBindings() {
        TradeNotifyPolicy policy = new TradeNotifyPolicy();
        policy.setPolicyName(" Runtime Risk Escalation ");
        policy.setPolicyScope(" strategy ");
        policy.setStrategyId(7L);
        policy.setEventScopeJson("[\" risk_guard_hit \",\"Decision\"]");
        policy.setSeverityScopeJson("[\" error \",\"critical\"]");
        policy.setModeScopeJson("[\" shadow \",\"LIVE\"]");
        policy.setThrottleSeconds(90);
        policy.setNotifyTemplateCode(" runtime-risk ");
        policy.setChannelBindings(List.of(channelBinding(3L, null, null), channelBinding(4L, 2, Boolean.FALSE)));

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(7L);
        when(tradeStrategyMapper.selectTradeStrategyById(7L)).thenReturn(strategy);

        NotifyChannel firstChannel = new NotifyChannel();
        firstChannel.setId(3L);
        NotifyChannel secondChannel = new NotifyChannel();
        secondChannel.setId(4L);
        when(notifyChannelMapper.selectNotifyChannelById(3L)).thenReturn(firstChannel);
        when(notifyChannelMapper.selectNotifyChannelById(4L)).thenReturn(secondChannel);
        when(notifyTemplateService.selectNotifyTemplateByCode("runtime-risk")).thenReturn(activeTemplate("runtime-risk"));
        when(tradeNotifyPolicyMapper.insertTradeNotifyPolicy(any(TradeNotifyPolicy.class))).thenAnswer(invocation -> {
            TradeNotifyPolicy saved = invocation.getArgument(0);
            saved.setId(11L);
            return 1;
        });
        when(tradeNotifyPolicyMapper.insertTradeNotifyPolicyChannels(any())).thenReturn(2);

        tradeNotifyPolicyService.insertTradeNotifyPolicy(policy);

        ArgumentCaptor<TradeNotifyPolicy> policyCaptor = ArgumentCaptor.forClass(TradeNotifyPolicy.class);
        verify(tradeNotifyPolicyMapper).insertTradeNotifyPolicy(policyCaptor.capture());
        assertThat(policyCaptor.getValue().getPolicyName()).isEqualTo("Runtime Risk Escalation");
        assertThat(policyCaptor.getValue().getPolicyScope()).isEqualTo("STRATEGY");
        assertThat(policyCaptor.getValue().getEventScopeJson()).isEqualTo("[\"risk_guard_hit\",\"decision\"]");
        assertThat(policyCaptor.getValue().getSeverityScopeJson()).isEqualTo("[\"ERROR\",\"CRITICAL\"]");
        assertThat(policyCaptor.getValue().getModeScopeJson()).isEqualTo("[\"shadow\",\"live\"]");
        assertThat(policyCaptor.getValue().getNotifyTemplateCode()).isEqualTo("runtime-risk");
        assertThat(policyCaptor.getValue().getEnabled()).isTrue();

        ArgumentCaptor<List<TradeNotifyPolicyChannel>> channelCaptor = ArgumentCaptor.forClass(List.class);
        verify(tradeNotifyPolicyMapper).insertTradeNotifyPolicyChannels(channelCaptor.capture());
        assertThat(channelCaptor.getValue())
            .extracting(TradeNotifyPolicyChannel::getPolicyId, TradeNotifyPolicyChannel::getChannelId, TradeNotifyPolicyChannel::getChannelOrder, TradeNotifyPolicyChannel::getEnabled)
            .containsExactly(
                org.assertj.core.groups.Tuple.tuple(11L, 3L, 1, true),
                org.assertj.core.groups.Tuple.tuple(11L, 4L, 2, false)
            );
    }

    @Test
    void insertTradeNotifyPolicyRejectsMissingChannelBindings() {
        TradeNotifyPolicy policy = new TradeNotifyPolicy();
        policy.setPolicyName("Runtime Alerts");
        policy.setPolicyScope("GLOBAL");
        policy.setEventScopeJson("[\"decision\"]");
        policy.setSeverityScopeJson("[\"ERROR\"]");
        policy.setModeScopeJson("[\"paper\"]");
        policy.setNotifyTemplateCode("runtime-risk");
        when(notifyTemplateService.selectNotifyTemplateByCode("runtime-risk")).thenReturn(activeTemplate("runtime-risk"));

        assertThatThrownBy(() -> tradeNotifyPolicyService.insertTradeNotifyPolicy(policy))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("channel");
    }

    @Test
    void insertTradeNotifyPolicyRejectsStrategyScopedPolicyWithoutExistingStrategy() {
        TradeNotifyPolicy policy = new TradeNotifyPolicy();
        policy.setPolicyName("Runtime Alerts");
        policy.setPolicyScope("STRATEGY");
        policy.setStrategyId(77L);
        policy.setEventScopeJson("[\"decision\"]");
        policy.setSeverityScopeJson("[\"ERROR\"]");
        policy.setModeScopeJson("[\"shadow\"]");
        policy.setChannelBindings(List.of(channelBinding(3L, 1, Boolean.TRUE)));
        when(tradeStrategyMapper.selectTradeStrategyById(77L)).thenReturn(null);

        assertThatThrownBy(() -> tradeNotifyPolicyService.insertTradeNotifyPolicy(policy))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("strategy");
    }

    private static TradeNotifyPolicyChannel channelBinding(Long channelId, Integer order, Boolean enabled) {
        TradeNotifyPolicyChannel binding = new TradeNotifyPolicyChannel();
        binding.setChannelId(channelId);
        binding.setChannelOrder(order);
        binding.setEnabled(enabled);
        return binding;
    }

    private static NotifyTemplate activeTemplate(String code) {
        NotifyTemplate template = new NotifyTemplate();
        template.setCode(code);
        template.setIsActive(1);
        return template;
    }
}
