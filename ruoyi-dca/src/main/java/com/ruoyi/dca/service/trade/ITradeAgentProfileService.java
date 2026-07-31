package com.ruoyi.dca.service.trade;

import com.ruoyi.dca.domain.trade.TradeAgentProfile;

import java.util.List;

public interface ITradeAgentProfileService {
    List<TradeAgentProfile> selectTradeAgentProfileList(TradeAgentProfile query);
    TradeAgentProfile selectTradeAgentProfileById(Long id);
    int insertTradeAgentProfile(TradeAgentProfile tradeAgentProfile);
    int updateTradeAgentProfile(TradeAgentProfile tradeAgentProfile);
    int deleteTradeAgentProfileByIds(Long[] ids);
}
