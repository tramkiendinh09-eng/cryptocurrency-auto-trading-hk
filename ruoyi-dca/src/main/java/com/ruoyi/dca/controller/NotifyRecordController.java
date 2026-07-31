package com.ruoyi.dca.controller;

import java.util.List;
import java.util.Map;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.common.utils.poi.ExcelUtil;
import com.ruoyi.dca.domain.NotifyRecord;
import com.ruoyi.dca.service.INotifyRecordService;

/**
 * 通知记录Controller
 *
 * @author ruoyi
 * @date 2026-04-02
 */
@RestController
@RequestMapping("/dca/notify/records")
public class NotifyRecordController extends BaseController {
    @Autowired
    private INotifyRecordService notifyRecordService;

    /**
     * 查询通知记录列表
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:list')")
    @GetMapping("/list")
    public TableDataInfo list(NotifyRecord notifyRecord) {
        startPage();
        List<NotifyRecord> list = notifyRecordService.selectNotifyRecordList(notifyRecord);
        return getDataTable(list);
    }

    /**
     * 导出通知记录列表
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:export')")
    @Log(title = "通知记录", businessType = BusinessType.EXPORT)
    @PostMapping("/export")
    public void export(HttpServletResponse response, NotifyRecord notifyRecord) {
        List<NotifyRecord> list = notifyRecordService.selectNotifyRecordList(notifyRecord);
        ExcelUtil<NotifyRecord> util = new ExcelUtil<NotifyRecord>(NotifyRecord.class);
        util.exportExcel(response, list, "通知记录数据");
    }

    /**
     * 获取通知记录详细信息
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:query')")
    @GetMapping(value = "/{id}")
    public AjaxResult getInfo(@PathVariable("id") Long id) {
        return success(notifyRecordService.selectNotifyRecordById(id));
    }

    /**
     * 根据渠道ID查询通知记录
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:query')")
    @GetMapping("/channel/{channelId}")
    public AjaxResult getByChannelId(@PathVariable("channelId") Long channelId) {
        List<NotifyRecord> list = notifyRecordService.selectByChannelId(channelId);
        return success(list);
    }

    /**
     * 删除通知记录
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:remove')")
    @Log(title = "通知记录", businessType = BusinessType.DELETE)
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(notifyRecordService.deleteNotifyRecordByIds(ids));
    }

    /**
     * 发送通知
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:send')")
    @Log(title = "发送通知", businessType = BusinessType.INSERT)
    @PostMapping("/send")
    public AjaxResult send(@RequestBody Map<String, Object> params) {
        try {
            Long channelId = Long.valueOf(params.get("channelId").toString());
            String title = (String) params.get("title");
            String content = (String) params.get("content");

            Map<String, Object> result = notifyRecordService.sendNotification(channelId, title, content);
            return success(result);
        } catch (Exception e) {
            logger.error("发送通知失败", e);
            return error("发送通知失败: " + e.getMessage());
        }
    }

    /**
     * 批量发送通知
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:send')")
    @Log(title = "批量发送通知", businessType = BusinessType.INSERT)
    @PostMapping("/batchSend")
    public AjaxResult batchSend(@RequestBody Map<String, Object> params) {
        try {
            @SuppressWarnings("unchecked")
            List<Long> channelIds = (List<Long>) params.get("channelIds");
            String title = (String) params.get("title");
            String content = (String) params.get("content");

            Map<String, Object> result = notifyRecordService.batchSendNotification(channelIds, title, content);
            return success(result);
        } catch (Exception e) {
            logger.error("批量发送通知失败", e);
            return error("批量发送通知失败: " + e.getMessage());
        }
    }

    /**
     * 根据用户ID发送通知
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:send')")
    @Log(title = "发送通知", businessType = BusinessType.INSERT)
    @PostMapping("/sendByUser")
    public AjaxResult sendByUser(@RequestBody Map<String, Object> params) {
        try {
            Long userId = Long.valueOf(params.get("userId").toString());
            String title = (String) params.get("title");
            String content = (String) params.get("content");

            Map<String, Object> result = notifyRecordService.sendByUserId(userId, title, content);
            return success(result);
        } catch (Exception e) {
            logger.error("发送通知失败", e);
            return error("发送通知失败: " + e.getMessage());
        }
    }

    /**
     * 使用模板发送通知
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:send')")
    @Log(title = "发送通知", businessType = BusinessType.INSERT)
    @PostMapping("/sendByTemplate")
    public AjaxResult sendByTemplate(@RequestBody Map<String, Object> params) {
        try {
            Long channelId = Long.valueOf(params.get("channelId").toString());
            Long templateId = Long.valueOf(params.get("templateId").toString());
            @SuppressWarnings("unchecked")
            Map<String, Object> variables = (Map<String, Object>) params.get("variables");

            Map<String, Object> result = notifyRecordService.sendByTemplate(channelId, templateId, variables);
            return success(result);
        } catch (Exception e) {
            logger.error("发送通知失败", e);
            return error("发送通知失败: " + e.getMessage());
        }
    }

    /**
     * 重试失败的通知
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:edit')")
    @Log(title = "重试通知", businessType = BusinessType.UPDATE)
    @PostMapping("/retry/{id}")
    public AjaxResult retry(@PathVariable Long id) {
        try {
            Map<String, Object> result = notifyRecordService.retrySend(id);
            return success(result);
        } catch (Exception e) {
            logger.error("重试通知失败", e);
            return error("重试通知失败: " + e.getMessage());
        }
    }

    /**
     * 批量重试失败的通知
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:edit')")
    @Log(title = "批量重试通知", businessType = BusinessType.UPDATE)
    @PostMapping("/batchRetry")
    public AjaxResult batchRetry() {
        try {
            Map<String, Object> result = notifyRecordService.batchRetryFailed();
            return success(result);
        } catch (Exception e) {
            logger.error("批量重试通知失败", e);
            return error("批量重试通知失败: " + e.getMessage());
        }
    }

    /**
     * 清空过期的成功记录
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:remove')")
    @Log(title = "清空过期记录", businessType = BusinessType.DELETE)
    @PostMapping("/clean")
    public AjaxResult clean(@RequestParam(defaultValue = "30") Integer days) {
        int rows = notifyRecordService.cleanExpiredRecords(days);
        return success("清空完成，共删除 " + rows + " 条记录");
    }

    /**
     * 获取状态统计
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:list')")
    @GetMapping("/stats/status")
    public AjaxResult getStatusStatistics() {
        Map<String, Object> stats = notifyRecordService.getStatusStatistics();
        return success(stats);
    }

    /**
     * 获取渠道统计
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:list')")
    @GetMapping("/stats/channel")
    public AjaxResult getChannelStatistics() {
        Map<String, Object> stats = notifyRecordService.getChannelStatistics();
        return success(stats);
    }

    /**
     * 获取发送统计概览
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:list')")
    @GetMapping("/overview")
    public AjaxResult getOverview() {
        Map<String, Object> overview = notifyRecordService.getSendOverview();
        return success(overview);
    }

    /**
     * 获取发送失败统计
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:list')")
    @GetMapping("/stats/failed")
    public AjaxResult getFailedStats(@RequestParam(defaultValue = "7") Integer days) {
        List<Map<String, Object>> stats = notifyRecordService.getFailedStats(days);
        return success(stats);
    }

    /**
     * 获取发送状态枚举
     */
    @GetMapping("/statusEnums")
    public AjaxResult getStatusEnums() {
        Map<String, String> statusEnums = Map.of(
            "0", "待发送",
            "1", "发送中",
            "2", "成功",
            "3", "失败"
        );
        return success(statusEnums);
    }
}
