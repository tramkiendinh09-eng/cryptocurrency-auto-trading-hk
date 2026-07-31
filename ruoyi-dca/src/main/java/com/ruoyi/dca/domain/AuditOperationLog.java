package com.ruoyi.dca.domain;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;
import org.apache.commons.lang3.builder.ToStringBuilder;
import org.apache.commons.lang3.builder.ToStringStyle;
import java.util.Date;

/**
 * 操作审计日志对象 audit_operation_log
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class AuditOperationLog extends BaseEntity {
    private static final long serialVersionUID = 1L;

    /** 主键ID */
    private Long id;

    /** 用户ID */
    @Excel(name = "用户ID")
    private Long userId;

    /** 用户名 */
    @Excel(name = "用户名")
    private String username;

    /** 操作模块: strategy/config/cardkey/notify/system */
    @Excel(name = "操作模块")
    private String module;

    /** 操作类型: create/update/delete/import/export */
    @Excel(name = "操作类型")
    private String operation;

    /** 操作描述 */
    @Excel(name = "操作描述")
    private String description;

    /** 请求方法 */
    private String requestMethod;

    /** 请求URL */
    private String requestUrl;

    /** 请求IP */
    @Excel(name = "请求IP")
    private String requestIp;

    /** 请求参数 */
    private String requestParams;

    /** 返回结果 */
    private String responseData;

    /** 操作状态: 0失败 1成功 */
    @Excel(name = "操作状态")
    private Integer status;

    /** 错误信息 */
    private String errorMsg;

    /** 执行时间(ms) */
    @Excel(name = "执行时间")
    private Long executionTime;

    /** 操作时间 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @Excel(name = "操作时间", dateFormat = "yyyy-MM-dd HH:mm:ss")
    private Date operationTime;

    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getUsername() {
        return username;
    }

    public void setModule(String module) {
        this.module = module;
    }

    public String getModule() {
        return module;
    }

    public void setOperation(String operation) {
        this.operation = operation;
    }

    public String getOperation() {
        return operation;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }

    public void setRequestMethod(String requestMethod) {
        this.requestMethod = requestMethod;
    }

    public String getRequestMethod() {
        return requestMethod;
    }

    public void setRequestUrl(String requestUrl) {
        this.requestUrl = requestUrl;
    }

    public String getRequestUrl() {
        return requestUrl;
    }

    public void setRequestIp(String requestIp) {
        this.requestIp = requestIp;
    }

    public String getRequestIp() {
        return requestIp;
    }

    public void setRequestParams(String requestParams) {
        this.requestParams = requestParams;
    }

    public String getRequestParams() {
        return requestParams;
    }

    public void setResponseData(String responseData) {
        this.responseData = responseData;
    }

    public String getResponseData() {
        return responseData;
    }

    public void setStatus(Integer status) {
        this.status = status;
    }

    public Integer getStatus() {
        return status;
    }

    public void setErrorMsg(String errorMsg) {
        this.errorMsg = errorMsg;
    }

    public String getErrorMsg() {
        return errorMsg;
    }

    public void setExecutionTime(Long executionTime) {
        this.executionTime = executionTime;
    }

    public Long getExecutionTime() {
        return executionTime;
    }

    public void setOperationTime(Date operationTime) {
        this.operationTime = operationTime;
    }

    public Date getOperationTime() {
        return operationTime;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this, ToStringStyle.MULTI_LINE_STYLE)
            .append("id", getId())
            .append("userId", getUserId())
            .append("username", getUsername())
            .append("module", getModule())
            .append("operation", getOperation())
            .append("description", getDescription())
            .append("requestMethod", getRequestMethod())
            .append("requestUrl", getRequestUrl())
            .append("requestIp", getRequestIp())
            .append("requestParams", getRequestParams())
            .append("responseData", getResponseData())
            .append("status", getStatus())
            .append("errorMsg", getErrorMsg())
            .append("executionTime", getExecutionTime())
            .append("operationTime", getOperationTime())
            .append("remark", getRemark())
            .append("createBy", getCreateBy())
            .append("createTime", getCreateTime())
            .append("updateBy", getUpdateBy())
            .append("updateTime", getUpdateTime())
            .toString();
    }
}
