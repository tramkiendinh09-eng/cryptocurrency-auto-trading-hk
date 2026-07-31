package com.ruoyi.dca.service.impl;

import com.ruoyi.dca.domain.MarketCollectTask;
import com.ruoyi.dca.mapper.MarketCollectTaskMapper;
import com.ruoyi.dca.service.IMarketCollectTaskService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class MarketCollectTaskServiceImpl implements IMarketCollectTaskService {

    @Autowired
    private MarketCollectTaskMapper taskMapper;

    @Override
    public MarketCollectTask selectTaskById(Long id) {
        return taskMapper.selectMarketCollectTaskById(id);
    }

    @Override
    public List<MarketCollectTask> selectTaskList(MarketCollectTask marketCollectTask) {
        return taskMapper.selectMarketCollectTaskList(marketCollectTask);
    }

    @Override
    public List<MarketCollectTask> selectEnabledTasks() {
        return taskMapper.selectEnabledTasks();
    }

    @Override
    public MarketCollectTask selectTaskBySymbol(String symbol) {
        return taskMapper.selectTaskBySymbol(symbol);
    }
}
