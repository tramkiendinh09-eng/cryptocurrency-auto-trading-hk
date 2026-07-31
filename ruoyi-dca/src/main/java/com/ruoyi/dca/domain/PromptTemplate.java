package com.ruoyi.dca.domain;

import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;
import org.apache.commons.lang3.builder.ToStringBuilder;
import org.apache.commons.lang3.builder.ToStringStyle;

/**
 * 提示词模板对象 prompt_template
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class PromptTemplate extends BaseEntity {
    private static final long serialVersionUID = 1L;

    /** 主键ID */
    private Long id;

    /** 模板名称 */
    @Excel(name = "模板名称")
    private String name;

    /** 模板代码: dca_day/big_drop/big_rise/daily_report */
    @Excel(name = "模板代码")
    private String code;

    /** 模板内容 */
    private String content;

    /** 模板版本 */
    @Excel(name = "模板版本")
    private Integer version;

    /** 是否启用: 0禁用 1启用 */
    @Excel(name = "是否启用")
    private Integer isActive;

    /** 是否默认模板: 0否 1是 */
    private Integer isDefault;

    /** 变量列表 */
    private String variables;

    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getCode() {
        return code;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public String getContent() {
        return content;
    }

    public void setVersion(Integer version) {
        this.version = version;
    }

    public Integer getVersion() {
        return version;
    }

    public void setIsActive(Integer isActive) {
        this.isActive = isActive;
    }

    public Integer getIsActive() {
        return isActive;
    }

    public void setIsDefault(Integer isDefault) {
        this.isDefault = isDefault;
    }

    public Integer getIsDefault() {
        return isDefault;
    }

    public void setVariables(String variables) {
        this.variables = variables;
    }

    public String getVariables() {
        return variables;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this, ToStringStyle.MULTI_LINE_STYLE)
            .append("id", getId())
            .append("name", getName())
            .append("code", getCode())
            .append("content", getContent())
            .append("version", getVersion())
            .append("isActive", getIsActive())
            .append("isDefault", getIsDefault())
            .append("variables", getVariables())
            .append("remark", getRemark())
            .append("createBy", getCreateBy())
            .append("createTime", getCreateTime())
            .append("updateBy", getUpdateBy())
            .append("updateTime", getUpdateTime())
            .toString();
    }
}
