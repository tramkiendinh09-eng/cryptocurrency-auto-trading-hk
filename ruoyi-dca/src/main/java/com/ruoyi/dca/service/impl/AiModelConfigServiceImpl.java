package com.ruoyi.dca.service.impl;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Base64;
import java.util.Locale;
import java.net.URI;
import java.math.BigDecimal;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.constant.UserConstants;
import com.ruoyi.common.core.domain.entity.SysUser;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.common.utils.DateUtils;
import com.ruoyi.common.utils.StringUtils;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.common.utils.spring.SpringUtils;
import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.domain.AuditAiCallLog;
import com.ruoyi.dca.domain.trade.RuntimeModelCallResponse;
import com.ruoyi.dca.mapper.AiModelConfigMapper;
import com.ruoyi.dca.mapper.AuditAiCallLogMapper;
import com.ruoyi.dca.service.IAiModelConfigService;

/**
 * AI妯″瀷閰嶇疆 鏈嶅姟灞傚疄鐜?
 *
 * @author ruoyi
 * @date 2026-04-02
 */
@Service
public class AiModelConfigServiceImpl implements IAiModelConfigService
{
    private static final Logger log = LoggerFactory.getLogger(AiModelConfigServiceImpl.class);
    private static final String RUNTIME_AUDIT_SCENE = "trade_runtime";
    private static final String RUNTIME_AUDIT_CREATE_BY = "runtime-worker";

    /** AES鍔犲瘑绠楁硶 */
    private static final String ALGORITHM = "AES/GCM/NoPadding";
    private static final int GCM_TAG_LENGTH = 128;
    private static final int GCM_IV_LENGTH = 12;

    @Autowired
    private AiModelConfigMapper aiModelConfigMapper;

    @Autowired
    private AuditAiCallLogMapper auditAiCallLogMapper;

    @Autowired
    private RestTemplate restTemplate;

    @Value("${ai.encryption.key:ruoyi-ai-model-encryption-key-32bytes!}")
    private String encryptionKey;

    /**
     * 鏌ヨAI妯″瀷閰嶇疆
     *
     * @param id AI妯″瀷閰嶇疆涓婚敭
     * @return AI妯″瀷閰嶇疆
     */
    @Override
    public AiModelConfig selectAiModelConfigById(Long id)
    {
        return aiModelConfigMapper.selectAiModelConfigById(id);
    }

    @Override
    public AiModelConfig selectAiModelConfigByCode(String modelCode)
    {
        return aiModelConfigMapper.selectByModelCode(modelCode);
    }

    @Override
    public RuntimeModelCallResponse callAiModelForRuntime(Long modelId, String prompt)
    {
        AiModelConfig config = null;
        long startedAt = System.currentTimeMillis();
        try
        {
            config = resolveCallableModel(modelId);
            RuntimeModelCallOutcome outcome = callModelForRuntime(config, prompt);
            recordRuntimeAiCall(modelId, config, prompt, outcome, null, System.currentTimeMillis() - startedAt);
            return outcome.payload();
        }
        catch (Exception e)
        {
            recordRuntimeAiCall(modelId, config, prompt, null, e, System.currentTimeMillis() - startedAt);
            log.error("runtime supervisor model call failed", e);
            throw new ServiceException("runtime supervisor model call failed: " + e.getMessage());
        }
    }

    private RuntimeModelCallOutcome callModelForRuntime(AiModelConfig config, String prompt) throws Exception
    {
        String decryptedKey = resolveApiKey(config);
        if (StringUtils.isEmpty(decryptedKey))
        {
            throw new ServiceException("API key must not be empty");
        }

        String url = buildApiUrl(config);
        HttpHeaders headers = buildHeaders(config, decryptedKey);
        Map<String, Object> requestBody = buildChatRequestBody(config, prompt);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        // 使用模型配置的timeout，如果没有配置则使用默认120秒
        int timeoutSeconds = config.getTimeoutSeconds() != null ? config.getTimeoutSeconds() : 120;
        RestTemplate timedRestTemplate = createRuntimeRestTemplate(timeoutSeconds);

        ResponseEntity<String> response = timedRestTemplate.exchange(
            url,
            HttpMethod.POST,
            entity,
            String.class
        );

        if (response.getStatusCode() != HttpStatus.OK)
        {
            throw new ServiceException("model call failed: " + response.getStatusCode());
        }

        aiModelConfigMapper.incrementUsageCount(config.getId());
        JsonNode responseRoot = parseModelResponseJson(config, response.getBody(), url);
        RuntimeTokenUsage usage = extractRuntimeTokenUsage(responseRoot);
        updateRuntimeUsageStats(config.getId(), usage);

        RuntimeModelCallResponse payload = new RuntimeModelCallResponse();
        payload.setModelId(config.getId());
        payload.setModelCode(resolveProviderModelCode(config, null));
        payload.setModelProvider(config.getProvider());
        payload.setContent(extractResponseContent(config, responseRoot));
        if (StringUtils.isEmpty(payload.getContent()))
        {
            throw new ServiceException("model response missing content");
        }
        return new RuntimeModelCallOutcome(payload, usage);
    }

    private AiModelConfig resolveCallableModel(Long modelId)
    {
        AiModelConfig config = modelId == null ? getDefaultModel() : aiModelConfigMapper.selectAiModelConfigById(modelId);
        if (config == null)
        {
            throw new ServiceException(modelId == null ? "default model is unavailable" : "model config not found");
        }
        if (config.getIsEnabled() == null || config.getIsEnabled() != 1)
        {
            throw new ServiceException("model is disabled");
        }
        return config;
    }

    private JsonNode parseModelResponseJson(AiModelConfig config, String responseBody, String url) throws Exception
    {
        String body = normalizeInput(responseBody);
        if (StringUtils.isEmpty(body))
        {
            throw new ServiceException("model response is empty: model=" + resolveProviderModelCode(config, null) + ", url=" + url);
        }
        if (body.startsWith("<"))
        {
            throw new ServiceException("model response is not JSON: model=" + resolveProviderModelCode(config, null)
                + ", url=" + url + ", preview=" + previewResponseBody(body));
        }
        char first = body.charAt(0);
        if (first != '{' && first != '[')
        {
            throw new ServiceException("model response is not JSON: model=" + resolveProviderModelCode(config, null)
                + ", url=" + url + ", preview=" + previewResponseBody(body));
        }
        try
        {
            return new ObjectMapper().readTree(body);
        }
        catch (Exception e)
        {
            throw new ServiceException("model response is not JSON: model=" + resolveProviderModelCode(config, null)
                + ", url=" + url + ", error=" + e.getMessage());
        }
    }

