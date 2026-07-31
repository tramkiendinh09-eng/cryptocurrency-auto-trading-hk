package com.ruoyi.dca.job;

import com.ruoyi.dca.service.IMarketDataCollectService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 市场数据采集定时任务
 * 每小时自动采集一次市场数据
 *
 * @author ruoyi
 * @date 2026-04-05
 */
@Component
public class MarketDataCollectionJob {

    private static final Logger log = LoggerFactory.getLogger(MarketDataCollectionJob.class);

    @Autowired
    private IMarketDataCollectService collectService;

    /**
     * 市场数据采集任务
     * 每小时执行一次（cron: 0 0 * * * ?）
     */
//    @Scheduled(cron = "0 0 * * * ?")
    public void hourlyCollection() {
        log.info("==================== 市场数据采集任务开始 ====================");

        try {
            Map<String, ?> results = collectService.collectAllEnabledConfigs("SCHEDULED");

            if (results != null && !results.isEmpty()) {
                log.info("市场数据采集任务完成，共采集{}个交易对", results.size());
            } else {
                log.warn("市场数据采集任务完成，但未采集到任何数据");
            }

        } catch (Exception e) {
            log.error("市场数据采集任务执行失败", e);
        }

        log.info("==================== 市场数据采集任务结束 ====================");
    }

    /**
     * Fear & Greed Index采集任务
     * 每30分钟执行一次
     */
//    @Scheduled(cron = "0 0/30 * * * ?")
    public void fearGreedIndexCollection() {
        log.debug("Fear & Greed Index采集任务开始");

        try {
            Integer index = collectService.getFearGreedIndex();
            if (index != null) {
                log.debug("Fear & Greed Index: {}", index);
            }
        } catch (Exception e) {
            log.error("Fear & Greed Index采集失败", e);
        }

        log.debug("Fear & Greed Index采集任务结束");
    }
}
