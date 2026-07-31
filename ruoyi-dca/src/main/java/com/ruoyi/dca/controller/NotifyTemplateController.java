package com.ruoyi.dca.controller;

import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.dca.domain.NotifyTemplate;
import com.ruoyi.dca.service.INotifyTemplateService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/dca/notify-template")
public class NotifyTemplateController extends BaseController {

    @Autowired
    private INotifyTemplateService notifyTemplateService;

    @PreAuthorize("@ss.hasPermi('dca:notifyTemplate:list')")
    @GetMapping("/list")
    public TableDataInfo list(NotifyTemplate notifyTemplate) {
        startPage();
        List<NotifyTemplate> list = notifyTemplateService.selectNotifyTemplateList(notifyTemplate);
        return getDataTable(list);
    }

    @PreAuthorize("@ss.hasPermi('dca:notifyTemplate:query')")
    @GetMapping("/{id}")
    public AjaxResult getInfo(@PathVariable Long id) {
        return AjaxResult.success(notifyTemplateService.selectNotifyTemplateById(id));
    }

    @GetMapping("/code/{code}")
    public AjaxResult getByCode(@PathVariable String code) {
        return AjaxResult.success(notifyTemplateService.selectNotifyTemplateByCode(code));
    }

    @PreAuthorize("@ss.hasPermi('dca:notifyTemplate:add')")
    @PostMapping
    public AjaxResult add(@Validated @RequestBody NotifyTemplate notifyTemplate) {
        return toAjax(notifyTemplateService.insertNotifyTemplate(notifyTemplate));
    }

    @PreAuthorize("@ss.hasPermi('dca:notifyTemplate:edit')")
    @PutMapping
    public AjaxResult edit(@Validated @RequestBody NotifyTemplate notifyTemplate) {
        return toAjax(notifyTemplateService.updateNotifyTemplate(notifyTemplate));
    }

    @PreAuthorize("@ss.hasPermi('dca:notifyTemplate:remove')")
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(notifyTemplateService.deleteNotifyTemplateByIds(ids));
    }
}
