package com.ruoyi.dca.domain.trade;

import com.fasterxml.jackson.annotation.JsonFormat;

import java.util.Date;

/**
 * 交易所账户实体类
 *
 * 存储交易所账户的配置信息，包括API密钥、保证金模式、仓位模式等。
 * API密钥以密文形式存储，确保安全性。
 *
 * @author ruoyi-dca
 */
public class ExchangeAccount {
    /** 账户ID */
    private Long id;

    /** 交易所代码：BINANCE/OKX */
    private String exchangeCode;

    /** 账户名称 */
    private String accountName;

    /** 账户键（唯一标识） */
    private String accountKey;

    /** 账户角色：main/sub */
    private String accountRole;

    /** API Key密文 */
    private String apiKeyCiphertext;

    /** API Secret密文 */
    private String apiSecretCiphertext;

    /** Passphrase密文（OKX） */
    private String passphraseCiphertext;

    /** API基础URL */
    private String apiBaseUrl;

    /** 是否测试网 */
    private Boolean testnet;

    /** 是否演示交易（OKX） */
    private Boolean demoTrading;

    /** 保证金模式：cross/isolated */
    private String marginMode;

    /** 杠杆模式 */
    private String leverageMode;

    /** 仓位模式：long_short_mode/net_mode */
    private String positionMode;

    /** 结算货币 */
    private String settleCurrency;

    /** 是否启用 */
    private Boolean enabled;

    /** 健康状态：healthy/unhealthy */
    private String healthStatus;

    /** 最后验证时间 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date lastValidatedAt;

    /** 最后错误信息 */
    private String lastErrorMessage;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getExchangeCode() {
        return exchangeCode;
    }

    public void setExchangeCode(String exchangeCode) {
        this.exchangeCode = exchangeCode;
    }

    public String getAccountName() {
        return accountName;
    }

    public void setAccountName(String accountName) {
        this.accountName = accountName;
    }

    public String getAccountKey() {
        return accountKey;
    }

    public void setAccountKey(String accountKey) {
        this.accountKey = accountKey;
    }

    public String getAccountRole() {
        return accountRole;
    }

    public void setAccountRole(String accountRole) {
        this.accountRole = accountRole;
    }

    public String getApiKeyCiphertext() {
        return apiKeyCiphertext;
    }

    public void setApiKeyCiphertext(String apiKeyCiphertext) {
        this.apiKeyCiphertext = apiKeyCiphertext;
    }

    public String getApiSecretCiphertext() {
        return apiSecretCiphertext;
    }

    public void setApiSecretCiphertext(String apiSecretCiphertext) {
        this.apiSecretCiphertext = apiSecretCiphertext;
    }

    public String getPassphraseCiphertext() {
        return passphraseCiphertext;
    }

    public void setPassphraseCiphertext(String passphraseCiphertext) {
        this.passphraseCiphertext = passphraseCiphertext;
    }

    public String getApiBaseUrl() {
        return apiBaseUrl;
    }

    public void setApiBaseUrl(String apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
    }

    public Boolean getTestnet() {
        return testnet;
    }

    public void setTestnet(Boolean testnet) {
        this.testnet = testnet;
    }

    public Boolean getDemoTrading() {
        return demoTrading;
    }

    public void setDemoTrading(Boolean demoTrading) {
        this.demoTrading = demoTrading;
    }

    public String getMarginMode() {
        return marginMode;
    }

    public void setMarginMode(String marginMode) {
        this.marginMode = marginMode;
    }

    public String getLeverageMode() {
        return leverageMode;
    }

    public void setLeverageMode(String leverageMode) {
        this.leverageMode = leverageMode;
    }

    public String getPositionMode() {
        return positionMode;
    }

    public void setPositionMode(String positionMode) {
        this.positionMode = positionMode;
    }

    public String getSettleCurrency() {
        return settleCurrency;
    }

    public void setSettleCurrency(String settleCurrency) {
        this.settleCurrency = settleCurrency;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

    public String getHealthStatus() {
        return healthStatus;
    }

    public void setHealthStatus(String healthStatus) {
        this.healthStatus = healthStatus;
    }

    public Date getLastValidatedAt() {
        return lastValidatedAt;
    }

    public void setLastValidatedAt(Date lastValidatedAt) {
        this.lastValidatedAt = lastValidatedAt;
    }

    public String getLastErrorMessage() {
        return lastErrorMessage;
    }

    public void setLastErrorMessage(String lastErrorMessage) {
        this.lastErrorMessage = lastErrorMessage;
    }
}
