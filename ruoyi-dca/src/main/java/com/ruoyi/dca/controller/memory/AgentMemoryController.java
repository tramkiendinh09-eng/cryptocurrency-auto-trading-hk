package com.ruoyi.dca.controller.memory;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.dca.domain.memory.AgentMemory;
import com.ruoyi.dca.service.memory.AgentMemoryService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/dca/agent-memory")
public class AgentMemoryController extends BaseController {
    @Autowired
    private AgentMemoryService agentMemoryService;

    @Anonymous
    @GetMapping("/list")
    public AjaxResult list(@RequestParam String agentCode,
                           @RequestParam String symbol,
                           @RequestParam(required = false) List<String> tags,
                           @RequestParam(required = false) Integer limit) {
        return success(agentMemoryService.selectCandidateMemories(agentCode, symbol, tags, limit));
    }


    @Anonymous
    @PostMapping("/usage")
    public AjaxResult recordUsage(@RequestBody java.util.Map<String, Object> payload) {
        Object memoryIdValue = payload.get("memoryId");
        Long memoryId = memoryIdValue instanceof Number number ? number.longValue() : Long.valueOf(String.valueOf(memoryIdValue));
        return toAjax(agentMemoryService.recordUsage(
            String.valueOf(payload.getOrDefault("traceId", "")),
            String.valueOf(payload.getOrDefault("symbol", "")),
            memoryId,
            String.valueOf(payload.getOrDefault("agentCode", "")),
            String.valueOf(payload.getOrDefault("usageContextJson", "{}"))
        ));
    }

    @PostMapping
    public AjaxResult add(@RequestBody AgentMemory memory) {
        return toAjax(agentMemoryService.createMemory(memory));
    }

    @PutMapping("/{id}/disable")
    public AjaxResult disable(@PathVariable Long id) {
        return toAjax(agentMemoryService.disableMemory(id));
    }
}
