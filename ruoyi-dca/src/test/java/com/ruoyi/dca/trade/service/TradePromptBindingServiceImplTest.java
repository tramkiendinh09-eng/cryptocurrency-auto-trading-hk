package com.ruoyi.dca.trade.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.domain.PromptTemplate;
import com.ruoyi.dca.domain.trade.TradePromptBinding;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.domain.trade.TradeStrategyVersion;
import com.ruoyi.dca.mapper.trade.TradePromptBindingMapper;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.IAiModelConfigService;
import com.ruoyi.dca.service.IPromptTemplateService;
import com.ruoyi.dca.service.trade.impl.TradePromptBindingServiceImpl;
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
class TradePromptBindingServiceImplTest {

    @Mock
    private TradePromptBindingMapper tradePromptBindingMapper;

    @Mock
    private TradeStrategyMapper tradeStrategyMapper;

    @Mock
    private IPromptTemplateService promptTemplateService;

    @Mock
    private IAiModelConfigService aiModelConfigService;

    @Spy
    private ObjectMapper objectMapper;

    @InjectMocks
    private TradePromptBindingServiceImpl tradePromptBindingService;

    @Test
    void insertTradePromptBindingNormalizesScopesAgainstSpecsWhitelist() {
        TradePromptBinding binding = new TradePromptBinding();
        binding.setBindingName(" Supervisor Prompt ");
        binding.setStrategyId(7L);
        binding.setStrategyVersionId(12L);
        binding.setSymbol(" btcusdt ");
        binding.setExchangeCode(" binance ");
        binding.setBindingScope(" supervisor ");
        binding.setTemplateCode(" trade.supervisor.v1 ");
        binding.setFallbackTemplateCode(" trade.supervisor.fallback ");
        binding.setModelId(21L);
        binding.setOutputSchemaCode(" supervisor_decision_v1 ");
        binding.setModeScopeJson("[\" shadow \",\"LIVE\"]");
        binding.setEventStrengthScopeJson("[\" strong \",\"NORMAL\"]");

        mockStrategyReference(7L, 12L);
        mockActiveTemplate("trade.supervisor.v1");
        mockActiveTemplate("trade.supervisor.fallback");
        mockEnabledModel(21L);
        when(tradePromptBindingMapper.selectTradePromptBindingList(any(TradePromptBinding.class))).thenReturn(List.of());
        when(tradePromptBindingMapper.insertTradePromptBinding(any(TradePromptBinding.class))).thenReturn(1);

        tradePromptBindingService.insertTradePromptBinding(binding);

        ArgumentCaptor<TradePromptBinding> captor = ArgumentCaptor.forClass(TradePromptBinding.class);
        verify(tradePromptBindingMapper).insertTradePromptBinding(captor.capture());
        TradePromptBinding saved = captor.getValue();
        assertThat(saved.getBindingName()).isEqualTo("Supervisor Prompt");
        assertThat(saved.getSymbol()).isEqualTo("BTCUSDT");
        assertThat(saved.getExchangeCode()).isEqualTo("BINANCE");
        assertThat(saved.getBindingScope()).isEqualTo("SUPERVISOR");
        assertThat(saved.getTemplateCode()).isEqualTo("trade.supervisor.v1");
        assertThat(saved.getFallbackTemplateCode()).isEqualTo("trade.supervisor.fallback");
        assertThat(saved.getOutputSchemaCode()).isEqualTo("supervisor_decision_v1");
        assertThat(saved.getPriority()).isEqualTo(100);
        assertThat(saved.getEnabled()).isTrue();
        assertThat(saved.getModeScopeJson()).isEqualTo("[\"shadow\",\"live\"]");
        assertThat(saved.getEventStrengthScopeJson()).isEqualTo("[\"strong\",\"normal\"]");
    }

