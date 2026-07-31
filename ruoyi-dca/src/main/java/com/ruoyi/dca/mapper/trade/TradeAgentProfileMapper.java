package com.ruoyi.dca.mapper.trade;

import com.ruoyi.dca.domain.trade.TradeAgentProfile;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface TradeAgentProfileMapper {
    List<TradeAgentProfile> selectTradeAgentProfileList(TradeAgentProfile query);
    TradeAgentProfile selectTradeAgentProfileById(@Param("id") Long id);
    int insertTradeAgentProfile(TradeAgentProfile tradeAgentProfile);
    int updateTradeAgentProfile(TradeAgentProfile tradeAgentProfile);
    int deleteTradeAgentProfileByIds(@Param("ids") Long[] ids);
}