    private String previewResponseBody(String body)
    {
        String normalized = normalizeInput(body).replaceAll("\\s+", " ");
        if (normalized.length() <= 120)
        {
            return normalized;
        }
        return normalized.substring(0, 120) + "...";
    }

    private String extractResponseContent(AiModelConfig config, JsonNode root) throws Exception
    {
        String provider = normalizeProvider(config.getProvider());
        if ("anthropic".equals(provider))
        {
            return collectTextContent(root.path("content"));
        }
        if ("ollama".equals(provider) || "local".equals(provider))
        {
            String content = normalizeInput(root.path("message").path("content").asText(null));
            if (!StringUtils.isEmpty(content))
            {
                return content;
            }
            content = normalizeInput(root.path("response").asText(null));
            if (!StringUtils.isEmpty(content))
            {
                return content;
            }
            return extractDirectJsonPayload(root);
        }

        String content = normalizeInput(root.path("choices").path(0).path("message").path("content").asText(null));
        if (!StringUtils.isEmpty(content))
        {
            return content;
        }
        content = collectTextContent(root.path("choices").path(0).path("message").path("content"));
        if (!StringUtils.isEmpty(content))
        {
            return content;
        }
        content = normalizeInput(root.path("choices").path(0).path("text").asText(null));
        if (!StringUtils.isEmpty(content))
        {
            return content;
        }
        content = normalizeInput(root.path("output_text").asText(""));
        if (!StringUtils.isEmpty(content))
        {
            return content;
        }
        return extractDirectJsonPayload(root);
    }

    protected RestTemplate createRuntimeRestTemplate(int timeoutSeconds)
    {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(30000);
        factory.setReadTimeout(timeoutSeconds * 1000);
        RestTemplate timedRestTemplate = new RestTemplate(factory);
        if (restTemplate != null)
        {
            timedRestTemplate.setMessageConverters(restTemplate.getMessageConverters());
            timedRestTemplate.setErrorHandler(restTemplate.getErrorHandler());
            timedRestTemplate.setInterceptors(restTemplate.getInterceptors());
            timedRestTemplate.setUriTemplateHandler(restTemplate.getUriTemplateHandler());
        }
        return timedRestTemplate;
    }

    private String extractDirectJsonPayload(JsonNode root) throws Exception
    {
        if (root == null || root.isMissingNode() || root.isNull())
        {
            return "";
        }
        if (!root.isObject() && !root.isArray())
        {
            return "";
        }
        if (root.isObject() && (root.has("choices")
                || root.has("content")
                || root.has("message")
                || root.has("response")
                || root.has("output")
                || root.has("output_text")))
        {
            return "";
        }
        return normalizeInput(new ObjectMapper().writeValueAsString(root));
    }

    private String collectTextContent(JsonNode node)
    {
        if (node == null || node.isMissingNode() || node.isNull())
        {
            return "";
        }
        if (node.isTextual())
        {
            return normalizeInput(node.asText());
        }
        if (!node.isArray())
        {
            return "";
        }

        List<String> parts = new ArrayList<>();
        for (JsonNode item : node)
        {
            String text = normalizeInput(item.path("text").asText(null));
            if (StringUtils.isEmpty(text))
            {
                text = normalizeInput(item.path("content").asText(null));
            }
            if (!StringUtils.isEmpty(text))
            {
                parts.add(text);
            }
        }
        return String.join("\n", parts).trim();
    }

    /**
     * 鏌ヨAI妯″瀷閰嶇疆鍒楄〃
     *
     * @param aiModelConfig AI妯″瀷閰嶇疆
     * @return AI妯″瀷閰嶇疆
     */
    @Override
    public List<AiModelConfig> selectAiModelConfigList(AiModelConfig aiModelConfig)
    {
        return aiModelConfigMapper.selectAiModelConfigList(aiModelConfig);
    }

    /**
     * 鑾峰彇榛樿妯″瀷
     *
     * @return AI妯″瀷閰嶇疆
     */
    @Override
    public AiModelConfig getDefaultModel()
    {
        AiModelConfig config = aiModelConfigMapper.selectDefaultModel();
        if (config == null)
        {
            config = aiModelConfigMapper.selectFirstEnabledModel();
            if (config != null)
            {
                log.warn("鏈壘鍒版樉寮忛粯璁I妯″瀷锛屽洖閫€鍒板凡鍚敤妯″瀷 id={}, modelCode={}",
                        config.getId(), config.getModelCode());
            }
        }
        return config;
    }

    /**
     * 鏂板AI妯″瀷閰嶇疆
     *
     * @param aiModelConfig AI妯″瀷閰嶇疆
     * @return 缁撴灉
     */
    @Override
    @Transactional
    public int insertAiModelConfig(AiModelConfig aiModelConfig)
    {
        normalizeModelConfig(aiModelConfig, null);
        if (!checkModelCodeUnique(aiModelConfig))
        {
            throw new ServiceException("鏂板妯″瀷'" + aiModelConfig.getModelName() + "'澶辫触锛屾ā鍨嬩唬鐮佸凡瀛樺湪");
        }

        if (aiModelConfig.getIsEnabled() == null)
        {
            aiModelConfig.setIsEnabled(1);
        }
        if (aiModelConfig.getUsageCount() == null)
        {
            aiModelConfig.setUsageCount(0);
        }
        if (aiModelConfig.getIsDefault() == null)
        {
            aiModelConfig.setIsDefault(0);
        }
        if (aiModelConfig.getTimeoutSeconds() == null)
        {
            aiModelConfig.setTimeoutSeconds(60);
        }

        ensureProviderModelCodePresent(aiModelConfig);
        prepareApiKeyForPersistence(aiModelConfig, null);
        if (StringUtils.isEmpty(aiModelConfig.getApiKeyEncrypted()))
        {
            throw new ServiceException("API瀵嗛挜涓嶈兘涓虹┖");
        }
        if (Integer.valueOf(1).equals(aiModelConfig.getIsDefault()))
        {
            aiModelConfigMapper.cancelAllDefaultModels();
            aiModelConfig.setIsEnabled(1);
        }

        aiModelConfig.setCreateBy(getUsername());
        int rows = aiModelConfigMapper.insertAiModelConfig(aiModelConfig);
        ensureDefaultModelExists();
        return rows;
    }

