package com.ruoyi.dca.trade.controller;

import com.ruoyi.dca.controller.trade.ExchangeAccountController;
import com.ruoyi.dca.domain.trade.ExchangeAccount;
import com.ruoyi.dca.service.trade.IExchangeAccountService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Collections;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ExchangeAccountController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {ExchangeAccountControllerTest.TestApplication.class, ExchangeAccountController.class})
class ExchangeAccountControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private IExchangeAccountService exchangeAccountService;

    @Test
    void listAccountsReturnsExchangeRows() throws Exception {
        ExchangeAccount account = new ExchangeAccount();
        account.setId(1L);
        account.setExchangeCode("binance");
        account.setAccountName("Primary");
        account.setEnabled(Boolean.TRUE);

        when(exchangeAccountService.selectExchangeAccountList(any(ExchangeAccount.class)))
            .thenReturn(Collections.singletonList(account));

        mockMvc.perform(get("/dca/trade/account/list"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows").isArray())
            .andExpect(jsonPath("$.rows[0].exchangeCode").value("binance"))
            .andExpect(jsonPath("$.rows[0].accountName").value("Primary"))
            .andExpect(jsonPath("$.rows[0].enabled").value(true))
            .andExpect(jsonPath("$.total").value(1));
    }

    @Test
    void createAccountAcceptsWritablePayload() throws Exception {
        when(exchangeAccountService.insertExchangeAccount(any(ExchangeAccount.class))).thenReturn(1);

        mockMvc.perform(post("/dca/trade/account")
                .contentType(APPLICATION_JSON)
                .content("""
                    {"exchangeCode":"binance","accountName":"Primary","apiKeyCiphertext":"ak","apiSecretCiphertext":"sk","enabled":true}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void updateAccountAcceptsWritablePayload() throws Exception {
        when(exchangeAccountService.updateExchangeAccount(any(ExchangeAccount.class))).thenReturn(1);

        mockMvc.perform(put("/dca/trade/account")
                .contentType(APPLICATION_JSON)
                .content("""
                    {"id":3,"exchangeCode":"okx","accountName":"Backup","apiKeyCiphertext":"ak2","apiSecretCiphertext":"sk2","enabled":false}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void deleteAccountAcceptsIds() throws Exception {
        when(exchangeAccountService.deleteExchangeAccountByIds(any(Long[].class))).thenReturn(1);

        mockMvc.perform(delete("/dca/trade/account/3"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }
}
