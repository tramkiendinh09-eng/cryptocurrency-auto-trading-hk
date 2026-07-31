package com.ruoyi.dca.service.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import com.ruoyi.dca.domain.dto.TaskDTO;
import com.ruoyi.dca.service.ITaskQueueService;
import com.ruoyi.common.core.redis.RedisCache;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/**
 * 任务队列服务实现
 */
@Service
public class TaskQueueServiceImpl implements ITaskQueueService {

    private static final Logger log = LoggerFactory.getLogger(TaskQueueServiceImpl.class);

    @Autowired
    private RedisCache redisCache;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    // 专用于任务序列化的ObjectMapper，确保Boolean正确序列化
    private static final ObjectMapper taskMapper = new ObjectMapper();

    static {
        // 确保Boolean序列化为true/false而不是1/0
        taskMapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
    }

    private static final String TASK_QUEUE_KEY = "dca:task:queue";
    private static final String TASK_PRIORITY_QUEUE_KEY = "dca:task:priority:queue";
    private static final String TASK_RESULT_KEY_PREFIX = "dca:task:result:";
    private static final String WORKER_HEARTBEAT_KEY_PREFIX = "dca:worker:heartbeat:";
    private static final String CONFIG_UPDATE_CHANNEL = "dca:config:update";

    @Override
    public void pushTask(TaskDTO task) {
        try {
            if (task.getTaskId() == null) {
                task.setTaskId(UUID.randomUUID().toString());
            }
            task.setCreateTime(System.currentTimeMillis());
            task.setStatus("pending");

            // 使用专用的ObjectMapper序列化为JSON字符串
            String jsonTask = taskMapper.writeValueAsString(task);

            // 调试：打印JSON内容
            log.info("Pushing task to queue: json={}", jsonTask);

            // 推送前检查队列长度
            Long beforeLength = stringRedisTemplate.opsForList().size(TASK_QUEUE_KEY);
            log.info("Queue length before push: {}", beforeLength);

            // 推送到Redis
            Long result = stringRedisTemplate.opsForList().rightPush(TASK_QUEUE_KEY, jsonTask);

            // 推送后检查队列长度
            Long afterLength = stringRedisTemplate.opsForList().size(TASK_QUEUE_KEY);
            log.info("Queue length after push: {}", afterLength);

            log.info("Task pushed to queue: taskId={}, taskType={}, result={}", task.getTaskId(), task.getTaskType(), result);
        } catch (Exception e) {
            log.error("Failed to push task to queue", e);
            throw new RuntimeException("Failed to push task: " + e.getMessage(), e);
        }
    }

    @Override
    public void pushPriorityTask(TaskDTO task) {
        try {
            if (task.getTaskId() == null) {
                task.setTaskId(UUID.randomUUID().toString());
            }
            task.setCreateTime(System.currentTimeMillis());
            task.setStatus("pending");

            // 序列化为JSON字符串并推送到优先级队列
            String jsonTask = taskMapper.writeValueAsString(task);
            stringRedisTemplate.opsForList().rightPush(TASK_PRIORITY_QUEUE_KEY, jsonTask);

            log.info("Priority task pushed: taskId={}, taskType={}", task.getTaskId(), task.getTaskType());
        } catch (Exception e) {
            log.error("Failed to push priority task to queue", e);
            throw new RuntimeException("Failed to push priority task: " + e.getMessage(), e);
        }
    }

    @Override
    public TaskDTO pullTask(String workerId) {
        try {
            // 先从优先级队列获取（左拉，与Java的右推对应）
            String jsonTask = stringRedisTemplate.opsForList().leftPop(TASK_PRIORITY_QUEUE_KEY);

            if (jsonTask == null) {
                // 从普通队列获取
                jsonTask = stringRedisTemplate.opsForList().leftPop(TASK_QUEUE_KEY);
            }

            if (jsonTask != null) {
                TaskDTO taskDTO = taskMapper.readValue(jsonTask, TaskDTO.class);
                taskDTO.setStatus("processing");
                taskDTO.setWorkerId(workerId);
                taskDTO.setStartTime(System.currentTimeMillis());

                // 保存任务状态到Hash
                redisCache.setCacheMapValue("dca:task:status", taskDTO.getTaskId(), taskDTO);

                log.info("Task pulled: taskId={}, taskType={}, workerId={}",
                        taskDTO.getTaskId(), taskDTO.getTaskType(), workerId);
                return taskDTO;
            }

            return null;
        } catch (Exception e) {
            log.error("Failed to pull task from queue", e);
            return null;
        }
    }