    /**
     * 淇敼AI妯″瀷閰嶇疆
     *
     * @param aiModelConfig AI妯″瀷閰嶇疆
     * @return 缁撴灉
     */
    @Override
    @Transactional
    public int updateAiModelConfig(AiModelConfig aiModelConfig)
    {
        AiModelConfig oldConfig = aiModelConfigMapper.selectAiModelConfigById(aiModelConfig.getId());
        if (oldConfig == null)
        {
            throw new ServiceException("model config not found");
        }
        normalizeModelConfig(aiModelConfig, oldConfig);
        if (!checkModelCodeUnique(aiModelConfig))
        {
            throw new ServiceException("淇敼妯″瀷'" + aiModelConfig.getModelName() + "'澶辫触锛屾ā鍨嬩唬鐮佸凡瀛樺湪");
        }

        ensureProviderModelCodePresent(aiModelConfig);
        if (aiModelConfig.getIsEnabled() != null
                && aiModelConfig.getIsEnabled() != 1
                && Integer.valueOf(1).equals(oldConfig.getIsDefault()))
        {
            aiModelConfig.setIsDefault(0);
        }
        if (Integer.valueOf(1).equals(aiModelConfig.getIsDefault()))
        {
            aiModelConfigMapper.cancelAllDefaultModels();
            aiModelConfig.setIsEnabled(1);
        }
        prepareApiKeyForPersistence(aiModelConfig, oldConfig);

        aiModelConfig.setUpdateBy(getUsername());
        int rows = aiModelConfigMapper.updateAiModelConfig(aiModelConfig);
        ensureDefaultModelExists();
        return rows;
    }

    /**
     * 鎵归噺鍒犻櫎AI妯″瀷閰嶇疆
     *
     * @param ids 闇€瑕佸垹闄ょ殑AI妯″瀷閰嶇疆涓婚敭
     * @return 缁撴灉
     */
    @Override
    @Transactional
    public int deleteAiModelConfigByIds(Long[] ids)
    {
        int rows = aiModelConfigMapper.deleteAiModelConfigByIds(ids);
        ensureDefaultModelExists();
        return rows;
    }

    /**
     * 鍒犻櫎AI妯″瀷閰嶇疆淇℃伅
     *
     * @param id AI妯″瀷閰嶇疆涓婚敭
     * @return 缁撴灉
     */
    @Override
    @Transactional
    public int deleteAiModelConfigById(Long id)
    {
        int rows = aiModelConfigMapper.deleteAiModelConfigById(id);
        ensureDefaultModelExists();
        return rows;
    }

    /**
     * 鏍￠獙妯″瀷浠ｇ爜鏄惁鍞竴
     *
     * @param aiModelConfig AI妯″瀷閰嶇疆淇℃伅
     * @return 缁撴灉
     */
    @Override
    public boolean checkModelCodeUnique(AiModelConfig aiModelConfig)
    {
        Long id = StringUtils.isNull(aiModelConfig.getId()) ? -1L : aiModelConfig.getId();
        AiModelConfig info = aiModelConfigMapper.checkModelCodeUnique(aiModelConfig.getModelCode());
        if (StringUtils.isNotNull(info) && info.getId().longValue() != id.longValue())
        {
            return UserConstants.NOT_UNIQUE;
        }
        return UserConstants.UNIQUE;
    }

    /**
     * 娴嬭瘯妯″瀷杩炴帴
     *
     * @param id 妯″瀷ID
     * @return 娴嬭瘯缁撴灉
     */
    @Override
    public Map<String, Object> testConnection(Long id)
    {
        Map<String, Object> result = new HashMap<>();

        try
        {
            AiModelConfig config = aiModelConfigMapper.selectAiModelConfigById(id);
            if (config == null)
            {
                result.put("success", false);
                result.put("message", "model config not found");
                return result;
            }

            if (config.getIsEnabled() == null || config.getIsEnabled() != 1)
            {
                result.put("success", false);
                result.put("message", "model is disabled");
                return result;
            }

            String decryptedKey = resolveApiKey(config);
            if (StringUtils.isEmpty(decryptedKey))
            {
                result.put("success", false);
                result.put("message", "API瀵嗛挜涓嶈兘涓虹┖");
                return result;
            }

            String url = buildApiUrl(config);
            HttpHeaders headers = buildHeaders(config, decryptedKey);
            Map<String, Object> requestBody = buildTestRequestBody(config);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            log.info("娴嬭瘯AI妯″瀷杩炴帴: model={}, url={}", config.getModelCode(), url);

            ResponseEntity<String> response = restTemplate.exchange(
                url,
                HttpMethod.POST,
                entity,
                String.class
            );

            if (response.getStatusCode() == HttpStatus.OK)
            {
                result.put("success", true);
                result.put("message", "杩炴帴鎴愬姛");
                result.put("response", response.getBody());
            }
            else
            {
                result.put("success", false);
                result.put("message", "杩炴帴澶辫触: " + response.getStatusCode());
            }
        }
        catch (HttpClientErrorException e)
        {
            log.error("娴嬭瘯AI妯″瀷杩炴帴澶辫触: {}", e.getMessage());
            result.put("success", false);
            result.put("message", "杩炴帴澶辫触: " + e.getMessage());
            try
            {
                result.put("details", e.getResponseBodyAsString());
            }
            catch (Exception ex)
            {
            }
        }
        catch (ResourceAccessException e)
        {
            log.error("娴嬭瘯AI妯″瀷杩炴帴瓒呮椂: {}", e.getMessage());
            result.put("success", false);
            result.put("message", "杩炴帴瓒呮椂: " + e.getMessage());
        }
        catch (Exception e)
        {
            log.error("娴嬭瘯AI妯″瀷杩炴帴寮傚父", e);
            result.put("success", false);
            result.put("message", "杩炴帴寮傚父: " + e.getMessage());
        }

        return result;
    }

