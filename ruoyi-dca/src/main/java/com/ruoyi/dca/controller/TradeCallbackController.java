package com.ruoyi.dca.controller;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.dca.domain.dto.TradeResultDTO;
import com.ruoyi.dca.service.ITradeCallbackService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import jakarta.servlet.http.HttpServletRequest;

/**
 * 交易回调Controller
 * 接收Python Worker发送的交易结果回调
 *
 * @author ruoyi
 * @date 2026-04-03
 */
@RestController
@Anonymous
@RequestMapping("/dca/callback")
public class TradeCallbackController extends BaseController {

    private static final Logger log = LoggerFactory.getLogger(TradeCallbackController.class);

    @Autowired
    private ITradeCallbackService tradeCallbackService;

    /**
     * 接收Python Worker的交易结果回调
     *
     * @param result 交易结果DTO
     * @return 处理结果
     */
    @PostMapping("/trade")
    public AjaxResult receiveTradeCallback(@RequestBody TradeResultDTO result, HttpServletRequest request) {
        try {
            String clientIp = getClientIp(request);

            log.info("Received trade callback from {}: taskId={}, symbol={}, success={}",
                    clientIp, result.getTaskId(), result.getSymbol(), result.getSuccess());

            // 基本校验
            if (result.getTaskId() == null || result.getTaskId().isEmpty()) {
                return AjaxResult.error("taskId is required");
            }

            // 异步处理回调（避免阻塞Python Worker）
            tradeCallbackService.processTradeResult(result);

            return AjaxResult.success("Callback received and processed");

        } catch (Exception e) {
            log.error("Failed to process trade callback: taskId={}", result.getTaskId(), e);
            return AjaxResult.error("Failed to process callback: " + e.getMessage());
        }
    }

    /**
     * 接收Python Worker的提醒结果回调
     *
     * @param alertData 提醒数据
     * @return 处理结果
     */
    @PostMapping("/alert")
    public AjaxResult receiveAlertCallback(@RequestBody java.util.Map<String, Object> alertData, HttpServletRequest request) {
        try {
            String clientIp = getClientIp(request);

            String taskId = (String) alertData.get("taskId");
            Long userId = extractLong(alertData.get("userId"));
            String alertTitle = (String) alertData.get("alertTitle");
            String alertContent = (String) alertData.get("alertContent");

            log.info("Received alert callback from {}: taskId={}, userId={}, title={}",
                    clientIp, taskId, userId, alertTitle);

            // 基本校验
            if (taskId == null || taskId.isEmpty()) {
                return AjaxResult.error("taskId is required");
            }

            // 处理提醒并发送通知
            tradeCallbackService.processAlertResult(userId, alertTitle, alertContent, alertData);

            return AjaxResult.success("Alert callback received and processed");

        } catch (Exception e) {
            log.error("Failed to process alert callback", e);
            return AjaxResult.error("Failed to process alert callback: " + e.getMessage());
        }
    }

    /**
     * 从对象中提取Long值
     */
    private Long extractLong(Object value) {
        if (value == null) return null;
        if (value instanceof Long) return (Long) value;
        if (value instanceof Integer) return ((Integer) value).longValue();
        if (value instanceof String) return Long.parseLong((String) value);
        return null;
    }

    /**
     * 健康检查端点
     *
     * @return 服务状态
     */
    @GetMapping("/health")
    public AjaxResult healthCheck() {
        return AjaxResult.success("Callback service is running");
    }

    /**
     * 获取客户端真实IP
     */
    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        // 处理多个IP的情况（X-Forwarded-For可能包含多个IP）
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        return ip;
    }
}