    @Test
    void insertTradePromptBindingAllowsModelOnlyOverrideWithoutTemplateOrSchema() {
        TradePromptBinding binding = new TradePromptBinding();
        binding.setBindingName("Market Model Override");
        binding.setBindingScope("market_agent");
        binding.setModelId(21L);

        mockEnabledModel(21L);
        when(tradePromptBindingMapper.selectTradePromptBindingList(any(TradePromptBinding.class))).thenReturn(List.of());
        when(tradePromptBindingMapper.insertTradePromptBinding(any(TradePromptBinding.class))).thenReturn(1);

        tradePromptBindingService.insertTradePromptBinding(binding);

        ArgumentCaptor<TradePromptBinding> captor = ArgumentCaptor.forClass(TradePromptBinding.class);
        verify(tradePromptBindingMapper).insertTradePromptBinding(captor.capture());
        TradePromptBinding saved = captor.getValue();
        assertThat(saved.getBindingScope()).isEqualTo("MARKET_AGENT");
        assertThat(saved.getTemplateCode()).isNull();
        assertThat(saved.getOutputSchemaCode()).isNull();
        assertThat(saved.getModelId()).isEqualTo(21L);
    }

    @Test
    void insertTradePromptBindingRejectsUnsupportedScopeSymbolAndEventStrength() {
        TradePromptBinding binding = new TradePromptBinding();
        binding.setBindingName("Bad Binding");
        binding.setBindingScope("random_agent");
        binding.setTemplateCode("trade.supervisor.v1");
        binding.setOutputSchemaCode("supervisor_decision_v1");
        binding.setSymbol("XRPUSDT");
        binding.setEventStrengthScopeJson("[\"critical\"]");

        assertThatThrownBy(() -> tradePromptBindingService.insertTradePromptBinding(binding))
            .isInstanceOf(ServiceException.class);
    }

    @Test
    void insertTradePromptBindingRejectsStrategyVersionOutsideStrategy() {
        TradePromptBinding binding = new TradePromptBinding();
        binding.setBindingName("Supervisor Prompt");
        binding.setStrategyId(7L);
        binding.setStrategyVersionId(13L);
        binding.setBindingScope("SUPERVISOR");
        binding.setTemplateCode("trade.supervisor.v1");
        binding.setOutputSchemaCode("supervisor_decision_v1");

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(7L);
        when(tradeStrategyMapper.selectTradeStrategyById(7L)).thenReturn(strategy);
        when(tradeStrategyMapper.selectTradeStrategyVersions(7L)).thenReturn(List.of());

        assertThatThrownBy(() -> tradePromptBindingService.insertTradePromptBinding(binding))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("version");
    }

    @Test
    void insertTradePromptBindingRejectsDuplicateEnabledBindingWithinSameScope() {
        TradePromptBinding binding = new TradePromptBinding();
        binding.setBindingName("Supervisor Prompt");
        binding.setStrategyId(7L);
        binding.setStrategyVersionId(12L);
        binding.setSymbol("BTCUSDT");
        binding.setExchangeCode("BINANCE");
        binding.setBindingScope("SUPERVISOR");
        binding.setTemplateCode("trade.supervisor.v1");
        binding.setOutputSchemaCode("supervisor_decision_v1");
        binding.setModeScopeJson("[\"shadow\"]");
        binding.setEventStrengthScopeJson("[\"strong\"]");

        mockStrategyReference(7L, 12L);
        mockActiveTemplate("trade.supervisor.v1");

        TradePromptBinding existing = new TradePromptBinding();
        existing.setId(99L);
        existing.setStrategyId(7L);
        existing.setStrategyVersionId(12L);
        existing.setSymbol("BTCUSDT");
        existing.setExchangeCode("BINANCE");
        existing.setBindingScope("SUPERVISOR");
        existing.setEnabled(Boolean.TRUE);
        existing.setModeScopeJson("[\"shadow\"]");
        existing.setEventStrengthScopeJson("[\"strong\"]");
        when(tradePromptBindingMapper.selectTradePromptBindingList(any(TradePromptBinding.class))).thenReturn(List.of(existing));

        assertThatThrownBy(() -> tradePromptBindingService.insertTradePromptBinding(binding))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("Duplicate");
    }

