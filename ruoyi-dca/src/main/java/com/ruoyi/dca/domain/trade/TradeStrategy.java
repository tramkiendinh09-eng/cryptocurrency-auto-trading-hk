package com.ruoyi.dca.domain.trade;

import com.ruoyi.dca.domain.enums.TradeRuntimeMode;

/**
 * 交易策略实体类
 *
 * 定义交易策略的基本信息和配置，包括策略键、名称、运行模式、
 * 交易品种、交易所等。
 *
 * @author ruoyi-dca
 */
public class TradeStrategy {
    /** 策略ID */
    private Long id;

    /** 策略键（唯一标识） */
    private String strategyKey;

    /** 策略名称 */
    private String strategyName;

    /** 运行模式：paper/shadow/live */
    private TradeRuntimeMode runtimeMode;

    /** 交易品种列表（JSON） */
    private String symbolsJson;

    /** 交易所列表（JSON） */
    private String exchangesJson;

    /** 策略配置（JSON） */
    private String configJson;

    /** 是否启用 */
    private Boolean enabled;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getStrategyKey() {
        return strategyKey;
    }

    public void setStrategyKey(String strategyKey) {
        this.strategyKey = strategyKey;
    }

    public String getStrategyName() {
        return strategyName;
    }

    public void setStrategyName(String strategyName) {
        this.strategyName = strategyName;
    }

    public TradeRuntimeMode getRuntimeMode() {
        return runtimeMode;
    }

    public void setRuntimeMode(TradeRuntimeMode runtimeMode) {
        this.runtimeMode = runtimeMode;
    }

    public String getSymbolsJson() {
        return symbolsJson;
    }

    public void setSymbolsJson(String symbolsJson) {
        this.symbolsJson = symbolsJson;
    }

    public String getExchangesJson() {
        return exchangesJson;
    }

    public void setExchangesJson(String exchangesJson) {
        this.exchangesJson = exchangesJson;
    }

    public String getConfigJson() {
        return configJson;
    }

    public void setConfigJson(String configJson) {
        this.configJson = configJson;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }
}
