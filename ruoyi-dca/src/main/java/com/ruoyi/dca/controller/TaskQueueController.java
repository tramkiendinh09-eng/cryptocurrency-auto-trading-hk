package com.ruoyi.dca.controller;

import com.ruoyi.common.annotation.Anonymous;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.dca.domain.dto.TaskDTO;
import com.ruoyi.dca.service.ITaskQueueService;

import java.util.List;

/**
 * 任务队列控制器
 */
@RestController
@RequestMapping("/dca/taskqueue")
public class TaskQueueController {

    @Autowired
    private ITaskQueueService taskQueueService;

    @Anonymous
    @PostMapping("/pull")
    public AjaxResult pullTask(@RequestParam String workerId) {
        TaskDTO task = taskQueueService.pullTask(workerId);
        return AjaxResult.success(task);
    }

    @PreAuthorize("@ss.hasPermi('dca:taskqueue:push')")
    @PostMapping("/push")
    public AjaxResult pushTask(@RequestBody TaskDTO task) {
        taskQueueService.pushTask(task);
        return AjaxResult.success();
    }

    @Anonymous
    @PutMapping("/status")
    public AjaxResult updateStatus(@RequestParam String taskId,
                                   @RequestParam String status,
                                   @RequestParam(required = false) String result) {
        taskQueueService.updateTaskStatus(taskId, status, result);
        return AjaxResult.success();
    }

    @Anonymous
    @PostMapping("/result")
    public AjaxResult saveResult(@RequestParam String taskId, @RequestBody Object result) {
        taskQueueService.saveTaskResult(taskId, result);
        return AjaxResult.success();
    }

    @GetMapping("/result/{taskId}")
    public AjaxResult getResult(@PathVariable String taskId) {
        Object result = taskQueueService.getTaskResult(taskId);
        return AjaxResult.success(result);
    }

    @Anonymous
    @PostMapping("/heartbeat")
    public AjaxResult heartbeat(@RequestParam String workerId) {
        taskQueueService.workerHeartbeat(workerId);
        return AjaxResult.success();
    }

    @GetMapping("/worker/{workerId}/status")
    public AjaxResult workerStatus(@PathVariable String workerId) {
        boolean online = taskQueueService.isWorkerOnline(workerId);
        return AjaxResult.success(online ? "online" : "offline");
    }
}
