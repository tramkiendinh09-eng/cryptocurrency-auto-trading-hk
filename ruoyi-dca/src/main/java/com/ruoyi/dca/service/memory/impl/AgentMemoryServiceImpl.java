package com.ruoyi.dca.service.memory.impl;

import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.memory.AgentMemory;
import com.ruoyi.dca.domain.memory.AgentMemoryUsage;
import com.ruoyi.dca.mapper.memory.AgentMemoryMapper;
import com.ruoyi.dca.service.memory.AgentMemoryService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

@Service
public class AgentMemoryServiceImpl implements AgentMemoryService {
    private static final int DEFAULT_LIMIT = 5;
    private static final int MAX_LIMIT = 20;

    @Autowired
    private AgentMemoryMapper agentMemoryMapper;

    @Override
    public List<AgentMemory> selectCandidateMemories(String agentCode, String symbol, List<String> tags, Integer limit) {
        String normalizedAgent = normalizeRequired(agentCode, "agentCode");
        String normalizedSymbol = normalizeRequired(symbol, "symbol").toUpperCase(Locale.ROOT);
        List<String> normalizedTags = normalizeTags(tags);
        int normalizedLimit = limit == null ? DEFAULT_LIMIT : Math.max(1, Math.min(MAX_LIMIT, limit));
        return agentMemoryMapper.selectCandidateMemories(normalizedAgent, normalizedSymbol, normalizedTags, normalizedLimit);
    }

    @Override
    public int createMemory(AgentMemory memory) {
        if (memory == null) {
            throw new ServiceException("Memory payload is required");
        }
        memory.setAgentCode(normalizeRequired(memory.getAgentCode(), "agentCode"));
        memory.setSymbol(normalizeRequired(memory.getSymbol(), "symbol").toUpperCase(Locale.ROOT));
        memory.setLessonText(normalizeRequired(memory.getLessonText(), "lessonText"));
        if (memory.getMemoryType() == null || memory.getMemoryType().isBlank()) {
            memory.setMemoryType("lesson");
        }
        if (memory.getMemoryKey() == null || memory.getMemoryKey().isBlank()) {
            String sourceTraceId = memory.getSourceTraceId() == null ? "manual" : memory.getSourceTraceId().trim();
            memory.setMemoryKey(memory.getAgentCode() + ":" + memory.getSymbol() + ":" + sourceTraceId + ":" + memory.getMemoryType());
        }
        if (memory.getQualityScore() == null) {
            memory.setQualityScore(BigDecimal.ZERO);
        }
        if (memory.getConfidence() == null) {
            memory.setConfidence(BigDecimal.ZERO);
        }
        if (memory.getEnabled() == null) {
            memory.setEnabled(Boolean.TRUE);
        }
        return agentMemoryMapper.insertAgentMemory(memory);
    }

    @Override
    public int disableMemory(Long id) {
        if (id == null) {
            throw new ServiceException("Memory id is required");
        }
        return agentMemoryMapper.disableMemory(id);
    }

    @Override
    public int recordUsage(String traceId, String symbol, Long memoryId, String agentCode, String usageContextJson) {
        if (memoryId == null) {
            return 0;
        }
        AgentMemoryUsage usage = new AgentMemoryUsage();
        usage.setTraceId(traceId);
        usage.setSymbol(symbol == null ? "" : symbol.toUpperCase(Locale.ROOT));
        usage.setMemoryId(memoryId);
        usage.setAgentCode(agentCode);
        usage.setUsageContextJson(usageContextJson);
        int inserted = agentMemoryMapper.insertAgentMemoryUsage(usage);
        agentMemoryMapper.markMemoryUsed(memoryId);
        return inserted;
    }

    private String normalizeRequired(String value, String fieldName) {
        String normalized = value == null ? "" : value.trim();
        if (normalized.isEmpty()) {
            throw new ServiceException(fieldName + " is required");
        }
        return normalized;
    }

    private List<String> normalizeTags(List<String> tags) {
        if (tags == null || tags.isEmpty()) {
            return List.of();
        }
        List<String> normalized = new ArrayList<>();
        for (String tag : tags) {
            String value = tag == null ? "" : tag.trim();
            if (!value.isEmpty()) {
                normalized.add(value);
            }
        }
        return normalized;
    }
}
