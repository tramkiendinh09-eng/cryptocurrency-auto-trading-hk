package com.ruoyi.dca.domain.trade;

public class TradeNotifyPolicyChannel {
    private Long id;
    private Long policyId;
    private Long channelId;
    private Integer channelOrder;
    private Boolean enabled;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getPolicyId() { return policyId; }
    public void setPolicyId(Long policyId) { this.policyId = policyId; }
    public Long getChannelId() { return channelId; }
    public void setChannelId(Long channelId) { this.channelId = channelId; }
    public Integer getChannelOrder() { return channelOrder; }
    public void setChannelOrder(Integer channelOrder) { this.channelOrder = channelOrder; }
    public Boolean getEnabled() { return enabled; }
    public void setEnabled(Boolean enabled) { this.enabled = enabled; }
}
