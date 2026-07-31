package com.ruoyi.dca.controller;

import java.util.List;
import java.util.Map;
import jakarta.servlet.http.HttpServletResponse;
import com.ruoyi.common.annotation.Anonymous;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.common.utils.poi.ExcelUtil;
import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.service.IAiModelConfigService;

/**
 * AI模型配置Controller
 *
 * @author ruoyi
 * @date 2026-04-02
 */
@RestController
@RequestMapping("/dca/ai/models")
public class AiModelConfigController extends BaseController
{
    @Autowired
    private IAiModelConfigService aiModelConfigService;

    /**
     * 查询AI模型配置列表
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:list')")
    @GetMapping("/list")
    public TableDataInfo list(AiModelConfig aiModelConfig)
    {
        startPage();
        List<AiModelConfig> list = sanitizeForDisplay(aiModelConfigService.selectAiModelConfigList(aiModelConfig));
        return getDataTable(list);
    }

    /**
     * 导出AI模型配置列表
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:export')")
    @Log(title = "AI模型配置", businessType = BusinessType.EXPORT)
    @PostMapping("/export")
    public void export(HttpServletResponse response, AiModelConfig aiModelConfig)
    {
        List<AiModelConfig> list = sanitizeForDisplay(aiModelConfigService.selectAiModelConfigList(aiModelConfig));
        ExcelUtil<AiModelConfig> util = new ExcelUtil<AiModelConfig>(AiModelConfig.class);
        util.exportExcel(response, list, "AI模型配置数据");
    }

    /**
     * 获取AI模型配置详细信息
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:query')")
    @GetMapping(value = "/{id}")
    public AjaxResult getInfo(@PathVariable("id") Long id)
    {
        return success(sanitizeForDisplay(aiModelConfigService.selectAiModelConfigById(id)));
    }

    /**
     * 根据模型代码查询配置
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:query')")
    @GetMapping(value = "/code/{modelCode}")
    public AjaxResult getByModelCode(@PathVariable("modelCode") String modelCode)
    {
        return success(sanitizeForDisplay(aiModelConfigService.selectAiModelConfigByCode(modelCode)));
    }

    /**
     * 获取默认模型
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:query')")
    @GetMapping("/default")
    public AjaxResult getDefaultModel()
    {
        return success(sanitizeForDisplay(aiModelConfigService.getDefaultModel()));
    }

    /**
     * 获取已启用的模型列表
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:query')")
    @GetMapping("/enabled")
    public AjaxResult getEnabledModels(@RequestParam(required = false) String provider)
    {
        return success(sanitizeForDisplay(aiModelConfigService.getEnabledModels(provider)));
    }

    /**
     * 新增AI模型配置
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:add')")
    @Log(title = "AI模型配置", businessType = BusinessType.INSERT)
    @PostMapping
    public AjaxResult add(@Validated @RequestBody AiModelConfig aiModelConfig)
    {
        aiModelConfig.setCreateBy(getUsername());
        return toAjax(aiModelConfigService.insertAiModelConfig(aiModelConfig));
    }

    /**
     * 修改AI模型配置
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:edit')")
    @Log(title = "AI模型配置", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult edit(@Validated @RequestBody AiModelConfig aiModelConfig)
    {
        aiModelConfig.setUpdateBy(getUsername());
        return toAjax(aiModelConfigService.updateAiModelConfig(aiModelConfig));
    }

    /**
     * 删除AI模型配置
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:remove')")
    @Log(title = "AI模型配置", businessType = BusinessType.DELETE)
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids)
    {
        return toAjax(aiModelConfigService.deleteAiModelConfigByIds(ids));
    }

    /**
     * 测试模型连接
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:edit')")
    @Log(title = "测试AI模型连接", businessType = BusinessType.OTHER)
    @PostMapping("/{id}/test")
    public AjaxResult testConnection(@PathVariable("id") Long id)
    {
        Map<String, Object> result = aiModelConfigService.testConnection(id);
        return success(result);
    }

    /**
     * 设置为默认模型
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:edit')")
    @Log(title = "设置默认AI模型", businessType = BusinessType.UPDATE)
    @PostMapping("/{id}/setDefault")
    public AjaxResult setAsDefault(@PathVariable("id") Long id)
    {
        return toAjax(aiModelConfigService.setAsDefault(id));
    }

    /**
     * 调用AI模型
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:use')")
    @Log(title = "调用AI模型", businessType = BusinessType.OTHER)
    @PostMapping("/{id}/call")
    public AjaxResult callModel(@PathVariable("id") Long id, @RequestBody Map<String, String> request)
    {
        String prompt = request.get("prompt");
        if (prompt == null || prompt.trim().isEmpty())
        {
            return error("提示词不能为空");
        }

        try
        {
            String response = aiModelConfigService.callAiModel(id, prompt);
            return success(response);
        }
        catch (Exception e)
        {
            return error("调用失败: " + e.getMessage());
        }
    }

    /**
     * 调用默认AI模型
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:use')")
    @Log(title = "调用默认AI模型", businessType = BusinessType.OTHER)
    @PostMapping("/call")
    public AjaxResult callDefaultModel(@RequestBody Map<String, String> request)
    {
        String prompt = request.get("prompt");
        if (prompt == null || prompt.trim().isEmpty())
        {
            return error("提示词不能为空");
        }

        try
        {
            String response = aiModelConfigService.callAiModel(prompt);
            return success(response);
        }
        catch (Exception e)
        {
            return error("调用失败: " + e.getMessage());
        }
    }

    /**
     * 获取使用统计
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:query')")
    @GetMapping("/stats")
    public AjaxResult getUsageStats()
    {
        Map<String, Object> stats = aiModelConfigService.getUsageStats();
        return success(stats);
    }

    /**
     * 加密API密钥
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:query')")
    @PostMapping("/encrypt")
    public AjaxResult encryptApiKey(@RequestBody Map<String, String> request)
    {
        String apiKey = request.get("apiKey");
        if (apiKey == null || apiKey.trim().isEmpty())
        {
            return error("API密钥不能为空");
        }

        try
        {
            String encrypted = aiModelConfigService.encryptApiKey(apiKey);
            return success(encrypted);
        }
        catch (Exception e)
        {
            return error("加密失败: " + e.getMessage());
        }
    }

    /**
     * 解密API密钥
     */
    @PreAuthorize("@ss.hasPermi('dca:aiModel:query')")
    @PostMapping("/decrypt")
    public AjaxResult decryptApiKey(@RequestBody Map<String, String> request)
    {
        String encryptedKey = request.get("encryptedKey");
        if (encryptedKey == null || encryptedKey.trim().isEmpty())
        {
            return error("加密密钥不能为空");
        }

        try
        {
            String decrypted = aiModelConfigService.decryptApiKey(encryptedKey);
            return success(decrypted);
        }
        catch (Exception e)
        {
            return error("解密失败: " + e.getMessage());
        }
    }

