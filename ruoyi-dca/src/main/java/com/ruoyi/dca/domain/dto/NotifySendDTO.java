package com.ruoyi.dca.domain.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.io.Serializable;
import java.util.List;
import java.util.Map;

/**
 * 通知发送DTO
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class NotifySendDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    /** 单个发送时使用 */
    @NotNull(message = "渠道ID不能为空", groups = {SingleSend.class})
    private Long channelId;

    /** 批量发送时使用 */
    @NotNull(message = "渠道ID列表不能为空", groups = {BatchSend.class})
    private List<Long> channelIds;

    /** 根据用户发送时使用 */
    @NotNull(message = "用户ID不能为空", groups = {UserSend.class})
    private Long userId;

    /** 通知标题 */
    @NotBlank(message = "通知标题不能为空")
    private String title;

    /** 通知内容 */
    @NotBlank(message = "通知内容不能为空")
    private String content;

    /** 模板ID（使用模板发送时） */
    private Long templateId;

    /** 模板变量（使用模板发送时） */
    private Map<String, Object> variables;

    /** 是否聚合发送 */
    private Boolean aggregate = false;

    /** 聚合键 */
    private String aggregateKey;

    /** 聚合时间窗口（秒） */
    private Integer aggregateSeconds = 60;

    /** 扩展数据 */
    private Map<String, Object> extData;

    public Long getChannelId() {
        return channelId;
    }

    public void setChannelId(Long channelId) {
        this.channelId = channelId;
    }

    public List<Long> getChannelIds() {
        return channelIds;
    }

    public void setChannelIds(List<Long> channelIds) {
        this.channelIds = channelIds;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public Long getTemplateId() {
        return templateId;
    }

    public void setTemplateId(Long templateId) {
        this.templateId = templateId;
    }

    public Map<String, Object> getVariables() {
        return variables;
    }

    public void setVariables(Map<String, Object> variables) {
        this.variables = variables;
    }

    public Boolean getAggregate() {
        return aggregate;
    }

    public void setAggregate(Boolean aggregate) {
        this.aggregate = aggregate;
    }

    public String getAggregateKey() {
        return aggregateKey;
    }

    public void setAggregateKey(String aggregateKey) {
        this.aggregateKey = aggregateKey;
    }

    public Integer getAggregateSeconds() {
        return aggregateSeconds;
    }

    public void setAggregateSeconds(Integer aggregateSeconds) {
        this.aggregateSeconds = aggregateSeconds;
    }

    public Map<String, Object> getExtData() {
        return extData;
    }

    public void setExtData(Map<String, Object> extData) {
        this.extData = extData;
    }

    /**
     * 单个发送校验组
     */
    public interface SingleSend {
    }

    /**
     * 批量发送校验组
     */
    public interface BatchSend {
    }

    /**
     * 用户发送校验组
     */
    public interface UserSend {
    }
}
