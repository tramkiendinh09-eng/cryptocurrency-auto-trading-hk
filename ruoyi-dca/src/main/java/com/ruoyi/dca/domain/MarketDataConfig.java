package com.ruoyi.dca.domain;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;
import org.apache.commons.lang3.builder.ToStringBuilder;
import org.apache.commons.lang3.builder.ToStringStyle;

import java.util.Date;

/**
 * 市场数据采集配置对象 market_data_config
 *
 * @author ruoyi
 * @date 2026-04-05
 */
public class MarketDataConfig extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 配置ID */
    private Long id;

    /** 配置名称 */
    @Excel(name = "配置名称")
    private String configName;

    /** 交易对 */
    @Excel(name = "交易对")
    private String symbol;

    /** 是否启用 */
    @Excel(name = "是否启用")
    private String enabled;

    /** 采集间隔（秒） */
    @Excel(name = "采集间隔")
    private Integer collectInterval;

    /** 数据源列表 */
    private String dataSources;

    /** 是否采集K线数据 */
    private String collectKline;

    /** K线周期 */
    private String klinePeriods;

    /** 是否采集恐慌贪婪指数 */
    private String collectFearGreed;

    /** 是否采集链上数据 */
    private String collectOnchain;

    /** API密钥配置 */
    private String apiKeyConfig;

    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
    }

    public void setConfigName(String configName) {
        this.configName = configName;
    }

    public String getConfigName() {
        return configName;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getSymbol() {
        return symbol;
    }

    public String getEnabled() {
        return enabled;
    }

    public void setEnabled(String enabled) {
        this.enabled = enabled;
    }

    public Integer getCollectInterval() {
        return collectInterval;
    }

    public void setCollectInterval(Integer collectInterval) {
        this.collectInterval = collectInterval;
    }

    public String getDataSources() {
        return dataSources;
    }

    public void setDataSources(String dataSources) {
        this.dataSources = dataSources;
    }

    public String getCollectKline() {
        return collectKline;
    }

    public void setCollectKline(String collectKline) {
        this.collectKline = collectKline;
    }

    public String getKlinePeriods() {
        return klinePeriods;
    }

    public void setKlinePeriods(String klinePeriods) {
        this.klinePeriods = klinePeriods;
    }

    public String getCollectFearGreed() {
        return collectFearGreed;
    }

    public void setCollectFearGreed(String collectFearGreed) {
        this.collectFearGreed = collectFearGreed;
    }

    public String getCollectOnchain() {
        return collectOnchain;
    }

    public void setCollectOnchain(String collectOnchain) {
        this.collectOnchain = collectOnchain;
    }

    public String getApiKeyConfig() {
        return apiKeyConfig;
    }

    public void setApiKeyConfig(String apiKeyConfig) {
        this.apiKeyConfig = apiKeyConfig;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this, ToStringStyle.MULTI_LINE_STYLE)
                .append("id", getId())
                .append("configName", getConfigName())
                .append("symbol", getSymbol())
                .append("enabled", getEnabled())
                .append("collectInterval", getCollectInterval())
                .append("dataSources", getDataSources())
                .append("collectKline", getCollectKline())
                .append("klinePeriods", getKlinePeriods())
                .append("collectFearGreed", getCollectFearGreed())
                .append("collectOnchain", getCollectOnchain())
                .append("remark", getRemark())
                .append("createBy", getCreateBy())
                .append("createTime", getCreateTime())
                .append("updateBy", getUpdateBy())
                .append("updateTime", getUpdateTime())
                .toString();
    }
}
