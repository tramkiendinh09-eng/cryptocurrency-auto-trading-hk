package com.ruoyi.dca.controller.trade;

import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.dca.domain.trade.TradeNotifyPolicy;
import com.ruoyi.dca.service.trade.ITradeNotifyPolicyService;
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
@RequestMapping("/dca/trade/notify-policy")
public class TradeNotifyPolicyController extends BaseController {

    @Autowired
    private ITradeNotifyPolicyService tradeNotifyPolicyService;

    @PreAuthorize("@ss.hasPermi('dca:tradeNotifyPolicy:list')")
    @GetMapping("/list")
    public TableDataInfo list(TradeNotifyPolicy query) {
        startPage();
        return getDataTable(tradeNotifyPolicyService.selectTradeNotifyPolicyList(query));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradeNotifyPolicy:add')")
    @PostMapping
    public AjaxResult add(@RequestBody TradeNotifyPolicy tradeNotifyPolicy) {
        return toAjax(tradeNotifyPolicyService.insertTradeNotifyPolicy(tradeNotifyPolicy));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradeNotifyPolicy:edit')")
    @PutMapping
    public AjaxResult edit(@RequestBody TradeNotifyPolicy tradeNotifyPolicy) {
        return toAjax(tradeNotifyPolicyService.updateTradeNotifyPolicy(tradeNotifyPolicy));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradeNotifyPolicy:remove')")
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(tradeNotifyPolicyService.deleteTradeNotifyPolicyByIds(ids));
    }
}
