package com.ruoyi.dca.utils;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * AI提供商适配器
 * 用于处理不同AI提供商的API差异
 *
 * @author ruoyi
 */
public class AiProviderAdapter
{
    /**
     * AI提供商枚举
     */
    public enum Provider
    {
        OPENAI("openai", "OpenAI", "https://api.openai.com/v1", "chat/completions"),
        ANTHROPIC("anthropic", "Anthropic", "https://api.anthropic.com/v1", "messages"),
        AZURE("azure", "Azure OpenAI", "https://your-resource.openai.azure.com", "openai/deployments/{deployment}/chat/completions"),
        DEEPSEEK("deepseek", "DeepSeek", "https://api.deepseek.com/v1", "chat/completions"),
        OLLAMA("ollama", "Ollama", "http://localhost:11434", "api/chat"),
        LOCAL("local", "Local Model", "http://localhost:11434", "api/chat");

        private final String code;
        private final String name;
        private final String defaultBaseUrl;
        private final String chatEndpoint;

        Provider(String code, String name, String defaultBaseUrl, String chatEndpoint)
        {
            this.code = code;
            this.name = name;
            this.defaultBaseUrl = defaultBaseUrl;
            this.chatEndpoint = chatEndpoint;
        }

        public String getCode()
        {
            return code;
        }

        public String getName()
        {
            return name;
        }

        public String getDefaultBaseUrl()
        {
            return defaultBaseUrl;
        }

        public String getChatEndpoint()
        {
            return chatEndpoint;
        }

        /**
         * 根据代码获取提供商
         */
        public static Provider fromCode(String code)
        {
            for (Provider provider : values())
            {
                if (provider.code.equalsIgnoreCase(code))
                {
                    return provider;
                }
            }
            return OPENAI; // 默认返回OpenAI
        }
    }

    /**
     * 构建请求头
     */
    public static Map<String, String> buildHeaders(Provider provider, String apiKey)
    {
        Map<String, String> headers = new HashMap<>();
        headers.put("Content-Type", "application/json");

        switch (provider)
        {
            case ANTHROPIC:
                headers.put("x-api-key", apiKey);
                headers.put("anthropic-version", "2023-06-01");
                break;
            default:
                headers.put("Authorization", "Bearer " + apiKey);
                break;
        }

        return headers;
    }

    /**
     * 构建聊天请求体
     */
    public static Map<String, Object> buildChatRequest(Provider provider, String modelCode, String prompt,
                                                         Integer maxTokens, Double temperature, Integer timeout)
    {
        Map<String, Object> body = new HashMap<>();

        switch (provider)
        {
            case ANTHROPIC:
                body.put("model", modelCode);
                body.put("max_tokens", maxTokens != null ? maxTokens : 4096);
                body.put("messages", List.of(
                    Map.of("role", "user", "content", prompt)
                ));
                if (temperature != null)
                {
                    body.put("temperature", temperature);
                }
                break;

            case OLLAMA:
            case LOCAL:
                body.put("model", modelCode);
                body.put("stream", false);
                body.put("messages", List.of(
                    Map.of("role", "user", "content", prompt)
                ));
                if (temperature != null)
                {
                    body.put("temperature", temperature);
                }
                break;

            default:
                // OpenAI compatible
                body.put("model", modelCode);
                body.put("max_tokens", maxTokens != null ? maxTokens : 4096);
                body.put("messages", List.of(
                    Map.of("role", "user", "content", prompt)
                ));
                if (temperature != null)
                {
                    body.put("temperature", temperature);
                }
                if (timeout != null)
                {
                    body.put("timeout", timeout);
                }
                break;
        }

        return body;
    }

    /**
     * 构建测试请求体
     */
    public static Map<String, Object> buildTestRequest(Provider provider, String modelCode)
    {
        Map<String, Object> body = new HashMap<>();

        switch (provider)
        {
            case ANTHROPIC:
                body.put("model", modelCode);
                body.put("max_tokens", 10);
                body.put("messages", List.of(
                    Map.of("role", "user", "content", "Hi")
                ));
                break;

            case OLLAMA:
            case LOCAL:
                body.put("model", modelCode);
                body.put("stream", false);
                body.put("messages", List.of(
                    Map.of("role", "user", "content", "Hi")
                ));
                break;

            default:
                body.put("model", modelCode);
                body.put("max_tokens", 10);
                body.put("messages", List.of(
                    Map.of("role", "user", "content", "Hi")
                ));
                break;
        }

        return body;
    }

    /**
     * 解析响应获取内容
     */
    public static String extractContent(Provider provider, String responseBody)
    {
        // 这里可以根据不同提供商的响应格式解析内容
        // 实际实现需要使用JSON解析库
        return responseBody;
    }

    /**
     * 计算Token消耗
     */
    public static int calculateTokenUsage(Provider provider, String prompt, String response)
    {
        // 简化计算：实际应该使用tokenizer
        int promptTokens = prompt.length() / 4; // 粗略估算
        int responseTokens = response.length() / 4;
        return promptTokens + responseTokens;
    }

    /**
     * 获取模型定价（每1K tokens的价格，单位：美元）
     */
    public static double getModelPricing(String modelCode)
    {
        // 这里定义常见模型的价格
        Map<String, Double> pricing = new HashMap<>();
        pricing.put("gpt-4", 0.03);
        pricing.put("gpt-4-turbo", 0.01);
        pricing.put("gpt-3.5-turbo", 0.0015);
        pricing.put("claude-3-opus", 0.015);
        pricing.put("claude-3-sonnet", 0.003);
        pricing.put("claude-3-haiku", 0.00025);
        pricing.put("deepseek-chat", 0.0014);

        return pricing.getOrDefault(modelCode, 0.002); // 默认价格
    }
}
