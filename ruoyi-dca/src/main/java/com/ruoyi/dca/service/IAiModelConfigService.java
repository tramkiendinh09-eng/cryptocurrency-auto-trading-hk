package com.ruoyi.dca.service;

import java.util.List;
import java.util.Map;
import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.domain.trade.RuntimeModelCallResponse;

/**
 * AI模型配置 服务层
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public interface IAiModelConfigService
{
    /**
     * 查询AI模型配置
     *
     * @param id AI模型配置主键
     * @return AI模型配置
     */
    public AiModelConfig selectAiModelConfigById(Long id);

    /**
     * 根据模型代码查询AI模型配置
     *
     * @param modelCode 模型代码
     * @return AI模型配置
     */
    public AiModelConfig selectAiModelConfigByCode(String modelCode);

    /**
     * 查询AI模型配置列表
     *
     * @param aiModelConfig AI模型配置
     * @return AI模型配置集合
     */
    public List<AiModelConfig> selectAiModelConfigList(AiModelConfig aiModelConfig);

    /**
     * 获取默认模型
     *
     * @return AI模型配置
     */
    public AiModelConfig getDefaultModel();

    /**
     * 新增AI模型配置
     *
     * @param aiModelConfig AI模型配置
     * @return 结果
     */
    public int insertAiModelConfig(AiModelConfig aiModelConfig);

    /**
     * 修改AI模型配置
     *
     * @param aiModelConfig AI模型配置
     * @return 结果
     */
    public int updateAiModelConfig(AiModelConfig aiModelConfig);

    /**
     * 批量删除AI模型配置
     *
     * @param ids 需要删除的AI模型配置主键集合
     * @return 结果
     */
    public int deleteAiModelConfigByIds(Long[] ids);

    /**
     * 删除AI模型配置信息
     *
     * @param id AI模型配置主键
     * @return 结果
     */
    public int deleteAiModelConfigById(Long id);

    /**
     * 校验模型代码是否唯一
     *
     * @param aiModelConfig AI模型配置信息
     * @return 结果
     */
    public boolean checkModelCodeUnique(AiModelConfig aiModelConfig);

    /**
     * 测试模型连接
     *
     * @param id 模型ID
     * @return 测试结果
     */
    public Map<String, Object> testConnection(Long id);

    /**
     * 调用AI模型
     *
     * @param modelId 模型ID
     * @param prompt 提示词
     * @return 响应结果
     */
    public String callAiModel(Long modelId, String prompt);

    /**
     * 调用AI模型（使用默认模型）
     *
     * @param prompt 提示词
     * @return 响应结果
     */
    public String callAiModel(String prompt);

    public RuntimeModelCallResponse callAiModelForRuntime(Long modelId, String prompt);

    /**
     * 加密API密钥
     *
     * @param apiKey 原始API密钥
     * @return 加密后的密钥
     */
    public String encryptApiKey(String apiKey);

    /**
     * 解密API密钥
     *
     * @param encryptedKey 加密的密钥
     * @return 原始API密钥
     */
    public String decryptApiKey(String encryptedKey);

    /**
     * 更新使用统计
     *
     * @param modelId 模型ID
     * @param tokens Token消耗
     * @param cost 费用
     */
    public void updateUsageStats(Long modelId, Integer tokens, Double cost);

    /**
     * 获取使用统计
     *
     * @return 统计信息
     */
    public Map<String, Object> getUsageStats();

    /**
     * 设置为默认模型
     *
     * @param id 模型ID
     * @return 结果
     */
    public int setAsDefault(Long id);

    /**
     * 获取已启用的模型列表
     *
     * @param provider 提供商（可选）
     * @return 模型列表
     */
    public List<AiModelConfig> getEnabledModels(String provider);

    /**
     * 根据模型代码增加使用次数（供Python Worker调用）
     *
     * @param modelCode 模型代码
     * @return 结果
     */
    public int incrementUsageByModelCode(String modelCode);
}
