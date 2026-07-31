package com.ruoyi.dca.controller;

import java.util.List;
import java.util.Map;
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
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.common.utils.poi.ExcelUtil;
import com.ruoyi.dca.domain.CardKey;
import com.ruoyi.dca.domain.dto.CardActivateDTO;
import com.ruoyi.dca.domain.dto.CardKeyBatchDTO;
import com.ruoyi.dca.domain.vo.CardUsageVO;
import com.ruoyi.dca.service.ICardKeyService;

/**
 * 卡密Controller
 *
 * @author ruoyi
 * @date 2026-04-02
 */
@RestController
@RequestMapping("/dca/card")
public class CardKeyController extends BaseController {
    @Autowired
    private ICardKeyService cardKeyService;

    /**
     * 查询卡密列表
     */
    @PreAuthorize("@ss.hasPermi('dca:card:list')")
    @GetMapping("/list")
    public TableDataInfo list(CardKey cardKey) {
        startPage();
        List<CardKey> list = cardKeyService.selectCardKeyList(cardKey);
        return getDataTable(list);
    }

    /**
     * 根据批次号查询卡密列表
     */
    @PreAuthorize("@ss.hasPermi('dca:card:list')")
    @GetMapping("/batch/{batchNo}")
    public AjaxResult listByBatchNo(@PathVariable String batchNo) {
        List<CardKey> list = cardKeyService.selectByBatchNo(batchNo);
        return success(list);
    }

    /**
     * 导出卡密列表
     */
    @PreAuthorize("@ss.hasPermi('dca:card:export')")
    @Log(title = "卡密", businessType = BusinessType.EXPORT)
    @PostMapping("/export")
    public void export(HttpServletResponse response, CardKey cardKey) {
        List<CardKey> list = cardKeyService.selectCardKeyList(cardKey);
        ExcelUtil<CardKey> util = new ExcelUtil<CardKey>(CardKey.class);
        util.exportExcel(response, list, "卡密数据");
    }

    /**
     * 获取卡密详细信息
     */
    @PreAuthorize("@ss.hasPermi('dca:card:query')")
    @GetMapping(value = "/{id}")
    public AjaxResult getInfo(@PathVariable("id") Long id) {
        return success(cardKeyService.selectCardKeyById(id));
    }

    /**
     * 根据卡密查询详情
     */
    @PreAuthorize("@ss.hasPermi('dca:card:query')")
    @GetMapping("/key/{cardKey}")
    public AjaxResult getByCardKey(@PathVariable String cardKey) {
        CardKey cardKeyEntity = cardKeyService.selectByCardKey(cardKey);
        if (cardKeyEntity == null) {
            return error("卡密不存在");
        }
        return success(cardKeyEntity);
    }

    /**
     * 批量生成卡密
     */
    @PreAuthorize("@ss.hasPermi('dca:card:generate')")
    @Log(title = "卡密", businessType = BusinessType.INSERT)
    @PostMapping("/generate")
    public AjaxResult generate(@Validated @RequestBody CardKeyBatchDTO batchDto) {
        try {
            List<CardKey> cardKeys = cardKeyService.generateCards(batchDto);
            return success(cardKeys);
        } catch (Exception e) {
            logger.error("生成卡密失败", e);
            return error("生成卡密失败: " + e.getMessage());
        }
    }

    /**
     * 激活卡密
     */
    @Log(title = "卡密", businessType = BusinessType.UPDATE)
    @PostMapping("/activate")
    public AjaxResult activate(@Validated @RequestBody CardActivateDTO dto) {
        try {
            CardKey cardKey = cardKeyService.activateCard(dto);
            return success(cardKey);
        } catch (Exception e) {
            logger.error("激活卡密失败", e);
            return error(e.getMessage());
        }
    }

    /**
     * 验证卡密有效性
     */
    @PostMapping("/validate")
    public AjaxResult validate(@RequestParam String cardKey) {
        Map<String, Object> result = cardKeyService.validateCard(cardKey);
        return success(result);
    }

    /**
     * 检查用户卡密是否过期
     */
    @GetMapping("/checkExpire")
    public AjaxResult checkExpire(@RequestParam Long userId) {
        boolean expired = cardKeyService.checkExpire(userId);
        return success(expired);
    }

    /**
     * 获取卡密使用统计
     */
    @PreAuthorize("@ss.hasPermi('dca:card:query')")
    @GetMapping("/usage/{id}")
    public AjaxResult getUsage(@PathVariable("id") Long id) {
        CardUsageVO usage = cardKeyService.getCardUsage(id);
        return success(usage);
    }

    /**
     * 绑定机器码
     */
    @PreAuthorize("@ss.hasPermi('dca:card:edit')")
    @Log(title = "卡密", businessType = BusinessType.UPDATE)
    @PutMapping("/bindMachine")
    public AjaxResult bindMachine(@RequestParam Long cardId, @RequestParam String machineCode) {
        int rows = cardKeyService.bindMachine(cardId, machineCode);
        return toAjax(rows);
    }

