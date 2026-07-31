package com.ruoyi.dca.domain.trade;

public class RuntimeModelCallRequest {
    private Long modelId;
    private String prompt;

    public Long getModelId() {
        return modelId;
    }

    public void setModelId(Long modelId) {
        this.modelId = modelId;
    }

    public String getPrompt() {
        return prompt;
    }

    public void setPrompt(String prompt) {
        this.prompt = prompt;
    }
}
