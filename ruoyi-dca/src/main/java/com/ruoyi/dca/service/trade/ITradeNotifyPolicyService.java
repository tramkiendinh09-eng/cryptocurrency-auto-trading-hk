package com.ruoyi.dca.service.trade;

import com.ruoyi.dca.domain.trade.TradeNotifyPolicy;

import java.util.List;

public interface ITradeNotifyPolicyService {
    List<TradeNotifyPolicy> selectTradeNotifyPolicyList(TradeNotifyPolicy query);
    int insertTradeNotifyPolicy(TradeNotifyPolicy tradeNotifyPolicy);
    int updateTradeNotifyPolicy(TradeNotifyPolicy tradeNotifyPolicy);
    int deleteTradeNotifyPolicyByIds(Long[] ids);
}