    /**
     * 解绑用户
     */
    @PreAuthorize("@ss.hasPermi('dca:card:edit')")
    @Log(title = "卡密", businessType = BusinessType.UPDATE)
    @PutMapping("/unbindUser")
    public AjaxResult unbindUser(@RequestParam Long userId) {
        int rows = cardKeyService.unbindUser(userId);
        return toAjax(rows);
    }

    /**
     * 新增卡密
     */
    @PreAuthorize("@ss.hasPermi('dca:card:add')")
    @Log(title = "卡密", businessType = BusinessType.INSERT)
    @PostMapping
    public AjaxResult add(@Validated @RequestBody CardKey cardKey) {
        return toAjax(cardKeyService.insertCardKey(cardKey));
    }

    /**
     * 修改卡密
     */
    @PreAuthorize("@ss.hasPermi('dca:card:edit')")
    @Log(title = "卡密", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult edit(@Validated @RequestBody CardKey cardKey) {
        return toAjax(cardKeyService.updateCardKey(cardKey));
    }

    /**
     * 删除卡密
     */
    @PreAuthorize("@ss.hasPermi('dca:card:remove')")
    @Log(title = "卡密", businessType = BusinessType.DELETE)
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(cardKeyService.deleteCardKeyByIds(ids));
    }

    /**
     * 禁用卡密
     */
    @PreAuthorize("@ss.hasPermi('dca:card:edit')")
    @Log(title = "卡密", businessType = BusinessType.UPDATE)
    @PostMapping("/{id}/disable")
    public AjaxResult disable(@PathVariable Long id) {
        int rows = cardKeyService.disableCard(id);
        return toAjax(rows);
    }

    /**
     * 启用卡密
     */
    @PreAuthorize("@ss.hasPermi('dca:card:edit')")
    @Log(title = "卡密", businessType = BusinessType.UPDATE)
    @PostMapping("/{id}/enable")
    public AjaxResult enable(@PathVariable Long id) {
        int rows = cardKeyService.enableCard(id);
        return toAjax(rows);
    }

    /**
     * 查询即将过期的卡密
     */
    @PreAuthorize("@ss.hasPermi('dca:card:list')")
    @GetMapping("/expiring")
    public AjaxResult getExpiringCards(@RequestParam(defaultValue = "7") Integer days) {
        List<CardKey> list = cardKeyService.selectExpiringCards(days);
        return success(list);
    }

    /**
     * 查询已过期的卡密
     */
    @PreAuthorize("@ss.hasPermi('dca:card:list')")
    @GetMapping("/expired")
    public AjaxResult getExpiredCards() {
        List<CardKey> list = cardKeyService.selectExpiredCards();
        return success(list);
    }

    /**
     * 批量更新过期卡密状态
     */
    @PreAuthorize("@ss.hasPermi('dca:card:edit')")
    @Log(title = "卡密", businessType = BusinessType.UPDATE)
    @PostMapping("/updateExpired")
    public AjaxResult updateExpiredStatus() {
        int rows = cardKeyService.batchUpdateExpiredStatus();
        return success("更新成功，共 " + rows + " 条");
    }

    /**
     * 获取状态统计
     */
    @PreAuthorize("@ss.hasPermi('dca:card:list')")
    @GetMapping("/stats/status")
    public AjaxResult getStatusStatistics() {
        Map<String, Object> stats = cardKeyService.getStatusStatistics();
        return success(stats);
    }

    /**
     * 获取类型统计
     */
    @PreAuthorize("@ss.hasPermi('dca:card:list')")
    @GetMapping("/stats/type")
    public AjaxResult getTypeStatistics() {
        Map<String, Object> stats = cardKeyService.getTypeStatistics();
        return success(stats);
    }

    /**
     * 获取卡密统计概览
     */
    @PreAuthorize("@ss.hasPermi('dca:card:list')")
    @GetMapping("/overview")
    public AjaxResult getOverview() {
        Map<String, Object> overview = cardKeyService.getCardOverview();
        return success(overview);
    }

    /**
     * 我的卡密（用户端）
     */
    @GetMapping("/my")
    public AjaxResult getMyCard(@RequestParam Long userId) {
        CardKey cardKey = cardKeyService.selectByUserId(userId);
        if (cardKey == null) {
            return error("未找到激活的卡密");
        }
        return success(cardKey);
    }

    /**
     * 验证我的卡密（用户端）
     */
    @GetMapping("/my/validate")
    public AjaxResult validateMyCard(@RequestParam Long userId) {
        CardKey cardKey = cardKeyService.selectByUserId(userId);
        if (cardKey == null) {
            return error("未找到激活的卡密");
        }

        Map<String, Object> result = cardKeyService.validateCard(cardKey.getCardKey());
        return success(result);
    }

    /**
     * 刷新卡密验证缓存
     */
    @GetMapping("/refresh/{cardKey}")
    public AjaxResult refreshValidation(@PathVariable String cardKey) {
        // 清除验证缓存，下次访问会重新验证
        String cacheKey = "card_validate:" + cardKey;
        // redisCache.deleteObject(cacheKey); // 需要注入 RedisCache
        return success("刷新成功");
    }
}
