package com.ruoyi.dca.domain;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;
import org.apache.commons.lang3.builder.ToStringBuilder;
import org.apache.commons.lang3.builder.ToStringStyle;
import java.util.Date;

/**
 * Python Worker状态对象 python_worker_status
 *
 * @author ruoyi
 * @date 2026-04-03
 */
public class PythonWorkerStatus extends BaseEntity {
    private static final long serialVersionUID = 1L;

    /** 主键ID */
    private Long id;

    /** Worker ID */
    @Excel(name = "Worker ID")
    private String workerId;

    /** Worker类型: general/collector/ai/notify */
    @Excel(name = "Worker类型")
    private String workerType;

    /** 关联的用户ID(用户隔离模式) */
    @Excel(name = "用户ID")
    private Long userId;

    /** 状态: online/offline/busy/error */
    @Excel(name = "状态")
    private String status;

    /** 进程ID */
    @Excel(name = "进程ID")
    private Integer pid;

    /** 主机 */
    @Excel(name = "主机")
    private String host;

    /** 端口 */
    @Excel(name = "端口")
    private Integer port;

    /** 最后心跳时间 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @Excel(name = "最后心跳", dateFormat = "yyyy-MM-dd HH:mm:ss")
    private Date lastHeartbeat;

    /** 最后任务时间 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @Excel(name = "最后任务时间", dateFormat = "yyyy-MM-dd HH:mm:ss")
    private Date lastTaskTime;

    /** 总任务数 */
    @Excel(name = "总任务数")
    private Integer totalTasks;

    /** 成功任务数 */
    @Excel(name = "成功任务数")
    private Integer successTasks;

    /** 失败任务数 */
    @Excel(name = "失败任务数")
    private Integer failedTasks;

    /** Worker配置 JSON */
    private String workerConfig;

    /** 启动时间 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @Excel(name = "启动时间", dateFormat = "yyyy-MM-dd HH:mm:ss")
    private Date startTime;

    /** 创建时间 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @Excel(name = "创建时间", dateFormat = "yyyy-MM-dd HH:mm:ss")
    private Date createTime;

    /** 更新时间 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @Excel(name = "更新时间", dateFormat = "yyyy-MM-dd HH:mm:ss")
    private Date updateTime;

    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
    }

    public void setWorkerId(String workerId) {
        this.workerId = workerId;
    }

    public String getWorkerId() {
        return workerId;
    }

    public void setWorkerType(String workerType) {
        this.workerType = workerType;
    }

    public String getWorkerType() {
        return workerType;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public Long getUserId() {
        return userId;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getStatus() {
        return status;
    }

    public void setPid(Integer pid) {
        this.pid = pid;
    }

    public Integer getPid() {
        return pid;
    }

    public void setHost(String host) {
        this.host = host;
    }

    public String getHost() {
        return host;
    }

    public void setPort(Integer port) {
        this.port = port;
    }

    public Integer getPort() {
        return port;
    }

    public void setLastHeartbeat(Date lastHeartbeat) {
        this.lastHeartbeat = lastHeartbeat;
    }

    public Date getLastHeartbeat() {
        return lastHeartbeat;
    }

    public void setLastTaskTime(Date lastTaskTime) {
        this.lastTaskTime = lastTaskTime;
    }

    public Date getLastTaskTime() {
        return lastTaskTime;
    }

    public void setTotalTasks(Integer totalTasks) {
        this.totalTasks = totalTasks;
    }

    public Integer getTotalTasks() {
        return totalTasks;
    }

    public void setSuccessTasks(Integer successTasks) {
        this.successTasks = successTasks;
    }

    public Integer getSuccessTasks() {
        return successTasks;
    }

    public void setFailedTasks(Integer failedTasks) {
        this.failedTasks = failedTasks;
    }

    public Integer getFailedTasks() {
        return failedTasks;
    }

    public void setWorkerConfig(String workerConfig) {
        this.workerConfig = workerConfig;
    }

    public String getWorkerConfig() {
        return workerConfig;
    }

    public void setStartTime(Date startTime) {
        this.startTime = startTime;
    }

    public Date getStartTime() {
        return startTime;
    }

    public void setCreateTime(Date createTime) {
        this.createTime = createTime;
    }

    public Date getCreateTime() {
        return createTime;
    }

    public void setUpdateTime(Date updateTime) {
        this.updateTime = updateTime;
    }

    public Date getUpdateTime() {
        return updateTime;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this, ToStringStyle.MULTI_LINE_STYLE)
            .append("id", getId())
            .append("workerId", getWorkerId())
            .append("workerType", getWorkerType())
            .append("userId", getUserId())
            .append("status", getStatus())
            .append("pid", getPid())
            .append("host", getHost())
            .append("port", getPort())
            .append("lastHeartbeat", getLastHeartbeat())
            .append("lastTaskTime", getLastTaskTime())
            .append("totalTasks", getTotalTasks())
            .append("successTasks", getSuccessTasks())
            .append("failedTasks", getFailedTasks())
            .append("workerConfig", getWorkerConfig())
            .append("startTime", getStartTime())
            .append("createTime", getCreateTime())
            .append("updateTime", getUpdateTime())
            .toString();
    }
}
