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

    /**
     * worker 复盘平仓后写入长期记忆。
     *
     * 这个方法此前是本控制器里唯一没标 @Anonymous 的——list 和 usage 都标了。
     * worker 走的是同一套免鉴权的内网协议（TRADE_RUNTIME_BEARER_TOKEN 不是
     * RuoYi 的 JWT，实测带上仍然 401），所以每一次写入都被拒。
     *
     * 失败还被双重掩盖：RuoYi 的认证失败返回 **HTTP 200**、把 401 装在 body 里，
     * 于是 worker 的 response.raise_for_status() 不抛；worker 再把它归成笼统的
     * memory_store_create_failed，只字不提鉴权。结果是 agent_memory 表从部署至今
     * 一行都没有，整条"从平仓复盘中学习"的闭环是死的，而没人看得出来。
     *
     * 公开面已在 nginx 逐条封堵：前缀 /prod-api/dca/agent-memory/ 加精确
     * /prod-api/dca/agent-memory（尾斜杠规则挡不住裸路径，而写入正是裸路径），
     * 后端本身只监听 127.0.0.1。记忆会进 LLM 提示词，这个入口一旦对外开放
     * 就是往交易系统里注入伪造"教训"的通道，改动这两处时务必一起核对。
     */
    @Anonymous
    @PostMapping
    public AjaxResult add(@RequestBody AgentMemory memory) {
        return toAjax(agentMemoryService.createMemory(memory));
    }

    @PutMapping("/{id}/disable")
    public AjaxResult disable(@PathVariable Long id) {
        return toAjax(agentMemoryService.disableMemory(id));
    }
}
