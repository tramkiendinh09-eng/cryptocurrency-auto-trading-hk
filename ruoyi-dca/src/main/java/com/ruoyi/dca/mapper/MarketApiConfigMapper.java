package com.ruoyi.dca.mapper;

import com.ruoyi.dca.domain.MarketApiConfig;
import java.util.List;

/**
 * 市场API配置Mapper接口
 *
 * @author ruoyi
 * @date 2026-04-05
 */
public interface MarketApiConfigMapper {

    /**
     * 查询市场API配置
     *
     * @param id 市场API配置主键
     * @return 市场API配置
     */
    public MarketApiConfig selectMarketApiConfigById(Long id);

    /**
     * 查询市场API配置列表
     *
     * @param marketApiConfig 市场API配置
     * @return 市场API配置集合
     */
    public List<MarketApiConfig> selectMarketApiConfigList(MarketApiConfig marketApiConfig);

    /**
     * 查询所有启用的API配置
     *
     * @param dataCategory 数据分类
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
    public int insertMarketApiConfig(MarketApiConfig marketApiConfig);

    /**
     * 修改市场API配置
     *
     * @param marketApiConfig 市场API配置
     * @return 结果
     */
    public int updateMarketApiConfig(MarketApiConfig marketApiConfig);

    /**
     * 删除市场API配置
     *
     * @param id 市场API配置主键
     * @return 结果
     */
    public int deleteMarketApiConfigById(Long id);

    /**
     * 批量删除市场API配置
     *
     * @param ids 需要删除的数据主键集合
     * @return 结果
     */
    public int deleteMarketApiConfigByIds(Long[] ids);
}
