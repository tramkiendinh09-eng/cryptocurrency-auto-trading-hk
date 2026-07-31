package com.ruoyi.dca.service;

import com.ruoyi.dca.domain.dto.TaskDTO;

/**
 * 任务队列服务接口
 */
public interface ITaskQueueService {

    /**
     * 推送任务到队列
     */
    void pushTask(TaskDTO task);

    /**
     * 推送高优先级任务
     */
    void pushPriorityTask(TaskDTO task);

    /**
     * 从队列获取任务
     */
    TaskDTO pullTask(String workerId);

    /**
     * 更新任务状态
     */
    void updateTaskStatus(String taskId, String status, String result);

    /**
     * 保存任务结果
     */
    void saveTaskResult(String taskId, Object result);

    /**
     * 获取任务结果
     */
    Object getTaskResult(String taskId);

    /**
     * 心跳上报
     */
    void workerHeartbeat(String workerId);

    /**
     * 检查Worker在线状态
     */
    boolean isWorkerOnline(String workerId);

    /**
     * 广播配置更新
     */
    void broadcastConfigUpdate(String configGroup);

    /**
     * 订阅配置更新
     */
    void subscribeConfigUpdate(String workerId);

    /**
     * 清理任务状态（任务完成后调用）
     */
    void cleanupTaskStatus(String taskId);

    /**
     * 清理所有过期任务状态（定时任务调用）
     */
    void cleanupExpiredTaskStatus();
}