    /**
     * 璋冪敤AI妯″瀷
     *
     * @param modelId 妯″瀷ID
     * @param prompt 鎻愮ず璇?
     * @return 鍝嶅簲缁撴灉
     */
    @Override
    public String callAiModel(Long modelId, String prompt)
    {
        try
        {
            AiModelConfig config = aiModelConfigMapper.selectAiModelConfigById(modelId);
            if (config == null)
            {
                throw new ServiceException("model config not found");
            }

            if (config.getIsEnabled() == null || config.getIsEnabled() != 1)
            {
                throw new ServiceException("model is disabled");
            }

            return callModelInternal(config, prompt);
        }
        catch (Exception e)
        {
            log.error("璋冪敤AI妯″瀷澶辫触", e);
            throw new ServiceException("璋冪敤AI妯″瀷澶辫触: " + e.getMessage());
        }
    }

    /**
     * 璋冪敤AI妯″瀷锛堜娇鐢ㄩ粯璁ゆā鍨嬶級
     *
     * @param prompt 鎻愮ず璇?
     * @return 鍝嶅簲缁撴灉
     */
    @Override
    public String callAiModel(String prompt)
    {
        try
        {
            AiModelConfig config = getDefaultModel();
            if (config == null)
            {
                throw new ServiceException("鏈壘鍒板彲鐢ㄧ殑榛樿妯″瀷");
            }

            return callModelInternal(config, prompt);
        }
        catch (Exception e)
        {
            log.error("璋冪敤榛樿AI妯″瀷澶辫触", e);
            throw new ServiceException("璋冪敤榛樿AI妯″瀷澶辫触: " + e.getMessage());
        }
    }

    /**
     * 鍐呴儴璋冪敤妯″瀷鏂规硶
     */
    private String callModelInternal(AiModelConfig config, String prompt) throws Exception
    {
        // 瑙ｅ瘑API瀵嗛挜
        String decryptedKey = resolveApiKey(config);
        if (StringUtils.isEmpty(decryptedKey))
        {
            throw new ServiceException("API瀵嗛挜涓嶈兘涓虹┖");
        }

        // 鏋勫缓璇锋眰
        String url = buildApiUrl(config);
        HttpHeaders headers = buildHeaders(config, decryptedKey);

        Map<String, Object> requestBody = buildChatRequestBody(config, prompt);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        log.info("璋冪敤AI妯″瀷: model={}, prompt={}", config.getModelCode(),
                 prompt.length() > 100 ? prompt.substring(0, 100) + "..." : prompt);

        ResponseEntity<String> response = restTemplate.exchange(
            url,
            HttpMethod.POST,
            entity,
            String.class
        );

        if (response.getStatusCode() == HttpStatus.OK)
        {
            // 鏇存柊浣跨敤缁熻
            aiModelConfigMapper.incrementUsageCount(config.getId());

            // 瑙ｆ瀽鍝嶅簲鑾峰彇token娑堣€楋紙濡傛灉鏈夌殑璇濓級
            parseAndUpdateUsageStats(config.getId(), response.getBody());

            return response.getBody();
        }
        else
        {
            throw new ServiceException("璋冪敤澶辫触: " + response.getStatusCode());
        }
    }

    /**
     * 鍔犲瘑API瀵嗛挜
     *
     * @param apiKey 鍘熷API瀵嗛挜
     * @return 鍔犲瘑鍚庣殑瀵嗛挜
     */
    @Override
    public String encryptApiKey(String apiKey)
    {
        try
        {
            // 纭繚瀵嗛挜闀垮害涓?2瀛楄妭锛圓ES-256锛?
            byte[] keyBytes = adjustKeyLength(encryptionKey.getBytes(), 32);
            SecretKey key = new SecretKeySpec(keyBytes, "AES");

            // 鐢熸垚闅忔満IV
            byte[] iv = new byte[GCM_IV_LENGTH];
            java.security.SecureRandom random = new java.security.SecureRandom();
            random.nextBytes(iv);

            // 鍔犲瘑
            Cipher cipher = Cipher.getInstance(ALGORITHM);
            GCMParameterSpec gcmSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
            cipher.init(Cipher.ENCRYPT_MODE, key, gcmSpec);

            byte[] encrypted = cipher.doFinal(apiKey.getBytes());

            // 缁勫悎IV鍜屽姞瀵嗘暟鎹?
            byte[] combined = new byte[iv.length + encrypted.length];
            System.arraycopy(iv, 0, combined, 0, iv.length);
            System.arraycopy(encrypted, 0, combined, iv.length, encrypted.length);

            // Base64缂栫爜骞舵坊鍔犳爣璇?
            return "ENC:" + Base64.getEncoder().encodeToString(combined);
        }
        catch (Exception e)
        {
            log.error("鍔犲瘑API瀵嗛挜澶辫触", e);
            throw new ServiceException("鍔犲瘑API瀵嗛挜澶辫触: " + e.getMessage());
        }
    }

    /**
     * 瑙ｅ瘑API瀵嗛挜
     *
     * @param encryptedKey 鍔犲瘑鐨勫瘑閽?
     * @return 鍘熷API瀵嗛挜
     */
    @Override
    public String decryptApiKey(String encryptedKey)
    {
        try
        {
            // 濡傛灉涓嶆槸鍔犲瘑鏍煎紡锛岀洿鎺ヨ繑鍥?
            if (StringUtils.isEmpty(encryptedKey) || !encryptedKey.startsWith("ENC:"))
            {
                return encryptedKey;
            }

            // 鍘婚櫎鏍囪瘑骞禕ase64瑙ｇ爜
            String base64Encoded = encryptedKey.substring(4);
            byte[] combined = Base64.getDecoder().decode(base64Encoded);

            // 鍒嗙IV鍜屽姞瀵嗘暟鎹?
            byte[] iv = new byte[GCM_IV_LENGTH];
            byte[] encrypted = new byte[combined.length - GCM_IV_LENGTH];
            System.arraycopy(combined, 0, iv, 0, iv.length);
            System.arraycopy(combined, iv.length, encrypted, 0, encrypted.length);

            // 瑙ｅ瘑
            byte[] keyBytes = adjustKeyLength(encryptionKey.getBytes(), 32);
            SecretKey key = new SecretKeySpec(keyBytes, "AES");

            Cipher cipher = Cipher.getInstance(ALGORITHM);
            GCMParameterSpec gcmSpec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
            cipher.init(Cipher.DECRYPT_MODE, key, gcmSpec);

            byte[] decrypted = cipher.doFinal(encrypted);
            return new String(decrypted);
        }
        catch (Exception e)
        {
            log.error("瑙ｅ瘑API瀵嗛挜澶辫触", e);
            // 瑙ｅ瘑澶辫触鏃惰繑鍥炲師鍊硷紙鍙兘鏄湭鍔犲瘑鐨勬棫鏁版嵁锛?
            return encryptedKey;
        }
    }

