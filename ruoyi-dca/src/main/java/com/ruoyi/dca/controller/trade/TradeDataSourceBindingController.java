package com.ruoyi.dca.controller.trade;

import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.dca.domain.trade.TradeDataSourceBinding;
import com.ruoyi.dca.service.trade.ITradeDataSourceBindingService;
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
@RequestMapping("/dca/trade/source-binding")
public class TradeDataSourceBindingController extends BaseController {

    @Autowired
    private ITradeDataSourceBindingService tradeDataSourceBindingService;

    @PreAuthorize("@ss.hasPermi('dca:tradeSourceBinding:list')")
    @GetMapping("/list")
    public TableDataInfo list(TradeDataSourceBinding query) {
        startPage();
        return getDataTable(tradeDataSourceBindingService.selectTradeDataSourceBindingList(query));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradeSourceBinding:add')")
    @PostMapping
    public AjaxResult add(@RequestBody TradeDataSourceBinding tradeDataSourceBinding) {
        return toAjax(tradeDataSourceBindingService.insertTradeDataSourceBinding(tradeDataSourceBinding));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradeSourceBinding:edit')")
    @PutMapping
    public AjaxResult edit(@RequestBody TradeDataSourceBinding tradeDataSourceBinding) {
        return toAjax(tradeDataSourceBindingService.updateTradeDataSourceBinding(tradeDataSourceBinding));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradeSourceBinding:remove')")
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(tradeDataSourceBindingService.deleteTradeDataSourceBindingByIds(ids));
    }
}
