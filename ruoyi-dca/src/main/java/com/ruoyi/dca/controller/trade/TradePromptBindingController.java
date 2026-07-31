package com.ruoyi.dca.controller.trade;

import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.dca.domain.trade.TradePromptBinding;
import com.ruoyi.dca.service.trade.ITradePromptBindingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/dca/trade/prompt-binding")
public class TradePromptBindingController extends BaseController {

    @Autowired
    private ITradePromptBindingService tradePromptBindingService;

    @PreAuthorize("@ss.hasPermi('dca:tradePromptBinding:list')")
    @GetMapping("/list")
    public TableDataInfo list(TradePromptBinding query) {
        startPage();
        return getDataTable(tradePromptBindingService.selectTradePromptBindingList(query));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradePromptBinding:add')")
    @PostMapping
    public AjaxResult add(@RequestBody TradePromptBinding tradePromptBinding) {
        return toAjax(tradePromptBindingService.insertTradePromptBinding(tradePromptBinding));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradePromptBinding:edit')")
    @PutMapping
    public AjaxResult edit(@RequestBody TradePromptBinding tradePromptBinding) {
        return toAjax(tradePromptBindingService.updateTradePromptBinding(tradePromptBinding));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradePromptBinding:remove')")
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(tradePromptBindingService.deleteTradePromptBindingByIds(ids));
    }
}