    /**
     * 璋冩暣瀵嗛挜闀垮害
     */
    private byte[] adjustKeyLength(byte[] key, int length)
    {
        byte[] adjusted = new byte[length];
        System.arraycopy(key, 0, adjusted, 0, Math.min(key.length, length));
        if (key.length < length)
        {
            // 鐢?濉厖鍓╀綑閮ㄥ垎
            for (int i = key.length; i < length; i++)
            {
                adjusted[i] = 0;
            }
        }
        return adjusted;
    }

    /**
     * 鏇存柊浣跨敤缁熻
     *
     * @param modelId 妯″瀷ID
     * @param tokens Token娑堣€?
     * @param cost 璐圭敤
     */
    @Override
    public void updateUsageStats(Long modelId, Integer tokens, Double cost)
    {
        // 杩欓噷鍙互璁板綍鍒板崟鐙殑缁熻琛ㄤ腑
        log.info("鏇存柊妯″瀷浣跨敤缁熻: modelId={}, tokens={}, cost={}", modelId, tokens, cost);
    }

    /**
     * 鑾峰彇浣跨敤缁熻锛堜粠audit_ai_call_log琛ㄧ粺璁＄湡瀹炴暟鎹級
     *
     * @return 缁熻淇℃伅
     */
    @Override
    public Map<String, Object> getUsageStats()
    {
        Map<String, Object> stats = new HashMap<>();

        List<AiModelConfig> allModels = aiModelConfigMapper.selectAiModelConfigList(new AiModelConfig());

        int totalModels = allModels.size();
        int enabledModels = 0;
        int totalCalls = 0;
        long totalTokens = 0;
        double totalCost = 0.0;
        double totalResponseTime = 0.0;
        int validResponseCount = 0;
        Map<String, Integer> providerStats = new HashMap<>();
        Map<String, Integer> modelUsageStats = new HashMap<>();

        // 浠巃udit_ai_call_log琛ㄨ幏鍙栫湡瀹炵殑璋冪敤缁熻
        List<Map<String, Object>> modelStatsFromLog = new ArrayList<>();
        try {
            modelStatsFromLog = auditAiCallLogMapper.selectModelUsageStats();
        } catch (Exception e) {
            log.error("鑾峰彇AI璋冪敤缁熻澶辫触", e);
        }

        // 灏唌odelStatsFromLog杞崲涓篗ap锛屾柟渚垮揩閫熸煡鎵?
        Map<String, Map<String, Object>> modelStatsMap = new HashMap<>();
        for (Map<String, Object> stat : modelStatsFromLog) {
            String modelName = (String) stat.get("model");
            if (modelName != null && !modelName.isEmpty()) {
                modelStatsMap.put(modelName, stat);
            }
        }

        for (AiModelConfig model : allModels)
        {
            if (model.getIsEnabled() != null && model.getIsEnabled() == 1)
            {
                enabledModels++;
            }

            String provider = model.getProvider();
            if (provider != null) {
                providerStats.put(provider, providerStats.getOrDefault(provider, 0) + 1);
            }

            // 浠巃udit_ai_call_log缁熻涓幏鍙栬妯″瀷鐨勮皟鐢ㄦ鏁?
            // 鍖归厤model_code鎴杕odel_name
            int callCount = 0;
            Long tokens = 0L;
            Double avgResponseTime = 0.0;

            // 灏濊瘯閫氳繃model_code鍖归厤锛堟鏌ull锛?
            String modelCode = model.getModelCode();
            String modelName = model.getModelName();

            if (modelCode != null) {
                Map<String, Object> stat = modelStatsMap.get(modelCode);
                if (stat == null && modelName != null) {
                    stat = modelStatsMap.get(modelName);
                }

                if (stat != null) {
                    callCount = ((Number) stat.getOrDefault("call_count", 0)).intValue();
                    tokens = ((Number) stat.getOrDefault("total_tokens", 0L)).longValue();
                    Object avgRespObj = stat.get("avg_response_time");
                    if (avgRespObj != null) {
                        avgResponseTime = ((Number) avgRespObj).doubleValue();
                    }
                }

                // 瀛樺偍姣忎釜妯″瀷鐨勪娇鐢ㄦ鏁帮紙鐢ㄤ簬鍓嶇鏄剧ず锛?
                modelUsageStats.put(modelCode, callCount);

                // 鏇存柊閰嶇疆琛ㄤ腑鐨剈sage_count瀛楁锛堜繚鎸佸悓姝ワ級
                if (model.getUsageCount() == null || model.getUsageCount() != callCount) {
                    AiModelConfig updateConfig = new AiModelConfig();
                    updateConfig.setId(model.getId());
                    updateConfig.setUsageCount(callCount);
                    try {
                        aiModelConfigMapper.updateAiModelConfig(updateConfig);
                    } catch (Exception e) {
                        log.error("鏇存柊妯″瀷浣跨敤娆℃暟澶辫触: modelId={}, callCount={}", model.getId(), callCount, e);
                    }
                }
            }

            totalCalls += callCount;
            totalTokens += tokens;

            // 绱鍝嶅簲鏃堕棿锛堢敤浜庤绠楀钩鍧囧€硷級
            if (callCount > 0 && avgResponseTime > 0) {
                totalResponseTime += (avgResponseTime * callCount);
                validResponseCount += callCount;
            }
        }

        // 璁＄畻骞冲潎鍝嶅簲鏃堕棿锛堟绉掞級
        double avgLatency = 0.0;
        if (validResponseCount > 0) {
            avgLatency = totalResponseTime / validResponseCount;
        }

        // 璁＄畻鎬昏垂鐢紙绠€鍖栦及绠楋細鎸?M tokens = $2.5 璁＄畻锛屽嵆1 token = $0.0000025锛?
        // 瀹為檯璐圭敤搴旇鏍规嵁涓嶅悓鎻愪緵鍟嗙殑瀹氫环鏉ヨ绠?
        double costPerToken = 0.0000025; // $2.5 per 1M tokens
        totalCost = totalTokens * costPerToken;

        stats.put("totalCalls", totalCalls);  // 鍓嶇鏈熸湜鐨勫瓧娈靛悕
        stats.put("totalTokens", totalTokens);
        stats.put("totalCost", totalCost);  // 鏂板锛氭€昏垂鐢?
        stats.put("avgLatency", avgLatency);  // 鏂板锛氬钩鍧囧搷搴旀椂闂?ms)
        stats.put("totalModels", totalModels);
        stats.put("enabledModels", enabledModels);
        stats.put("disabledModels", totalModels - enabledModels);
        stats.put("providerStats", providerStats);
        stats.put("modelUsageStats", modelUsageStats);
        stats.put("currentTime", DateUtils.getTime());

        return stats;
    }

