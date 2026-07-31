package com.ruoyi.dca.mapper.trade;

import com.ruoyi.dca.domain.trade.TradeNotifyPolicy;
import com.ruoyi.dca.domain.trade.TradeNotifyPolicyChannel;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface TradeNotifyPolicyMapper {
    List<TradeNotifyPolicy> selectTradeNotifyPolicyList(TradeNotifyPolicy query);
    TradeNotifyPolicy selectTradeNotifyPolicyById(@Param("id") Long id);
    int insertTradeNotifyPolicy(TradeNotifyPolicy tradeNotifyPolicy);
    int updateTradeNotifyPolicy(TradeNotifyPolicy tradeNotifyPolicy);
    int deleteTradeNotifyPolicyByIds(@Param("ids") Long[] ids);
    List<TradeNotifyPolicyChannel> selectTradeNotifyPolicyChannels(@Param("policyId") Long policyId);
    int deleteTradeNotifyPolicyChannelsByPolicyId(@Param("policyId") Long policyId);
    int deleteTradeNotifyPolicyChannelsByPolicyIds(@Param("ids") Long[] ids);
    int insertTradeNotifyPolicyChannels(@Param("channels") List<TradeNotifyPolicyChannel> channels);
}
