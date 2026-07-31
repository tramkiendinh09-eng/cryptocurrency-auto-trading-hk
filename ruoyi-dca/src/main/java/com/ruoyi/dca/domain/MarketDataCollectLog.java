package com.ruoyi.dca.domain;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;

import java.util.Date;

/**
 * 市场数据采集日志对象 market_data_collect_log
 *
 * @author ruoyi
 * @date 2026-04-05
 */
public class MarketDataCollectLog extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 日志ID */
    private Long id;

    /** 交易对 */
    @Excel(name = "交易对")
    private String symbol;

    /** 采集类型（SCHEDULED/MANUAL） */
    @Excel(name = "采集类型")
    private String collectType;

    /** 状态（0失败 1成功） */
    @Excel(name = "状态")
    private String status;

    /** 成功数量 */
    @Excel(name = "成功数量")
    private Integer successCount;

    /** 失败数量 */
    @Excel(name = "失败数量")
    private Integer failCount;

    /** 耗时（毫秒） */
    @Excel(name = "耗时")
    private Long durationMs;

    /** 错误信息 */
    private String errorMessage;

    /** 使用的数据源 */
    private String dataSourcesUsed;

    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setCollectType(String collectType) {
        this.collectType = collectType;
    }

    public String getCollectType() {
        return collectType;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getStatus() {
        return status;
    }

    public void setSuccessCount(Integer successCount) {
        this.successCount = successCount;
    }

    public Integer getSuccessCount() {
        return successCount;
    }

    public void setFailCount(Integer failCount) {
        this.failCount = failCount;
    }

    public Integer getFailCount() {
        return failCount;
    }

    public void setDurationMs(Long durationMs) {
        this.durationMs = durationMs;
    }

    public Long getDurationMs() {
        return durationMs;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public void setDataSourcesUsed(String dataSourcesUsed) {
        this.dataSourcesUsed = dataSourcesUsed;
    }

    public String getDataSourcesUsed() {
        return dataSourcesUsed;
    }
}
