package com.ruoyi.dca.mapper.memory;

import com.ruoyi.dca.domain.memory.AgentMemory;
import com.ruoyi.dca.domain.memory.AgentMemoryUsage;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface AgentMemoryMapper {
    List<AgentMemory> selectCandidateMemories(@Param("agentCode") String agentCode,
                                              @Param("symbol") String symbol,
                                              @Param("tags") List<String> tags,
                                              @Param("limit") Integer limit);

    int insertAgentMemory(AgentMemory memory);

    int insertAgentMemoryUsage(AgentMemoryUsage usage);

    int markMemoryUsed(@Param("id") Long id);

    int disableMemory(@Param("id") Long id);
}
