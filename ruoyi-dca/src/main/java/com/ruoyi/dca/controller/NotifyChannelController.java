package com.ruoyi.dca.controller;

import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.common.utils.poi.ExcelUtil;
import com.ruoyi.dca.domain.NotifyChannel;
import com.ruoyi.dca.service.INotifyChannelService;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 通知渠道 Controller
 *
 * 修复点：新增渠道时强制写入当前登录用户，避免插入 user_id 为空的数据。
 */
@RestController
@RequestMapping("/dca/notify/channels")
public class NotifyChannelController extends BaseController {
    @Autowired
    private INotifyChannelService notifyChannelService;

    /**
     * 查询通知渠道列表
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:list')")
    @GetMapping("/list")
    public TableDataInfo list(NotifyChannel notifyChannel) {
        startPage();
        List<NotifyChannel> list = notifyChannelService.selectNotifyChannelList(notifyChannel);
        return getDataTable(list);
    }

    /**
     * 导出通知渠道列表
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:export')")
    @Log(title = "通知渠道", businessType = BusinessType.EXPORT)
    @PostMapping("/export")
    public void export(HttpServletResponse response, NotifyChannel notifyChannel) {
        List<NotifyChannel> list = notifyChannelService.selectNotifyChannelList(notifyChannel);
        ExcelUtil<NotifyChannel> util = new ExcelUtil<>(NotifyChannel.class);
        util.exportExcel(response, list, "通知渠道数据");
    }

    /**
     * 获取通知渠道详情
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:query')")
    @GetMapping("/{id}")
    public AjaxResult getInfo(@PathVariable("id") Long id) {
        return success(notifyChannelService.selectNotifyChannelById(id));
    }

    /**
     * 根据用户 ID 获取已启用渠道
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:query')")
    @GetMapping("/user/{userId}")
    public AjaxResult getByUserId(@PathVariable("userId") Long userId) {
        List<NotifyChannel> list = notifyChannelService.selectEnabledByUserId(userId);
        return success(list);
    }

    /**
     * 获取全部已启用渠道
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:query')")
    @GetMapping("/enabled")
    public AjaxResult getEnabled() {
        List<NotifyChannel> list = notifyChannelService.selectAllEnabled();
        return success(list);
    }

    /**
     * 新增通知渠道
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:add')")
    @Log(title = "通知渠道", businessType = BusinessType.INSERT)
    @PostMapping
    public AjaxResult add(@Validated @RequestBody NotifyChannel notifyChannel) {
        notifyChannel.setUserId(getUserId());
        notifyChannel.setCreateBy(getUsername());
        return toAjax(notifyChannelService.insertNotifyChannel(notifyChannel));
    }

    /**
     * 修改通知渠道
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:edit')")
    @Log(title = "通知渠道", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult edit(@Validated @RequestBody NotifyChannel notifyChannel) {
        return toAjax(notifyChannelService.updateNotifyChannel(notifyChannel));
    }

    /**
     * 删除通知渠道
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:remove')")
    @Log(title = "通知渠道", businessType = BusinessType.DELETE)
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(notifyChannelService.deleteNotifyChannelByIds(ids));
    }

    /**
     * 修改渠道启用状态
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:edit')")
    @Log(title = "通知渠道", businessType = BusinessType.UPDATE)
    @PutMapping("/{id}/status")
    public AjaxResult updateStatus(@PathVariable Long id, @RequestParam Integer isEnabled) {
        int rows = notifyChannelService.updateEnabledStatus(id, isEnabled);
        return toAjax(rows);
    }

    /**
     * 批量修改渠道启用状态
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:edit')")
    @Log(title = "通知渠道", businessType = BusinessType.UPDATE)
    @PutMapping("/batchStatus")
    public AjaxResult batchUpdateStatus(@RequestBody Map<String, Object> params) {
        @SuppressWarnings("unchecked")
        List<Long> ids = (List<Long>) params.get("ids");
        Integer isEnabled = (Integer) params.get("isEnabled");
        int rows = notifyChannelService.batchUpdateEnabledStatus(ids, isEnabled);
        return toAjax(rows);
    }

    /**
     * 测试发送
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:edit')")
    @Log(title = "测试发送", businessType = BusinessType.OTHER)
    @PostMapping("/{id}/test")
    public AjaxResult testSend(@PathVariable Long id) {
        try {
            Map<String, Object> result = notifyChannelService.testSend(id);
            return success(result);
        } catch (Exception e) {
            logger.error("测试发送失败", e);
            return error("测试发送失败: " + e.getMessage());
        }
    }

    /**
     * 测试邮件连接
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:edit')")
    @Log(title = "测试邮件连接", businessType = BusinessType.OTHER)
    @PostMapping("/{id}/testConnection")
    public AjaxResult testConnection(@PathVariable Long id) {
        try {
            boolean success = notifyChannelService.testMailConnection(id);
            return success(success ? "SMTP连接测试成功" : "SMTP连接测试失败");
        } catch (Exception e) {
            logger.error("测试邮件连接失败", e);
            return error("测试连接失败: " + e.getMessage());
        }
    }

    /**
     * 验证渠道配置
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:query')")
    @PostMapping("/validate")
    public AjaxResult validate(@RequestBody NotifyChannel notifyChannel) {
        Map<String, Object> result = notifyChannelService.validateChannel(notifyChannel);
        return success(result);
    }

    /**
     * 检查渠道名称唯一性
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:query')")
    @GetMapping("/checkUnique")
    public AjaxResult checkUnique(@RequestParam String channelName, @RequestParam(required = false) Long userId) {
        NotifyChannel notifyChannel = new NotifyChannel();
        notifyChannel.setChannelName(channelName);
        notifyChannel.setUserId(userId != null ? userId : getUserId());
        boolean unique = notifyChannelService.checkChannelNameUnique(notifyChannel);
        return success(unique);
    }

    /**
     * 获取类型统计
     */
    @PreAuthorize("@ss.hasPermi('dca:notify:list')")
    @GetMapping("/stats/type")
    public AjaxResult getTypeStatistics() {
        Map<String, Object> stats = notifyChannelService.getTypeStatistics();
        return success(stats);
    }

    /**
     * 获取支持的渠道类型
     */
    @GetMapping("/channelTypes")
    public AjaxResult getChannelTypes() {
        Map<String, String> channelTypes = Map.of(
                "email", "邮件",
                "telegram", "Telegram Bot",
                "dingtalk", "钉钉",
                "feishu", "飞书",
                "webhook", "自定义Webhook"
        );
        return success(channelTypes);
    }
}