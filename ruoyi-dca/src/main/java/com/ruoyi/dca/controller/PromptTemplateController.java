package com.ruoyi.dca.controller;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.dca.domain.PromptTemplate;
import com.ruoyi.dca.service.IPromptTemplateService;

import java.util.List;
import java.util.Map;

/**
 * 提示词模板控制器
 */
@RestController
@RequestMapping("/dca/template")
public class PromptTemplateController extends BaseController {

    @Autowired
    private IPromptTemplateService promptTemplateService;

    @PreAuthorize("@ss.hasPermi('dca:template:list')")
    @GetMapping("/list")
    public TableDataInfo list(PromptTemplate promptTemplate) {
        startPage();
        List<PromptTemplate> list = promptTemplateService.selectPromptTemplateList(promptTemplate);
        return getDataTable(list);
    }

    @PreAuthorize("@ss.hasPermi('dca:template:query')")
    @GetMapping("/{id}")
    public AjaxResult getInfo(@PathVariable Long id) {
        return AjaxResult.success(promptTemplateService.selectPromptTemplateById(id));
    }

    @PreAuthorize("@ss.hasPermi('dca:template:add')")
    @PostMapping
    public AjaxResult add(@Validated @RequestBody PromptTemplate promptTemplate) {
        return toAjax(promptTemplateService.insertPromptTemplate(promptTemplate));
    }

    @PreAuthorize("@ss.hasPermi('dca:template:edit')")
    @PutMapping
    public AjaxResult edit(@Validated @RequestBody PromptTemplate promptTemplate) {
        return toAjax(promptTemplateService.updatePromptTemplate(promptTemplate));
    }

    @PreAuthorize("@ss.hasPermi('dca:template:remove')")
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(promptTemplateService.deletePromptTemplateByIds(ids));
    }

    @Anonymous
    @GetMapping("/code/{code}")
    public AjaxResult getTemplateByCode(@PathVariable String code) {
        return AjaxResult.success(promptTemplateService.selectTemplateByCode(code));
    }

    @PostMapping("/render")
    public AjaxResult renderTemplate(@RequestParam String templateCode, @RequestBody Map<String, Object> variables) {
        try {
            String result = promptTemplateService.renderTemplate(templateCode, variables);
            return AjaxResult.success(result);
        } catch (Exception e) {
            return AjaxResult.error("模板渲染失败: " + e.getMessage());
        }
    }

    @PreAuthorize("@ss.hasPermi('dca:template:edit')")
    @PostMapping("/{id}/newVersion")
    public AjaxResult createNewVersion(@PathVariable Long id) {
        return toAjax(promptTemplateService.createNewVersion(id));
    }

    @GetMapping("/versions/{code}")
    public AjaxResult getVersions(@PathVariable String code) {
        return AjaxResult.success(promptTemplateService.selectTemplateVersions(code));
    }

    @PreAuthorize("@ss.hasPermi('dca:template:edit')")
    @PutMapping("/{id}/toggle")
    public AjaxResult toggleTemplate(@PathVariable Long id, @RequestParam Integer isActive) {
        return toAjax(promptTemplateService.updateTemplateStatus(id, isActive));
    }
}
