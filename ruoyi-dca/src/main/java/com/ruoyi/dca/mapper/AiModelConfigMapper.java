package com.ruoyi.dca.mapper;

import java.util.List;
import com.ruoyi.dca.domain.AiModelConfig;

/**
 * AI模型配置 数据层
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public interface AiModelConfigMapper
{
    /**
     * 查询AI模型配置信息
     *
     * @param id AI模型配置主键
     * @return AI模型配置信息
     */
    public AiModelConfig selectAiModelConfigById(Long id);

    /**
     * 查询AI模型配置列表
     *
     * @param aiModelConfig AI模型配置信息
     * @return AI模型配置集合
     */
    public List<AiModelConfig> selectAiModelConfigList(AiModelConfig aiModelConfig);

    /**
     * 查询默认模型
     *
     * @return AI模型配置信息
     */
    public AiModelConfig selectDefaultModel();

    /**
     * 查询第一个启用的模型
     *
     * @return AI模型配置
     */
    public AiModelConfig selectFirstEnabledModel();

    /**
     * 根据模型代码查询配置
     *
     * @param modelCode 模型代码
     * @return AI模型配置信息
     */
    public AiModelConfig selectByModelCode(String modelCode);

    /**
     * 校验模型代码是否唯一
     *
     * @param modelCode 模型代码
     * @return AI模型配置信息
     */
    public AiModelConfig checkModelCodeUnique(String modelCode);

    /**
     * 新增AI模型配置
     *
     * @param aiModelConfig AI模型配置信息
     * @return 结果
     */
    public int insertAiModelConfig(AiModelConfig aiModelConfig);

    /**
     * 修改AI模型配置
     *
     * @param aiModelConfig AI模型配置信息
     * @return 结果
     */
    public int updateAiModelConfig(AiModelConfig aiModelConfig);

    /**
     * 删除AI模型配置
     *
     * @param id AI模型配置主键
     * @return 结果
     */
    public int deleteAiModelConfigById(Long id);

    /**
     * 批量删除AI模型配置
     *
     * @param ids 需要删除的数据主键集合
     * @return 结果
     */
    public int deleteAiModelConfigByIds(Long[] ids);

    /**
     * 更新使用次数
     *
     * @param id 模型ID
     * @return 结果
     */
    public int incrementUsageCount(Long id);

    /**
     * 根据模型代码增加使用次数
     *
     * @param modelCode 模型代码
     * @return 结果
     */
    public int incrementUsageByModelCode(String modelCode);

    /**
     * 取消所有默认模型设置
     *
     * @return 结果
     */
    public int cancelAllDefaultModels();

    /**
     * 查询已启用的模型列表
     *
     * @param provider 提供商（可选）
     * @return AI模型配置集合
     */
    public List<AiModelConfig> selectEnabledModels(String provider);
}
