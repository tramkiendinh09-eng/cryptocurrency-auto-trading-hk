package com.ruoyi.dca.controller.trade;

import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.dca.domain.trade.TradeAgentProfile;
import com.ruoyi.dca.service.trade.ITradeAgentProfileService;
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
@RequestMapping("/dca/trade/agent-profile")
public class TradeAgentProfileController extends BaseController {

    @Autowired
    private ITradeAgentProfileService tradeAgentProfileService;

    @PreAuthorize("@ss.hasPermi('dca:tradeAgentProfile:list')")
    @GetMapping("/list")
    public TableDataInfo list(TradeAgentProfile query) {
        startPage();
        return getDataTable(tradeAgentProfileService.selectTradeAgentProfileList(query));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradeAgentProfile:add')")
    @PostMapping
    public AjaxResult add(@RequestBody TradeAgentProfile tradeAgentProfile) {
        return toAjax(tradeAgentProfileService.insertTradeAgentProfile(tradeAgentProfile));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradeAgentProfile:edit')")
    @PutMapping
    public AjaxResult edit(@RequestBody TradeAgentProfile tradeAgentProfile) {
        return toAjax(tradeAgentProfileService.updateTradeAgentProfile(tradeAgentProfile));
    }

    @PreAuthorize("@ss.hasPermi('dca:tradeAgentProfile:remove')")
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(tradeAgentProfileService.deleteTradeAgentProfileByIds(ids));
    }
}