    /**
     * 获取默认AI模型配置（包含解密后的API密钥）
     * 此接口供内部Python Worker调用，不需要权限验证
     */
    @Anonymous
    @GetMapping("/config/default")
    public AjaxResult getDefaultConfigWithKey()
    {
        try
        {
            AiModelConfig config = aiModelConfigService.getDefaultModel();
            if (config == null)
            {
                return error("未找到默认AI模型配置");
            }

            // 解密API密钥（仅用于内部调用）
            if (config.getApiKeyEncrypted() != null && !config.getApiKeyEncrypted().isEmpty())
            {
                String decryptedKey = aiModelConfigService.decryptApiKey(config.getApiKeyEncrypted());
                config.setApiKey(decryptedKey);
            }
            config.setApiKeyEncrypted(null);

            return success(config);
        }
        catch (Exception e)
        {
            return error("获取AI配置失败: " + e.getMessage());
        }
    }

    /**
     * 根据ID获取AI模型配置（包含解密后的API密钥）
     * 此接口供内部Python Worker调用，不需要权限验证
     */
    @Anonymous
    @GetMapping("/config/{id}")
    public AjaxResult getConfigById(@PathVariable("id") Long id)
    {
        try
        {
            AiModelConfig config = aiModelConfigService.selectAiModelConfigById(id);
            if (config == null)
            {
                return error("AI模型配置不存在");
            }

            // 解密API密钥（仅用于内部调用）
            if (config.getApiKeyEncrypted() != null && !config.getApiKeyEncrypted().isEmpty())
            {
                String decryptedKey = aiModelConfigService.decryptApiKey(config.getApiKeyEncrypted());
                config.setApiKey(decryptedKey);
            }
            config.setApiKeyEncrypted(null);

            return success(config);
        }
        catch (Exception e)
        {
            return error("获取AI配置失败: " + e.getMessage());
        }
    }
    private List<AiModelConfig> sanitizeForDisplay(List<AiModelConfig> configs)
    {
        if (configs == null)
        {
            return null;
        }
        for (AiModelConfig config : configs)
        {
            sanitizeForDisplay(config);
        }
        return configs;
    }

    private AiModelConfig sanitizeForDisplay(AiModelConfig config)
    {
        if (config == null)
        {
            return null;
        }
        if (config.getApiKeyEncrypted() != null && !config.getApiKeyEncrypted().isEmpty())
        {
            config.setApiKeyEncrypted(maskApiKey(config.getApiKeyEncrypted()));
        }
        config.setApiKey(null);
        return config;
    }

    private String maskApiKey(String apiKey)
    {
        if (apiKey == null || apiKey.isEmpty())
        {
            return "";
        }
        if (apiKey.length() <= 8)
        {
            return "****";
        }
        if (apiKey.startsWith("ENC:"))
        {
            return "ENC:****" + apiKey.substring(apiKey.length() - 4);
        }
        return apiKey.substring(0, 4) + "****" + apiKey.substring(apiKey.length() - 4);
    }
}
