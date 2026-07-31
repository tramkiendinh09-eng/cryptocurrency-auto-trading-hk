package com.ruoyi.dca.service;

import com.ruoyi.dca.domain.MarketApiConfig;
import java.util.List;
import java.util.Map;

/**
 * 市场API配置服务接口
 *
 * @author ruoyi
 * @date 2026-04-05
 */
public interface IMarketApiConfigService {

    /**
     * 查询市场API配置
     *
     * @param id 市场API配置主键
     * @return 市场API配置
     */
    public MarketApiConfig selectApiConfigById(Long id);

    /**
     * 查询市场API配置列表
     *
     * @param marketApiConfig 市场API配置
     * @return 市场API配置集合
     */
    public List<MarketApiConfig> selectApiConfigList(MarketApiConfig marketApiConfig);

    /**
     * 查询所有启用的API配置
     *
     * @param dataCategory 数据分类（可选）
     * @return 启用的API配置列表
     */
    public List<MarketApiConfig> selectEnabledApis(String dataCategory);

    /**
     * 根据API名称查询配置
     *
     * @param apiName API名称
     * @return API配置
     */
    public MarketApiConfig selectApiByName(String apiName);

    /**
     * 新增市场API配置
     *
     * @param marketApiConfig 市场API配置
     * @return 结果
     */
    public int insertApiConfig(MarketApiConfig marketApiConfig);

    /**
     * 修改市场API配置
     *
     * @param marketApiConfig 市场API配置
     * @return 结果
     */
    public int updateApiConfig(MarketApiConfig marketApiConfig);

    /**
     * 批量删除市场API配置
     *
     * @param ids 需要删除的市场API配置主键集合
     * @return 结果
     */
    public int deleteApiConfigByIds(Long[] ids);

    /**
     * 测试API连接
     *
     * @param id API配置ID
     * @return 测试结果
     */
    public Map<String, Object> testApiConnection(Long id);
}