    /**
     * 璁剧疆涓洪粯璁ゆā鍨?
     *
     * @param id 妯″瀷ID
     * @return 缁撴灉
     */
    @Override
    @Transactional
    public int setAsDefault(Long id)
    {
        AiModelConfig target = aiModelConfigMapper.selectAiModelConfigById(id);
        if (target == null)
        {
            throw new ServiceException("model config not found");
        }

        aiModelConfigMapper.cancelAllDefaultModels();
        AiModelConfig config = new AiModelConfig();
        config.setId(id);
        config.setIsDefault(1);
        config.setIsEnabled(1);
        config.setUpdateBy(getUsername());
        return aiModelConfigMapper.updateAiModelConfig(config);
    }

    /**
     * 鑾峰彇宸插惎鐢ㄧ殑妯″瀷鍒楄〃
     *
     * @param provider 鎻愪緵鍟嗭紙鍙€夛級
     * @return 妯″瀷鍒楄〃
     */
    @Override
    public List<AiModelConfig> getEnabledModels(String provider)
    {
        return aiModelConfigMapper.selectEnabledModels(normalizeProvider(provider));
    }

    /**
     * 鏋勫缓API URL
     */
    private String buildApiUrl(AiModelConfig config)
    {
        String endpoint = normalizeInput(config.getApiEndpoint());
        if (!StringUtils.isEmpty(endpoint))
        {
            if (isAbsoluteUrl(endpoint))
            {
                return normalizeAbsoluteApiEndpoint(config, endpoint);
            }
            return joinUrl(getDefaultBaseUrl(config.getProvider()), endpoint);
        }

        String baseUrl = normalizeInput(config.getApiBaseUrl());
        if (StringUtils.isEmpty(baseUrl))
        {
            baseUrl = getDefaultBaseUrl(config.getProvider());
        }
        return joinUrl(baseUrl, getChatEndpoint(config.getProvider()));
    }

    private String normalizeAbsoluteApiEndpoint(AiModelConfig config, String endpoint)
    {
        String chatEndpoint = getChatEndpoint(config.getProvider());
        if (endsWithPath(endpoint, chatEndpoint))
        {
            return endpoint;
        }
        if (isBaseApiUrl(endpoint))
        {
            return joinUrl(endpoint, chatEndpoint);
        }
        return endpoint;
    }

    private boolean isBaseApiUrl(String endpoint)
    {
        try
        {
            URI uri = URI.create(endpoint);
            if (!StringUtils.isEmpty(uri.getQuery()) || !StringUtils.isEmpty(uri.getFragment()))
            {
                return false;
            }
            String path = normalizeInput(uri.getPath());
            if (StringUtils.isEmpty(path) || "/".equals(path))
            {
                return true;
            }
            String normalizedPath = path.endsWith("/") ? path.substring(0, path.length() - 1) : path;
            return normalizedPath.matches("/v\\d+(\\.\\d+)?") || "/api".equals(normalizedPath);
        }
        catch (IllegalArgumentException e)
        {
            return false;
        }
    }

    private boolean endsWithPath(String endpoint, String path)
    {
        String normalizedEndpoint = normalizeInput(endpoint);
        String normalizedPath = normalizeInput(path);
        if (StringUtils.isEmpty(normalizedEndpoint) || StringUtils.isEmpty(normalizedPath))
        {
            return false;
        }
        String endpointWithoutSlash = normalizedEndpoint.endsWith("/")
            ? normalizedEndpoint.substring(0, normalizedEndpoint.length() - 1)
            : normalizedEndpoint;
        String pathWithoutSlash = normalizedPath.startsWith("/") ? normalizedPath.substring(1) : normalizedPath;
        return endpointWithoutSlash.endsWith("/" + pathWithoutSlash);
    }

    /**
     * 鑾峰彇鎻愪緵鍟嗛粯璁ase URL
     */
    private String getDefaultBaseUrl(String provider)
    {
        return switch (normalizeProvider(provider))
        {
            case "openai" -> "https://api.openai.com/v1";
            case "deepseek" -> "https://api.deepseek.com";
            case "anthropic" -> "https://api.anthropic.com/v1";
            case "azure" -> "https://your-resource.openai.azure.com";
            case "ollama", "local" -> "http://localhost:11434";
            default -> "https://api.openai.com/v1";
        };
    }

    /**
     * 鑾峰彇鑱婂ぉ绔偣
     */
    private String getChatEndpoint(String provider)
    {
        return switch (normalizeProvider(provider))
        {
            case "anthropic" -> "messages";
            case "ollama", "local" -> "api/chat";
            default -> "chat/completions";
        };
    }

    /**
     * 鏋勫缓璇锋眰澶?
     */
    private HttpHeaders buildHeaders(AiModelConfig config, String decryptedKey)
    {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        String provider = normalizeProvider(config.getProvider());

        if ("anthropic".equals(provider))
        {
            headers.set("x-api-key", decryptedKey);
            headers.set("anthropic-version", "2023-06-01");
        }
        else
        {
            headers.set("Authorization", "Bearer " + decryptedKey);
        }

        return headers;
    }

    /**
     * 鏋勫缓娴嬭瘯璇锋眰浣?
     */
    private Map<String, Object> buildTestRequestBody(AiModelConfig config)
    {
        return buildMessageRequestBody(config, "Hi", 10);
    }

    /**
     * 鏋勫缓鑱婂ぉ璇锋眰浣?
     */
    private Map<String, Object> buildChatRequestBody(AiModelConfig config, String prompt)
    {
        return buildMessageRequestBody(config, prompt, config.getMaxTokens() != null ? config.getMaxTokens() : 4096);
    }

