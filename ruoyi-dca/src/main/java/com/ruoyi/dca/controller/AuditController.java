package com.ruoyi.dca.controller;

import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.common.utils.DateUtils;
import com.ruoyi.common.utils.poi.ExcelUtil;
import com.ruoyi.dca.domain.AuditOperationLog;
import com.ruoyi.dca.domain.AuditStrategyTrigger;
import com.ruoyi.dca.domain.AuditAiCallLog;
import com.ruoyi.dca.service.IAuditOperationLogService;
import com.ruoyi.dca.service.IAuditStrategyTriggerService;
import com.ruoyi.dca.service.IAuditAiCallLogService;

/**
 * 日志审计 信息操作处理
 *
 * @author ruoyi
 */
@RestController
@RequestMapping("/dca/audit")
public class AuditController extends BaseController
{
    private static final String LEGACY_TRIGGER_RETIRED_MESSAGE = "旧DCA触发审计已退役，请使用运行时决策审计控制台";

    @Autowired
    private IAuditOperationLogService auditOperationLogService;

    @Autowired
    private IAuditStrategyTriggerService auditStrategyTriggerService;

    @Autowired
    private IAuditAiCallLogService auditAiCallLogService;

    /**
     * 获取操作审计日志列表
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:list')")
    @GetMapping("/operations")
    public TableDataInfo listOperations(AuditOperationLog auditOperationLog)
    {
        startPage();
        // 只能查看自己的操作日志，管理员可以查看所有
        if (!isAdmin())
        {
            auditOperationLog.setUserId(getUserId());
        }
        List<AuditOperationLog> list = auditOperationLogService.selectAuditOperationLogList(auditOperationLog);
        return getDataTable(list);
    }

    /**
     * 导出操作审计日志列表
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:export')")
    @Log(title = "操作审计日志", businessType = BusinessType.EXPORT)
    @PostMapping("/operations/export")
    public void exportOperations(HttpServletResponse response, AuditOperationLog auditOperationLog)
    {
        // 只能导出自己的操作日志，管理员可以导出所有
        if (!isAdmin())
        {
            auditOperationLog.setUserId(getUserId());
        }
        List<AuditOperationLog> list = auditOperationLogService.selectAuditOperationLogList(auditOperationLog);
        ExcelUtil<AuditOperationLog> util = new ExcelUtil<AuditOperationLog>(AuditOperationLog.class);
        util.exportExcel(response, list, "操作审计日志");
    }

    /**
     * 获取操作审计日志详细信息
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:query')")
    @GetMapping("/operation/{id}")
    public AjaxResult getOperationInfo(@PathVariable("id") Long id)
    {
        AuditOperationLog log = auditOperationLogService.selectAuditOperationLogById(id);
        // 数据隔离检查
        if (log != null && !isAdmin() && !log.getUserId().equals(getUserId()))
        {
            return error("无权访问此日志");
        }
        return success(log);
    }

    /**
     * 删除操作审计日志
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:remove')")
    @Log(title = "操作审计日志", businessType = BusinessType.DELETE)
    @DeleteMapping("/operations/{ids}")
    public AjaxResult removeOperations(@PathVariable Long[] ids)
    {
        // 数据隔离检查
        if (!isAdmin())
        {
            for (Long id : ids)
            {
                AuditOperationLog log = auditOperationLogService.selectAuditOperationLogById(id);
                if (log != null && !log.getUserId().equals(getUserId()))
                {
                    return error("无权删除日志 ID: " + id);
                }
            }
        }
        return toAjax(auditOperationLogService.deleteAuditOperationLogByIds(ids));
    }

    /**
     * 获取策略触发日志列表
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:list')")
    @GetMapping("/triggers")
    public AjaxResult listTriggers(AuditStrategyTrigger auditStrategyTrigger)
    {
        return success(LEGACY_TRIGGER_RETIRED_MESSAGE);
    }

    /**
     * 导出策略触发日志列表
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:export')")
    @Log(title = "策略触发日志", businessType = BusinessType.EXPORT)
    @PostMapping("/triggers/export")
    public AjaxResult exportTriggers(HttpServletResponse response, AuditStrategyTrigger auditStrategyTrigger)
    {
        return success(LEGACY_TRIGGER_RETIRED_MESSAGE);
    }

    /**
     * 获取策略触发日志详细信息
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:query')")
    @GetMapping("/trigger/{id}")
    public AjaxResult getTriggerInfo(@PathVariable("id") Long id)
    {
        return success(LEGACY_TRIGGER_RETIRED_MESSAGE);
    }

    /**
     * 删除策略触发日志
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:remove')")
    @Log(title = "策略触发日志", businessType = BusinessType.DELETE)
    @DeleteMapping("/triggers/{ids}")
    public AjaxResult removeTriggers(@PathVariable Long[] ids)
    {
        return success(LEGACY_TRIGGER_RETIRED_MESSAGE);
    }

    /**
     * 获取AI调用日志列表
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:list')")
    @GetMapping("/aiCalls")
    public TableDataInfo listAiCalls(AuditAiCallLog auditAiCallLog)
    {
        startPage();
        // 只能查看自己的AI调用日志，管理员可以查看所有
        if (!isAdmin())
        {
            auditAiCallLog.setUserId(getUserId());
        }
        List<AuditAiCallLog> list = auditAiCallLogService.selectAuditAiCallLogList(auditAiCallLog);
        return getDataTable(list);
    }

    /**
     * 导出AI调用日志列表
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:export')")
    @Log(title = "AI调用日志", businessType = BusinessType.EXPORT)
    @PostMapping("/aiCalls/export")
    public void exportAiCalls(HttpServletResponse response, AuditAiCallLog auditAiCallLog)
    {
        // 只能导出自己的AI调用日志，管理员可以导出所有
        if (!isAdmin())
        {
            auditAiCallLog.setUserId(getUserId());
        }
        List<AuditAiCallLog> list = auditAiCallLogService.selectAuditAiCallLogList(auditAiCallLog);
        ExcelUtil<AuditAiCallLog> util = new ExcelUtil<AuditAiCallLog>(AuditAiCallLog.class);
        util.exportExcel(response, list, "AI调用日志");
    }

    /**
     * 获取AI调用日志详细信息
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:query')")
    @GetMapping("/aiCall/{id}")
    public AjaxResult getAiCallInfo(@PathVariable("id") Long id)
    {
        AuditAiCallLog log = auditAiCallLogService.selectAuditAiCallLogById(id);
        // 数据隔离检查
        if (log != null && !isAdmin() && !log.getUserId().equals(getUserId()))
        {
            return error("无权访问此日志");
        }
        return success(log);
    }

    /**
     * 删除AI调用日志
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:remove')")
    @Log(title = "AI调用日志", businessType = BusinessType.DELETE)
    @DeleteMapping("/aiCalls/{ids}")
    public AjaxResult removeAiCalls(@PathVariable Long[] ids)
    {
        // 数据隔离检查
        if (!isAdmin())
        {
            for (Long id : ids)
            {
                AuditAiCallLog log = auditAiCallLogService.selectAuditAiCallLogById(id);
                if (log != null && !log.getUserId().equals(getUserId()))
                {
                    return error("无权删除日志 ID: " + id);
                }
            }
        }
        return toAjax(auditAiCallLogService.deleteAuditAiCallLogByIds(ids));
    }

    /**
     * 获取审计统计信息
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:query')")
    @GetMapping("/statistics")
    public AjaxResult getStatistics(
            @RequestParam(required = false) String type,
            @RequestParam(required = false) String beginTime,
            @RequestParam(required = false) String endTime)
    {
        Map<String, Object> result = new HashMap<>();

        Map<String, Object> params = new HashMap<>();
        if (!isAdmin())
        {
            params.put("userId", getUserId());
        }
        if (beginTime != null && !beginTime.isEmpty())
        {
            params.put("beginTime", beginTime);
        }
        if (endTime != null && !endTime.isEmpty())
        {
            params.put("endTime", endTime);
        }

        // 操作日志统计
        Map<String, Object> operationStats = auditOperationLogService.selectOperationStatistics(params);
        result.put("operationStatistics", operationStats);

        // 策略触发统计
        Map<String, Object> triggerStats = auditStrategyTriggerService.selectTriggerStatistics(params);
        result.put("triggerStatistics", triggerStats);

        // AI调用统计
        Map<String, Object> aiCallStats = auditAiCallLogService.selectAiCallStatistics(params);
        result.put("aiCallStatistics", aiCallStats);

        // 如果指定了类型，返回更详细的统计
        if ("operation".equals(type))
        {
            if (!isAdmin())
            {
                result.put("userOperationStats", auditOperationLogService.selectUserOperationStatistics(getUserId()));
            }
        }
        else if ("trigger".equals(type))
        {
            if (!isAdmin())
            {
                result.put("userTriggerStats", auditStrategyTriggerService.selectUserTriggerStatistics(getUserId()));
            }
        }
        else if ("aiCall".equals(type))
        {
            if (!isAdmin())
            {
                result.put("userAiCallStats", auditAiCallLogService.selectUserAiCallStatistics(getUserId()));
            }
            // 添加Token消耗趋势
            List<Map<String, Object>> tokenTrend = auditAiCallLogService.selectDailyTokenTrend(params);
            result.put("tokenTrend", tokenTrend);

            // 添加成本统计
            Map<String, Object> costStats = auditAiCallLogService.selectCostStatistics(params);
            result.put("costStatistics", costStats);
        }

        return success(result);
    }

    /**
     * 获取综合统计信息（仪表盘用）
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:query')")
    @GetMapping("/dashboard")
    public AjaxResult getDashboardStatistics()
    {
        Map<String, Object> result = new HashMap<>();

        // 默认统计最近30天
        String endTime = DateUtils.getDate();
        String beginTime = DateUtils.parseDateToStr(DateUtils.YYYY_MM_DD, DateUtils.addDays(new Date(), -30));

        Map<String, Object> params = new HashMap<>();
        if (!isAdmin())
        {
            params.put("userId", getUserId());
        }
        params.put("beginTime", beginTime);
        params.put("endTime", endTime);

        // 操作日志统计
        Map<String, Object> operationStats = auditOperationLogService.selectOperationStatistics(params);
        result.put("operationStats", operationStats);

        // 策略触发统计
        Map<String, Object> triggerStats = auditStrategyTriggerService.selectTriggerStatistics(params);
        result.put("triggerStats", triggerStats);

        // AI调用统计
        Map<String, Object> aiCallStats = auditAiCallLogService.selectAiCallStatistics(params);
        result.put("aiCallStats", aiCallStats);

        // Token消耗趋势（最近30天）
        List<Map<String, Object>> tokenTrend = auditAiCallLogService.selectDailyTokenTrend(params);
        result.put("tokenTrend", tokenTrend);

        return success(result);
    }

    /**
     * 清理过期日志（管理员功能）
     */
    @PreAuthorize("@ss.hasPermi('dca:audit:clean')")
    @Log(title = "清理过期日志", businessType = BusinessType.CLEAN)
    @PostMapping("/clean")
    public AjaxResult cleanExpiredLogs(
            @RequestParam(defaultValue = "90") Integer days,
            @RequestParam String logType)
    {
        if (!isAdmin())
        {
            return error("只有管理员才能清理日志");
        }

        int count = 0;
        switch (logType)
        {
            case "operation":
                count = auditOperationLogService.cleanExpiredLogs(days);
                break;
            case "trigger":
                count = auditStrategyTriggerService.cleanExpiredLogs(days);
                break;
            case "aiCall":
                count = auditAiCallLogService.cleanExpiredLogs(days);
                break;
            case "all":
                count += auditOperationLogService.cleanExpiredLogs(days);
                count += auditStrategyTriggerService.cleanExpiredLogs(days);
                count += auditAiCallLogService.cleanExpiredLogs(days);
                break;
            default:
                return error("无效的日志类型");
        }

        return success("成功清理 " + count + " 条" + days + "天前的过期日志");
    }

    /**
     * 判断是否是管理员
     */
    private boolean isAdmin()
    {
        // 获取当前用户
        com.ruoyi.common.core.domain.entity.SysUser user = com.ruoyi.common.utils.SecurityUtils.getLoginUser().getUser();
        // 检查用户是否是管理员角色
        return user != null && user.getUserId() == 1L;
    }
}
