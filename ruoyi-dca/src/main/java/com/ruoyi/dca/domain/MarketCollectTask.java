package com.ruoyi.dca.domain;

import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;

/**
 * 数据采集任务对象 market_collect_task
 *
 * @author ruoyi
 * @date 2026-04-05
 */
public class MarketCollectTask extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 任务ID */
    private Long id;

    /** 任务名称 */
    @Excel(name = "任务名称")
    private String taskName;

    /** 交易对 */
    @Excel(name = "交易对")
    private String symbol;

    /** 采集价格 */
    private String collectPrice;

    /** 采集成交量 */
    private String collectVolume;

    /** 采集1小时K线 */
    private String collectKline1h;

    /** 采集4小时K线 */
    private String collectKline4h;

    /** 采集日K线 */
    private String collectKline1d;

    /** 采集恐慌指数 */
    private String collectFearGreed;

    /** 采集链上数据 */
    private String collectOnchain;

    /** 采集Gas价格 */
    private String collectGas;

    /** 价格API配置ID */
    private Long priceApiId;

    /** 成交量API配置ID */
    private Long volumeApiId;

    /** K线API配置ID */
    private Long klineApiId;

    /** 链上API配置ID */
    private Long onchainApiId;

    /** Gas API配置ID */
    private Long gasApiId;

    /** 采集间隔 */
    @Excel(name = "采集间隔(秒)")
    private Integer collectInterval;

    /** 是否启用 */
    @Excel(name = "启用状态")
    private String enabled;

    /** 备注 */
    @Excel(name = "备注")
    private String remark;

    // Getter and Setter methods
    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
    }

    public void setTaskName(String taskName) {
        this.taskName = taskName;
    }

    public String getTaskName() {
        return taskName;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setCollectPrice(String collectPrice) {
        this.collectPrice = collectPrice;
    }

    public String getCollectPrice() {
        return collectPrice;
    }

    public void setCollectVolume(String collectVolume) {
        this.collectVolume = collectVolume;
    }

    public String getCollectVolume() {
        return collectVolume;
    }

    public void setCollectKline1h(String collectKline1h) {
        this.collectKline1h = collectKline1h;
    }

    public String getCollectKline1h() {
        return collectKline1h;
    }

    public void setCollectKline4h(String collectKline4h) {
        this.collectKline4h = collectKline4h;
    }

    public String getCollectKline4h() {
        return collectKline4h;
    }

    public void setCollectKline1d(String collectKline1d) {
        this.collectKline1d = collectKline1d;
    }

    public String getCollectKline1d() {
        return collectKline1d;
    }

    public void setCollectFearGreed(String collectFearGreed) {
        this.collectFearGreed = collectFearGreed;
    }

    public String getCollectFearGreed() {
        return collectFearGreed;
    }

    public void setCollectOnchain(String collectOnchain) {
        this.collectOnchain = collectOnchain;
    }

    public String getCollectOnchain() {
        return collectOnchain;
    }

    public void setCollectGas(String collectGas) {
        this.collectGas = collectGas;
    }

    public String getCollectGas() {
        return collectGas;
    }

    public void setPriceApiId(Long priceApiId) {
        this.priceApiId = priceApiId;
    }

    public Long getPriceApiId() {
        return priceApiId;
    }

    public void setVolumeApiId(Long volumeApiId) {
        this.volumeApiId = volumeApiId;
    }

    public Long getVolumeApiId() {
        return volumeApiId;
    }

    public void setKlineApiId(Long klineApiId) {
        this.klineApiId = klineApiId;
    }

    public Long getKlineApiId() {
        return klineApiId;
    }

    public void setOnchainApiId(Long onchainApiId) {
        this.onchainApiId = onchainApiId;
    }

    public Long getOnchainApiId() {
        return onchainApiId;
    }

    public void setGasApiId(Long gasApiId) {
        this.gasApiId = gasApiId;
    }

    public Long getGasApiId() {
        return gasApiId;
    }

    public void setCollectInterval(Integer collectInterval) {
        this.collectInterval = collectInterval;
    }

    public Integer getCollectInterval() {
        return collectInterval;
    }

    public void setEnabled(String enabled) {
        this.enabled = enabled;
    }

    public String getEnabled() {
        return enabled;
    }

    public void setRemark(String remark) {
        this.remark = remark;
    }

    public String getRemark() {
        return remark;
    }
}
