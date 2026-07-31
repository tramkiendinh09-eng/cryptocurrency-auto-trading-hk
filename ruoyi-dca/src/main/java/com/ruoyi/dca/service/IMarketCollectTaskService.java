package com.ruoyi.dca.service;

import com.ruoyi.dca.domain.MarketCollectTask;

import java.util.List;

public interface IMarketCollectTaskService {

    MarketCollectTask selectTaskById(Long id);

    List<MarketCollectTask> selectTaskList(MarketCollectTask marketCollectTask);

    List<MarketCollectTask> selectEnabledTasks();

    MarketCollectTask selectTaskBySymbol(String symbol);
}
