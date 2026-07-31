package com.ruoyi.dca.controller.trade;

import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.dca.domain.trade.TradePositionGuard;
import com.ruoyi.dca.service.trade.ITradePositionGuardService;
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
@RequestMapping("/dca/trade/position-guard")
public class TradePositionGuardController extends BaseController {

    @Autowired
    private ITradePositionGuardService tradePositionGuardService;

    @PreAuthorize("@ss.hasPermi('dca:tradePositionGuard:list')")
    @GetMapping("/list")
    public TableDataInfo list(TradePositionGuard query) {
        startPage();
        return getDataTable(tradePositionGuardService.selectTradePositionGuardList(query));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradePositionGuard:add')")
    @PostMapping
    public AjaxResult add(@RequestBody TradePositionGuard tradePositionGuard) {
        return toAjax(tradePositionGuardService.insertTradePositionGuard(tradePositionGuard));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradePositionGuard:edit')")
    @PutMapping
    public AjaxResult edit(@RequestBody TradePositionGuard tradePositionGuard) {
        return toAjax(tradePositionGuardService.updateTradePositionGuard(tradePositionGuard));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradePositionGuard:remove')")
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(tradePositionGuardService.deleteTradePositionGuardByIds(ids));
    }
}