    /**
     * 瑙ｆ瀽骞舵洿鏂颁娇鐢ㄧ粺璁?
     */
    private void parseAndUpdateUsageStats(Long modelId, String responseBody)
    {
        try
        {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(responseBody);

            JsonNode usage = root.path("usage");
            if (usage.isObject())
            {
                int totalTokens = usage.path("total_tokens").asInt();
                double cost = calculateCost(modelId, totalTokens);
                updateUsageStats(modelId, totalTokens, cost);
            }
        }
        catch (Exception e)
        {
            log.debug("瑙ｆ瀽浣跨敤缁熻澶辫触锛堝彲鑳芥彁渚涘晢涓嶈繑鍥炴淇℃伅锛? {}", e.getMessage());
        }
    }

    private RuntimeTokenUsage extractRuntimeTokenUsage(String responseBody)
    {
        try
        {
            ObjectMapper mapper = new ObjectMapper();
            return extractRuntimeTokenUsage(mapper.readTree(responseBody));
        }
        catch (Exception e)
        {
            return RuntimeTokenUsage.empty();
        }
    }

    private RuntimeTokenUsage extractRuntimeTokenUsage(JsonNode root)
    {
        if (root == null)
        {
            return RuntimeTokenUsage.empty();
        }
        JsonNode usage = root.path("usage");
        if (!usage.isObject())
        {
            return RuntimeTokenUsage.empty();
        }
        return new RuntimeTokenUsage(
            nullableInt(usage.path("prompt_tokens")),
            nullableInt(usage.path("completion_tokens")),
            nullableInt(usage.path("total_tokens"))
        );
    }

    private void updateRuntimeUsageStats(Long modelId, RuntimeTokenUsage usage)
    {
        Integer totalTokens = usage.totalTokens();
        if (totalTokens == null || totalTokens <= 0)
        {
            return;
        }
        double cost = calculateCost(modelId, totalTokens);
        updateUsageStats(modelId, totalTokens, cost);
    }

    private Integer nullableInt(JsonNode node)
    {
        if (node == null || node.isMissingNode() || node.isNull())
        {
            return null;
        }
        return node.asInt();
    }

    private void recordRuntimeAiCall(Long modelId, AiModelConfig config, String prompt,
                                     RuntimeModelCallOutcome outcome, Exception error, long responseTime)
    {
        if (auditAiCallLogMapper == null)
        {
            return;
        }
        try
        {
            AuditAiCallLog auditLog = new AuditAiCallLog();
            auditLog.setUserId(resolveRuntimeAuditUserId());
            auditLog.setScene(RUNTIME_AUDIT_SCENE);
            auditLog.setModel(resolveRuntimeAuditModel(modelId, config));
            auditLog.setPrompt(normalizeInput(prompt));
            auditLog.setResponseTime(Math.max(responseTime, 0L));
            auditLog.setCallTime(DateUtils.getNowDate());
            auditLog.setCreateBy(RUNTIME_AUDIT_CREATE_BY);
            if (outcome != null)
            {
                auditLog.setResponse(outcome.payload().getContent());
                auditLog.setPromptTokens(outcome.usage().promptTokens());
                auditLog.setCompletionTokens(outcome.usage().completionTokens());
                auditLog.setTotalTokens(outcome.usage().totalTokens());
                auditLog.setStatus(1);
            }
            else
            {
                auditLog.setStatus(0);
                auditLog.setErrorMsg(normalizeInput(error == null ? null : error.getMessage()));
            }
            auditAiCallLogMapper.insertAuditAiCallLog(auditLog);
        }
        catch (Exception auditError)
        {
            log.warn("runtime ai audit log insert failed: {}", auditError.getMessage());
        }
    }

    private Long resolveRuntimeAuditUserId()
    {
        try
        {
            return SecurityUtils.getUserId();
        }
        catch (Exception ignored)
        {
            return null;
        }
    }

    private String resolveRuntimeAuditModel(Long modelId, AiModelConfig config)
    {
        String providerModelCode = resolveProviderModelCode(config, null);
        if (!StringUtils.isEmpty(providerModelCode))
        {
            return providerModelCode;
        }
        if (config != null && !StringUtils.isEmpty(config.getModelName()))
        {
            return config.getModelName();
        }
        return modelId == null ? "default" : String.valueOf(modelId);
    }

    private record RuntimeModelCallOutcome(RuntimeModelCallResponse payload, RuntimeTokenUsage usage) {}

    private record RuntimeTokenUsage(Integer promptTokens, Integer completionTokens, Integer totalTokens)
    {
        private static RuntimeTokenUsage empty()
        {
            return new RuntimeTokenUsage(null, null, null);
        }
    }

    /**
     * 璁＄畻璐圭敤
     */
    private double calculateCost(Long modelId, int tokens)
    {
        // 杩欓噷鍙互鏍规嵁妯″瀷绫诲瀷璁＄畻璐圭敤
        // 绠€鍖栫増锛氭寜token璁＄畻锛屽疄闄呭簲璇ユ牴鎹笉鍚屾ā鍨嬬殑瀹氫环
        return tokens * 0.00001; // 绀轰緥浠锋牸
    }

    /**
     * 闅愯棌API瀵嗛挜
     */
    private void normalizeModelConfig(AiModelConfig config, AiModelConfig existing)
    {
        if (config == null)
        {
            return;
        }
        config.setModelKey(normalizeInput(config.getModelKey()));
        config.setModelName(normalizeInput(config.getModelName()));
        config.setModelVersion(normalizeInput(config.getModelVersion()));
        config.setModelCode(resolveProviderModelCode(config, existing));
        config.setProvider(normalizeProvider(config.getProvider()));
        if (StringUtils.isEmpty(normalizeInput(config.getApiEndpoint())))
        {
            config.setApiEndpoint(joinUrl(getDefaultBaseUrl(config.getProvider()), getChatEndpoint(config.getProvider())));
        }
    }

    private void ensureProviderModelCodePresent(AiModelConfig config)
    {
        if (config == null)
        {
            return;
        }
        if (StringUtils.isEmpty(config.getModelCode()))
        {
            throw new ServiceException("model_code must not be empty");
        }
    }

