package com.ruoyi.dca.trade.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.domain.PromptTemplate;
import com.ruoyi.dca.domain.trade.TradeAgentProfile;
import com.ruoyi.dca.mapper.trade.TradeAgentProfileMapper;
import com.ruoyi.dca.service.IAiModelConfigService;
import com.ruoyi.dca.service.IPromptTemplateService;
import com.ruoyi.dca.service.trade.impl.TradeAgentProfileServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TradeAgentProfileServiceImplTest {

    @Mock
    private TradeAgentProfileMapper tradeAgentProfileMapper;

    @Mock
    private IAiModelConfigService aiModelConfigService;

    @Mock
    private IPromptTemplateService promptTemplateService;

    @Spy
    private ObjectMapper objectMapper;

    @InjectMocks
    private TradeAgentProfileServiceImpl tradeAgentProfileService;

    @Test
    void insertTradeAgentProfileNormalizesDefaultsAndJsonPayloads() {
        TradeAgentProfile profile = new TradeAgentProfile();
        profile.setAgentCode(" market_agent ");
        profile.setAgentName(" Market Agent ");
        profile.setAgentType(" llm ");
        profile.setDialogueEnabled(Boolean.TRUE);
        profile.setMaxDialogueRounds(2);
        profile.setSpeakOrder(1);
        profile.setTimeoutSeconds(45);
        profile.setMaxRetries(2);
        profile.setStructuredSchemaCode(" agent_view_v1 ");
        profile.setDefaultModelId(21L);
        profile.setDefaultTemplateCode(" trade.market.v1 ");
        profile.setDefaultOutputSchemaCode(" agent_view_v1 ");
        profile.setToolPolicyJson("{\"web_search\":false}");
        profile.setRuntimeOptionsJson("{\"reasoning_effort\":\"medium\"}");

        mockEnabledModel(21L);
        mockActiveTemplate("trade.market.v1");
        when(tradeAgentProfileMapper.insertTradeAgentProfile(profile)).thenReturn(1);

        int rows = tradeAgentProfileService.insertTradeAgentProfile(profile);

        ArgumentCaptor<TradeAgentProfile> captor = ArgumentCaptor.forClass(TradeAgentProfile.class);
        verify(tradeAgentProfileMapper).insertTradeAgentProfile(captor.capture());
        TradeAgentProfile saved = captor.getValue();
        assertThat(rows).isEqualTo(1);
        assertThat(saved.getAgentCode()).isEqualTo("market_agent");
        assertThat(saved.getAgentName()).isEqualTo("Market Agent");
        assertThat(saved.getAgentType()).isEqualTo("LLM");
        assertThat(saved.getEnabled()).isTrue();
        assertThat(saved.getLlmEnabled()).isTrue();
        assertThat(saved.getDialogueEnabled()).isTrue();
        assertThat(saved.getStructuredSchemaCode()).isEqualTo("agent_view_v1");
        assertThat(saved.getDefaultTemplateCode()).isEqualTo("trade.market.v1");
        assertThat(saved.getDefaultOutputSchemaCode()).isEqualTo("agent_view_v1");
        assertThat(saved.getToolPolicyJson()).isEqualTo("{\"web_search\":false}");
        assertThat(saved.getRuntimeOptionsJson()).isEqualTo("{\"reasoning_effort\":\"medium\"}");
    }

    @Test
    void insertTradeAgentProfileRejectsLlmAgentWithoutDefaultModelOrTemplate() {
        TradeAgentProfile profile = new TradeAgentProfile();
        profile.setAgentCode("market_agent");
        profile.setAgentName("Market Agent");
        profile.setAgentType("LLM");
        profile.setLlmEnabled(Boolean.TRUE);
        profile.setStructuredSchemaCode("agent_view_v1");
        profile.setDefaultOutputSchemaCode("agent_view_v1");

        assertThatThrownBy(() -> tradeAgentProfileService.insertTradeAgentProfile(profile))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("defaultModelId");
    }

    @Test
    void insertTradeAgentProfileRejectsSupervisorWithWrongDefaultSchema() {
        TradeAgentProfile profile = new TradeAgentProfile();
        profile.setAgentCode("supervisor_agent");
        profile.setAgentName("Supervisor Agent");
        profile.setAgentType("HYBRID");
        profile.setLlmEnabled(Boolean.TRUE);
        profile.setStructuredSchemaCode("supervisor_decision_v1");
        profile.setDefaultModelId(21L);
        profile.setDefaultTemplateCode("trade.supervisor.v1");
        profile.setDefaultOutputSchemaCode("agent_view_v1");

        assertThatThrownBy(() -> tradeAgentProfileService.insertTradeAgentProfile(profile))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("defaultOutputSchemaCode");
    }

    @Test
    void insertTradeAgentProfileRejectsUnsupportedAgentCodeAndType() {
        TradeAgentProfile profile = new TradeAgentProfile();
        profile.setAgentCode("macro_agent");
        profile.setAgentName("News Agent");
        profile.setAgentType("AUTO");
        profile.setStructuredSchemaCode("agent_view_v1");

        assertThatThrownBy(() -> tradeAgentProfileService.insertTradeAgentProfile(profile))
            .isInstanceOf(ServiceException.class);
    }

    @Test
    void insertTradeAgentProfileRejectsDialogueRoundsOutsideBoundedDeliberationLimit() {
        TradeAgentProfile profile = new TradeAgentProfile();
        profile.setAgentCode("news_agent");
        profile.setAgentName("News Agent");
        profile.setAgentType("HYBRID");
        profile.setStructuredSchemaCode("agent_view_v1");
        profile.setDialogueEnabled(Boolean.TRUE);
        profile.setMaxDialogueRounds(3);

        assertThatThrownBy(() -> tradeAgentProfileService.insertTradeAgentProfile(profile))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("maxDialogueRounds");
    }

    private void mockEnabledModel(Long id) {
        AiModelConfig config = new AiModelConfig();
        config.setId(id);
        config.setIsEnabled(1);
        when(aiModelConfigService.selectAiModelConfigById(id)).thenReturn(config);
    }

    private void mockActiveTemplate(String code) {
        PromptTemplate template = new PromptTemplate();
        template.setCode(code);
        template.setIsActive(1);
        when(promptTemplateService.selectTemplateByCode(code)).thenReturn(template);
    }
}
