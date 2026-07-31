package com.ruoyi.dca.controller.trade;

import java.beans.PropertyEditorSupport;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.utils.StringUtils;
import com.ruoyi.dca.domain.enums.TradeRuntimeMode;
import com.ruoyi.dca.domain.trade.ExchangeAccountBinding;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.service.trade.ITradeStrategyService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.WebDataBinder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.InitBinder;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 交易策略控制器
 * 提供交易策略的增删改查、版本管理、账户绑定等RESTful API接口
 *
 * @author ruoyi-dca
 */
@RestController
@RequestMapping("/dca/trade/strategy")
public class TradeStrategyController extends BaseController {

    @Autowired
    private ITradeStrategyService tradeStrategyService;

    /**
     * 初始化数据绑定器
     * 注册自定义编辑器，用于将字符串转换为TradeRuntimeMode枚举类型
     *
     * @param binder Web数据绑定器
     */
    @InitBinder
    public void initTradeModeBinder(WebDataBinder binder) {
        binder.registerCustomEditor(TradeRuntimeMode.class, new PropertyEditorSupport() {
            @Override
            public void setAsText(String text) {
                if (StringUtils.isEmpty(text)) {
                    setValue(null);
                    return;
                }
                setValue(TradeRuntimeMode.fromCode(text));
            }
        });
    }

    /**
     * 查询交易策略列表
     *
     * @param query 查询条件
     * @return 分页数据
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeStrategy:list')")
    @GetMapping("/list")
    public TableDataInfo list(TradeStrategy query) {
        startPage();
        return getDataTable(tradeStrategyService.selectTradeStrategyList(query));
    }

    /**
     * 获取策略版本列表
     *
     * @param strategyId 策略ID
     * @return 版本列表
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeStrategy:query')")
    @GetMapping("/{strategyId}/versions")
    public AjaxResult versions(@PathVariable Long strategyId) {
        return success(tradeStrategyService.selectTradeStrategyVersions(strategyId));
    }

    /**
     * 获取策略账户绑定列表
     *
     * @param strategyId 策略ID
     * @return 账户绑定列表
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeStrategy:query')")
    @GetMapping("/{strategyId}/bindings")
    public AjaxResult bindings(@PathVariable Long strategyId) {
        return success(tradeStrategyService.selectExchangeAccountBindings(strategyId));
    }

    /**
     * 新增交易策略
     *
     * @param tradeStrategy 交易策略
     * @return 操作结果
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeStrategy:add')")
    @PostMapping
    public AjaxResult add(@RequestBody TradeStrategy tradeStrategy) {
        return toAjax(tradeStrategyService.insertTradeStrategy(tradeStrategy));
    }

    /**
     * 修改交易策略
     *
     * @param tradeStrategy 交易策略
     * @return 操作结果
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeStrategy:edit')")
    @PutMapping
    public AjaxResult edit(@RequestBody TradeStrategy tradeStrategy) {
        return toAjax(tradeStrategyService.updateTradeStrategy(tradeStrategy));
    }

    /**
     * 替换策略账户绑定
     *
     * @param strategyId 策略ID
     * @param bindings 账户绑定列表
     * @return 操作结果
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeStrategy:edit')")
    @PutMapping("/{strategyId}/bindings")
    public AjaxResult replaceBindings(@PathVariable Long strategyId, @RequestBody List<ExchangeAccountBinding> bindings) {
        return toAjax(tradeStrategyService.replaceExchangeAccountBindings(strategyId, bindings));
    }

    /**
     * 删除交易策略
     *
     * @param ids 策略ID数组
     * @return 操作结果
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeStrategy:remove')")
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(tradeStrategyService.deleteTradeStrategyByIds(ids));
    }
}
