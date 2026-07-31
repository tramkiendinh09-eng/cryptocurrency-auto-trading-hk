package com.ruoyi.dca.service.memory;

import com.ruoyi.dca.domain.memory.AgentMemory;

import java.util.List;

public interface AgentMemoryService {
    List<AgentMemory> selectCandidateMemories(String agentCode, String symbol, List<String> tags, Integer limit);
    int createMemory(AgentMemory memory);
    int disableMemory(Long id);
    int recordUsage(String traceId, String symbol, Long memoryId, String agentCode, String usageContextJson);
}
