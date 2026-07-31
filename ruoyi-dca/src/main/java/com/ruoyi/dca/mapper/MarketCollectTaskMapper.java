package com.ruoyi.dca.mapper;

import com.ruoyi.dca.domain.MarketCollectTask;

import java.util.List;

public interface MarketCollectTaskMapper {

    MarketCollectTask selectMarketCollectTaskById(Long id);

    List<MarketCollectTask> selectMarketCollectTaskList(MarketCollectTask marketCollectTask);

    List<MarketCollectTask> selectEnabledTasks();

    MarketCollectTask selectTaskBySymbol(String symbol);
}