    @Test
    void insertTradePromptBindingRejectsSupervisorBindingWithWrongSchema() {
        TradePromptBinding binding = new TradePromptBinding();
        binding.setBindingName("Supervisor Prompt");
        binding.setBindingScope("SUPERVISOR");
        binding.setTemplateCode("trade.supervisor.v1");
        binding.setOutputSchemaCode("agent_view_v1");

        mockActiveTemplate("trade.supervisor.v1");

        assertThatThrownBy(() -> tradePromptBindingService.insertTradePromptBinding(binding))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("outputSchemaCode");
    }

    @Test
    void updateTradePromptBindingPreservesExistingScopeFieldsWhenPayloadIsPartial() {
        TradePromptBinding existing = new TradePromptBinding();
        existing.setId(8L);
        existing.setBindingName("Existing Supervisor");
        existing.setStrategyId(7L);
        existing.setStrategyVersionId(12L);
        existing.setSymbol("BTCUSDT");
        existing.setExchangeCode("BINANCE");
        existing.setBindingScope("SUPERVISOR");
        existing.setTemplateCode("trade.supervisor.v1");
        existing.setFallbackTemplateCode("trade.supervisor.fallback");
        existing.setModelId(21L);
        existing.setOutputSchemaCode("supervisor_decision_v1");
        existing.setPriority(100);
        existing.setModeScopeJson("[\"shadow\"]");
        existing.setEventStrengthScopeJson("[\"strong\"]");
        existing.setEnabled(Boolean.TRUE);

        TradePromptBinding patch = new TradePromptBinding();
        patch.setId(8L);
        patch.setBindingName("Updated Supervisor");
        patch.setTemplateCode("trade.supervisor.v2");
        patch.setOutputSchemaCode("supervisor_decision_v1");

        when(tradePromptBindingMapper.selectTradePromptBindingById(8L)).thenReturn(existing);
        when(tradePromptBindingMapper.selectTradePromptBindingList(any(TradePromptBinding.class))).thenReturn(List.of(existing));
        mockStrategyReference(7L, 12L);
        mockActiveTemplate("trade.supervisor.v2");
        mockActiveTemplate("trade.supervisor.fallback");
        mockEnabledModel(21L);
        when(tradePromptBindingMapper.updateTradePromptBinding(any(TradePromptBinding.class))).thenReturn(1);

        tradePromptBindingService.updateTradePromptBinding(patch);

        ArgumentCaptor<TradePromptBinding> captor = ArgumentCaptor.forClass(TradePromptBinding.class);
        verify(tradePromptBindingMapper).updateTradePromptBinding(captor.capture());
        TradePromptBinding saved = captor.getValue();
        assertThat(saved.getStrategyId()).isEqualTo(7L);
        assertThat(saved.getStrategyVersionId()).isEqualTo(12L);
        assertThat(saved.getSymbol()).isEqualTo("BTCUSDT");
        assertThat(saved.getExchangeCode()).isEqualTo("BINANCE");
        assertThat(saved.getFallbackTemplateCode()).isEqualTo("trade.supervisor.fallback");
        assertThat(saved.getModelId()).isEqualTo(21L);
        assertThat(saved.getTemplateCode()).isEqualTo("trade.supervisor.v2");
    }

    private void mockStrategyReference(Long strategyId, Long versionId) {
        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(strategyId);
        when(tradeStrategyMapper.selectTradeStrategyById(strategyId)).thenReturn(strategy);

        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setId(versionId);
        version.setStrategyId(strategyId);
        when(tradeStrategyMapper.selectTradeStrategyVersions(strategyId)).thenReturn(List.of(version));
    }

    private void mockActiveTemplate(String code) {
        PromptTemplate template = new PromptTemplate();
        template.setCode(code);
        template.setIsActive(1);
        when(promptTemplateService.selectTemplateByCode(code)).thenReturn(template);
    }

    private void mockEnabledModel(Long id) {
        AiModelConfig config = new AiModelConfig();
        config.setId(id);
        config.setIsEnabled(1);
        when(aiModelConfigService.selectAiModelConfigById(id)).thenReturn(config);
    }
}
