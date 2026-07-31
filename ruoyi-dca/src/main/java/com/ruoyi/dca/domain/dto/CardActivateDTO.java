package com.ruoyi.dca.domain.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 卡密激活DTO
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class CardActivateDTO {
    /** 卡密 */
    @NotBlank(message = "卡密不能为空")
    private String cardKey;

    /** 用户ID */
    private Long userId;

    /** 机器码 */
    @NotBlank(message = "机器码不能为空")
    private String machineCode;

    public void setCardKey(String cardKey) {
        this.cardKey = cardKey;
    }

    public String getCardKey() {
        return cardKey;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public Long getUserId() {
        return userId;
    }

    public void setMachineCode(String machineCode) {
        this.machineCode = machineCode;
    }

    public String getMachineCode() {
        return machineCode;
    }
}
