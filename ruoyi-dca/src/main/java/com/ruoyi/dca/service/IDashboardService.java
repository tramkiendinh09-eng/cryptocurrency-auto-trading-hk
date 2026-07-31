package com.ruoyi.dca.service;

import com.ruoyi.dca.domain.vo.DashboardOverviewVO;

import java.util.Map;

/**
 * 运行时仪表盘服务契约。
 */
public interface IDashboardService {

    /**
     * 获取仪表盘概览对象。
     *
     * @param userId 用户ID
     * @return 运行时概览
     */
    DashboardOverviewVO getOverview(Long userId);

    /**
     * 获取仪表盘概览映射。
     *
     * @param userId 用户ID
     * @return 运行时概览映射
     */
    Map<String, Object> getOverviewMap(Long userId);
}