    private void prepareApiKeyForPersistence(AiModelConfig incoming, AiModelConfig existing)
    {
        String directApiKey = normalizeInput(incoming.getApiKey());
        String apiKeyEncryptedInput = normalizeInput(incoming.getApiKeyEncrypted());

        if (!StringUtils.isEmpty(directApiKey))
        {
            incoming.setApiKeyEncrypted(encryptApiKeyIfNeeded(directApiKey));
        }
        else if (existing != null && isMaskedApiKeyInput(apiKeyEncryptedInput, existing.getApiKeyEncrypted()))
        {
            incoming.setApiKeyEncrypted(encryptApiKeyIfNeeded(existing.getApiKeyEncrypted()));
        }
        else if (!StringUtils.isEmpty(apiKeyEncryptedInput))
        {
            incoming.setApiKeyEncrypted(encryptApiKeyIfNeeded(apiKeyEncryptedInput));
        }
        else if (existing != null)
        {
            incoming.setApiKeyEncrypted(encryptApiKeyIfNeeded(existing.getApiKeyEncrypted()));
        }

        incoming.setApiKey(null);
    }

    private boolean isMaskedApiKeyInput(String candidate, String existingStored)
    {
        if (StringUtils.isEmpty(candidate) || StringUtils.isEmpty(existingStored))
        {
            return false;
        }
        return candidate.equals(maskApiKey(existingStored));
    }

    private String encryptApiKeyIfNeeded(String apiKeyValue)
    {
        if (StringUtils.isEmpty(apiKeyValue))
        {
            return apiKeyValue;
        }
        return apiKeyValue.startsWith("ENC:") ? apiKeyValue : encryptApiKey(apiKeyValue);
    }

    private String resolveApiKey(AiModelConfig config)
    {
        if (config == null)
        {
            return null;
        }
        String storedKey = !StringUtils.isEmpty(config.getApiKeyEncrypted()) ? config.getApiKeyEncrypted() : config.getApiKey();
        return decryptApiKey(storedKey);
    }

    private void ensureDefaultModelExists()
    {
        if (aiModelConfigMapper.selectDefaultModel() != null)
        {
            return;
        }

        AiModelConfig fallback = aiModelConfigMapper.selectFirstEnabledModel();
        if (fallback == null)
        {
            return;
        }

        aiModelConfigMapper.cancelAllDefaultModels();
        AiModelConfig updateConfig = new AiModelConfig();
        updateConfig.setId(fallback.getId());
        updateConfig.setIsDefault(1);
        updateConfig.setIsEnabled(1);
        updateConfig.setUpdateBy(getUsername());
        aiModelConfigMapper.updateAiModelConfig(updateConfig);
    }

    private Map<String, Object> buildMessageRequestBody(AiModelConfig config, String prompt, int maxTokens)
    {
        Map<String, Object> body = new HashMap<>();
        String provider = normalizeProvider(config.getProvider());
        String providerModelCode = resolveProviderModelCode(config, null);

        body.put("model", providerModelCode);
        body.put("messages", List.of(Map.of("role", "user", "content", prompt)));

        if ("ollama".equals(provider) || "local".equals(provider))
        {
            body.put("stream", false);
            addSamplingParameters(body, config, false);
            return body;
        }

        body.put("max_tokens", maxTokens);
        addSamplingParameters(body, config, !"anthropic".equals(provider));
        return body;
    }

    private void addSamplingParameters(Map<String, Object> body, AiModelConfig config, boolean includeTopP)
    {
        if (isDeepSeekReasoner(config))
        {
            return;
        }

        addDecimalParameter(body, "temperature", config.getTemperature());
        if (includeTopP)
        {
            addDecimalParameter(body, "top_p", config.getTopP());
        }
    }

    private void addDecimalParameter(Map<String, Object> body, String key, BigDecimal value)
    {
        if (value != null)
        {
            body.put(key, value);
        }
    }

    private String resolveProviderModelCode(AiModelConfig config, AiModelConfig existing)
    {
        String modelCode = normalizeInput(config == null ? null : config.getModelCode());
        if (!StringUtils.isEmpty(modelCode))
        {
            return modelCode;
        }
        String modelVersion = normalizeInput(config == null ? null : config.getModelVersion());
        if (!StringUtils.isEmpty(modelVersion))
        {
            return modelVersion;
        }
        return normalizeInput(existing == null ? null : existing.getModelCode());
    }

    private boolean isDeepSeekReasoner(AiModelConfig config)
    {
        return config != null
                && "deepseek".equals(normalizeProvider(config.getProvider()))
                && "deepseek-reasoner".equalsIgnoreCase(resolveProviderModelCode(config, null));
    }

    private String normalizeProvider(String provider)
    {
        if (StringUtils.isEmpty(provider))
        {
            return "openai";
        }
        String normalized = provider.trim().toLowerCase(Locale.ROOT);
        return "claude".equals(normalized) ? "anthropic" : normalized;
    }

    private String normalizeInput(String value)
    {
        return value == null ? null : value.trim();
    }

    private boolean isAbsoluteUrl(String value)
    {
        return value.startsWith("http://") || value.startsWith("https://");
    }

    private String joinUrl(String baseUrl, String path)
    {
        String normalizedBase = normalizeInput(baseUrl);
        String normalizedPath = normalizeInput(path);
        if (StringUtils.isEmpty(normalizedBase))
        {
            return normalizedPath;
        }
        if (StringUtils.isEmpty(normalizedPath))
        {
            return normalizedBase;
        }
        String left = normalizedBase.endsWith("/") ? normalizedBase.substring(0, normalizedBase.length() - 1) : normalizedBase;
        String right = normalizedPath.startsWith("/") ? normalizedPath.substring(1) : normalizedPath;
        return left + "/" + right;
    }
    private String maskApiKey(String apiKey)
    {
        if (StringUtils.isEmpty(apiKey))
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

    /**
     * 鑾峰彇褰撳墠鐢ㄦ埛鍚?
     */
    private String getUsername()
    {
        try
        {
            return SecurityUtils.getUsername();
        }
        catch (Exception e)
        {
            return "system";
        }
    }

    /**
     * 鏍规嵁妯″瀷浠ｇ爜澧炲姞浣跨敤娆℃暟锛堜緵Python Worker璋冪敤锛?
     *
     * @param modelCode 妯″瀷浠ｇ爜
     * @return 缁撴灉
     */
    @Override
    public int incrementUsageByModelCode(String modelCode)
    {
        try
        {
            return aiModelConfigMapper.incrementUsageByModelCode(modelCode);
        }
        catch (Exception e)
        {
            log.error("澧炲姞浣跨敤娆℃暟澶辫触: modelCode={}, error={}", modelCode, e.getMessage());
            return 0;
        }
    }
}