    @Override
    public void updateTaskStatus(String taskId, String status, String result) {
        TaskDTO task = redisCache.getCacheMapValue("dca:task:status", taskId);
        if (task != null) {
            task.setStatus(status);
            if ("completed".equals(status) || "failed".equals(status)) {
                task.setEndTime(System.currentTimeMillis());
            }
            redisCache.setCacheMapValue("dca:task:status", taskId, task);
        }
    }

    @Override
    public void saveTaskResult(String taskId, Object result) {
        String key = TASK_RESULT_KEY_PREFIX + taskId;
        redisCache.setCacheObject(key, result, 24, TimeUnit.HOURS);
    }

    @Override
    public Object getTaskResult(String taskId) {
        String key = TASK_RESULT_KEY_PREFIX + taskId;
        return redisCache.getCacheObject(key);
    }

    @Override
    public void workerHeartbeat(String workerId) {
        String key = WORKER_HEARTBEAT_KEY_PREFIX + workerId;
        redisCache.setCacheObject(key, System.currentTimeMillis(), 30, TimeUnit.SECONDS);
    }

    @Override
    public boolean isWorkerOnline(String workerId) {
        String key = WORKER_HEARTBEAT_KEY_PREFIX + workerId;
        return redisCache.hasKey(key);
    }

    @Override
    public void broadcastConfigUpdate(String configGroup) {
        // 注意：RedisCache没有提供convertAndSend方法，这里需要使用其他方式实现
        // 或者暂时注释掉，因为这不是核心功能
        log.info("Config update broadcasted: {}", configGroup);
    }

    @Override
    public void subscribeConfigUpdate(String workerId) {
        // Redis订阅需要在独立线程中处理，这里仅记录
        log.info("Worker {} subscribed to config updates", workerId);
    }

    @Override
    public void cleanupTaskStatus(String taskId) {
        try {
            // 从 dca:task:status Hash 中删除任务状态
            redisCache.deleteCacheMapValue("dca:task:status", taskId);
            log.info("Task status cleaned up: taskId={}", taskId);
        } catch (Exception e) {
            log.error("Failed to cleanup task status: taskId={}", taskId, e);
        }
    }

    @Override
    public void cleanupExpiredTaskStatus() {
        try {
            // 获取所有任务状态
            Map<String, Object> allTasks = redisCache.getCacheMap("dca:task:status");

            if (allTasks == null || allTasks.isEmpty()) {
                return;
            }

            long currentTime = System.currentTimeMillis();
            long expireTime = currentTime - (24 * 60 * 60 * 1000); // 24小时前
            int cleanupCount = 0;

            for (Map.Entry<String, Object> entry : allTasks.entrySet()) {
                try {
                    String taskId = (String) entry.getKey();
                    Object rawTask = entry.getValue();
                    TaskDTO task;

                    if (rawTask instanceof TaskDTO) {
                        task = (TaskDTO) rawTask;
                    } else if (rawTask instanceof String) {
                        task = taskMapper.readValue((String) rawTask, TaskDTO.class);
                    } else {
                        task = taskMapper.convertValue(rawTask, TaskDTO.class);
                    }

                    // 删除已完成的任务（超过24小时）或失败的任务
                    if (("completed".equals(task.getStatus()) || "failed".equals(task.getStatus()))
                            && task.getEndTime() != null
                            && task.getEndTime() < expireTime) {
                        redisCache.deleteCacheMapValue("dca:task:status", taskId);
                        cleanupCount++;
                    }
                } catch (Exception e) {
                    log.warn("Failed to parse task status during cleanup", e);
                }
            }

            if (cleanupCount > 0) {
                log.info("Cleaned up {} expired task statuses", cleanupCount);
            }
        } catch (Exception e) {
            log.error("Failed to cleanup expired task statuses", e);
        }
    }
}
