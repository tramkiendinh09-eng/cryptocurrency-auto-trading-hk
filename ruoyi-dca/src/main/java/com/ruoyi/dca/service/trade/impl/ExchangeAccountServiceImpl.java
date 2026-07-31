package com.ruoyi.dca.service.trade.impl;

import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.constants.TradeConstants;
import com.ruoyi.dca.domain.trade.ExchangeAccount;
import com.ruoyi.dca.mapper.trade.ExchangeAccountMapper;
import com.ruoyi.dca.service.trade.IExchangeAccountService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Locale;
import java.util.Set;

@Service
public class ExchangeAccountServiceImpl implements IExchangeAccountService {

    @Autowired
    private ExchangeAccountMapper exchangeAccountMapper;

    @Override
    public List<ExchangeAccount> selectExchangeAccountList(ExchangeAccount query) {
        return exchangeAccountMapper.selectExchangeAccountList(query);
    }

    @Override
    public int insertExchangeAccount(ExchangeAccount exchangeAccount) {
        normalizeAndValidate(exchangeAccount);
        return exchangeAccountMapper.insertExchangeAccount(exchangeAccount);
    }

    @Override
    public int updateExchangeAccount(ExchangeAccount exchangeAccount) {
        normalizeAndValidate(exchangeAccount);
        return exchangeAccountMapper.updateExchangeAccount(exchangeAccount);
    }

    @Override
    public int deleteExchangeAccountByIds(Long[] ids) {
        if (ids == null || ids.length == 0) {
            return 0;
        }
        return exchangeAccountMapper.deleteExchangeAccountByIds(ids);
    }

    private void normalizeAndValidate(ExchangeAccount exchangeAccount) {
        if (exchangeAccount == null) {
            throw new ServiceException("Exchange account payload is required");
        }
        exchangeAccount.setExchangeCode(normalizeExchangeCode(exchangeAccount.getExchangeCode()));
        exchangeAccount.setAccountName(trimToEmpty(exchangeAccount.getAccountName()));
        exchangeAccount.setAccountKey(trimToEmpty(exchangeAccount.getAccountKey()));
        exchangeAccount.setAccountRole(defaultIfBlank(normalizeUpper(exchangeAccount.getAccountRole()), "EXECUTION"));
        exchangeAccount.setApiKeyCiphertext(trimToEmpty(exchangeAccount.getApiKeyCiphertext()));
        exchangeAccount.setApiSecretCiphertext(trimToEmpty(exchangeAccount.getApiSecretCiphertext()));
        exchangeAccount.setPassphraseCiphertext(trimToEmpty(exchangeAccount.getPassphraseCiphertext()));
        exchangeAccount.setApiBaseUrl(trimToEmpty(exchangeAccount.getApiBaseUrl()));
        exchangeAccount.setMarginMode(defaultIfBlank(normalizeLower(exchangeAccount.getMarginMode()), "cross"));
        exchangeAccount.setLeverageMode(defaultIfBlank(normalizeLower(exchangeAccount.getLeverageMode()), "manual"));
        exchangeAccount.setPositionMode(defaultIfBlank(normalizeLower(exchangeAccount.getPositionMode()), "one_way"));
        exchangeAccount.setSettleCurrency(defaultIfBlank(normalizeUpper(exchangeAccount.getSettleCurrency()), "USDT"));
        exchangeAccount.setHealthStatus(defaultIfBlank(normalizeLower(exchangeAccount.getHealthStatus()), "unknown"));
        exchangeAccount.setLastErrorMessage(trimToEmpty(exchangeAccount.getLastErrorMessage()));
        if (exchangeAccount.getEnabled() == null) {
            exchangeAccount.setEnabled(Boolean.TRUE);
        }
        if (exchangeAccount.getTestnet() == null) {
            exchangeAccount.setTestnet(Boolean.FALSE);
        }
        if (exchangeAccount.getDemoTrading() == null) {
            exchangeAccount.setDemoTrading(Boolean.FALSE);
        }
        if (exchangeAccount.getExchangeCode().isEmpty()) {
            throw new ServiceException("Exchange code is required");
        }
        if (!TradeConstants.V1_ALLOWED_EXCHANGES.contains(exchangeAccount.getExchangeCode())) {
            throw new ServiceException("Only BINANCE and OKX are supported in V1");
        }
        if (exchangeAccount.getAccountName().isEmpty()) {
            throw new ServiceException("Account name is required");
        }
        if (exchangeAccount.getApiKeyCiphertext().isEmpty()) {
            throw new ServiceException("API key is required");
        }
        if (exchangeAccount.getApiSecretCiphertext().isEmpty()) {
            throw new ServiceException("API secret is required");
        }
        if (TradeConstants.EXCHANGE_OKX.equals(exchangeAccount.getExchangeCode()) && exchangeAccount.getPassphraseCiphertext().isEmpty()) {
            throw new ServiceException("OKX passphrase is required");
        }
    }

    private String normalizeExchangeCode(String exchangeCode) {
        return trimToEmpty(exchangeCode).toUpperCase();
    }

    private String normalizeUpper(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? "" : trimmed.toUpperCase(Locale.ROOT);
    }

    private String normalizeLower(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? "" : trimmed.toLowerCase(Locale.ROOT);
    }

    private String defaultIfBlank(String value, String defaultValue) {
        return value == null || value.isEmpty() ? defaultValue : value;
    }

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }
}
