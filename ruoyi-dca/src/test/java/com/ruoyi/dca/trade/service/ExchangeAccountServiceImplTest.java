package com.ruoyi.dca.trade.service;

import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.trade.ExchangeAccount;
import com.ruoyi.dca.mapper.trade.ExchangeAccountMapper;
import com.ruoyi.dca.service.trade.impl.ExchangeAccountServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.assertj.core.api.Assertions.assertThat;

@ExtendWith(MockitoExtension.class)
class ExchangeAccountServiceImplTest {

    @Mock
    private ExchangeAccountMapper exchangeAccountMapper;

    @InjectMocks
    private ExchangeAccountServiceImpl exchangeAccountService;

    @Test
    void insertExchangeAccountRejectsOkxAccountWithoutPassphrase() {
        ExchangeAccount account = new ExchangeAccount();
        account.setExchangeCode("okx");
        account.setAccountName("okx-primary");
        account.setApiKeyCiphertext("ak");
        account.setApiSecretCiphertext("sk");

        assertThatThrownBy(() -> exchangeAccountService.insertExchangeAccount(account))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("OKX passphrase");
    }

    @Test
    void insertExchangeAccountNormalizesBasicRuntimeFieldsBeforePersist() {
        ExchangeAccount account = new ExchangeAccount();
        account.setExchangeCode(" okx ");
        account.setAccountName(" primary ");
        account.setAccountKey(" okx-main ");
        account.setAccountRole(" execution ");
        account.setApiKeyCiphertext(" ak ");
        account.setApiSecretCiphertext(" sk ");
        account.setPassphraseCiphertext(" pass ");
        account.setApiBaseUrl(" https://www.okx.com ");
        account.setMarginMode(" ISOLATED ");
        account.setLeverageMode(" AUTO ");
        account.setPositionMode(" HEDGE ");
        account.setSettleCurrency(" usdt ");
        account.setHealthStatus(" HEALTHY ");
        account.setLastErrorMessage(" rate limit recovered ");
        when(exchangeAccountMapper.insertExchangeAccount(any(ExchangeAccount.class))).thenReturn(1);

        exchangeAccountService.insertExchangeAccount(account);

        ArgumentCaptor<ExchangeAccount> captor = ArgumentCaptor.forClass(ExchangeAccount.class);
        verify(exchangeAccountMapper).insertExchangeAccount(captor.capture());
        assertThat(captor.getValue().getExchangeCode()).isEqualTo("OKX");
        assertThat(captor.getValue().getAccountName()).isEqualTo("primary");
        assertThat(captor.getValue().getAccountKey()).isEqualTo("okx-main");
        assertThat(captor.getValue().getAccountRole()).isEqualTo("EXECUTION");
        assertThat(captor.getValue().getApiKeyCiphertext()).isEqualTo("ak");
        assertThat(captor.getValue().getApiSecretCiphertext()).isEqualTo("sk");
        assertThat(captor.getValue().getPassphraseCiphertext()).isEqualTo("pass");
        assertThat(captor.getValue().getApiBaseUrl()).isEqualTo("https://www.okx.com");
        assertThat(captor.getValue().getMarginMode()).isEqualTo("isolated");
        assertThat(captor.getValue().getLeverageMode()).isEqualTo("auto");
        assertThat(captor.getValue().getPositionMode()).isEqualTo("hedge");
        assertThat(captor.getValue().getSettleCurrency()).isEqualTo("USDT");
        assertThat(captor.getValue().getHealthStatus()).isEqualTo("healthy");
        assertThat(captor.getValue().getLastErrorMessage()).isEqualTo("rate limit recovered");
        assertThat(captor.getValue().getEnabled()).isTrue();
        assertThat(captor.getValue().getTestnet()).isFalse();
        assertThat(captor.getValue().getDemoTrading()).isFalse();
    }

    @Test
    void insertExchangeAccountAppliesRuntimeDefaultsForControlPlaneFields() {
        ExchangeAccount account = new ExchangeAccount();
        account.setExchangeCode("binance");
        account.setAccountName("primary");
        account.setApiKeyCiphertext("ak");
        account.setApiSecretCiphertext("sk");
        when(exchangeAccountMapper.insertExchangeAccount(any(ExchangeAccount.class))).thenReturn(1);

        exchangeAccountService.insertExchangeAccount(account);

        ArgumentCaptor<ExchangeAccount> captor = ArgumentCaptor.forClass(ExchangeAccount.class);
        verify(exchangeAccountMapper).insertExchangeAccount(captor.capture());
        assertThat(captor.getValue().getAccountRole()).isEqualTo("EXECUTION");
        assertThat(captor.getValue().getMarginMode()).isEqualTo("cross");
        assertThat(captor.getValue().getLeverageMode()).isEqualTo("manual");
        assertThat(captor.getValue().getPositionMode()).isEqualTo("one_way");
        assertThat(captor.getValue().getSettleCurrency()).isEqualTo("USDT");
        assertThat(captor.getValue().getHealthStatus()).isEqualTo("unknown");
    }

    @Test
    void insertExchangeAccountRejectsExchangesOutsideV1Whitelist() {
        ExchangeAccount account = new ExchangeAccount();
        account.setExchangeCode("bybit");
        account.setAccountName("bybit-primary");
        account.setApiKeyCiphertext("ak");
        account.setApiSecretCiphertext("sk");

        assertThatThrownBy(() -> exchangeAccountService.insertExchangeAccount(account))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("BINANCE")
            .hasMessageContaining("OKX");
    }
}
