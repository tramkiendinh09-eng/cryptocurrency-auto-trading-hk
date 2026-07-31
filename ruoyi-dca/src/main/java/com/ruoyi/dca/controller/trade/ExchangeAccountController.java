package com.ruoyi.dca.controller.trade;

import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.dca.domain.trade.ExchangeAccount;
import com.ruoyi.dca.service.trade.IExchangeAccountService;
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

/**
 * 交易所账户控制器
 * 提供交易所账户的增删改查等RESTful API接口
 *
 * @author ruoyi-dca
 */
@RestController
@RequestMapping("/dca/trade/account")
public class ExchangeAccountController extends BaseController {

    @Autowired
    private IExchangeAccountService exchangeAccountService;

    /**
     * 查询交易所账户列表
     *
     * @param query 查询条件
     * @return 分页数据
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeAccount:list')")
    @GetMapping("/list")
    public TableDataInfo list(ExchangeAccount query) {
        startPage();
        return getDataTable(exchangeAccountService.selectExchangeAccountList(query));
    }

    /**
     * 新增交易所账户
     *
     * @param exchangeAccount 交易所账户
     * @return 操作结果
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeAccount:add')")
    @PostMapping
    public AjaxResult add(@RequestBody ExchangeAccount exchangeAccount) {
        return toAjax(exchangeAccountService.insertExchangeAccount(exchangeAccount));
    }

    /**
     * 修改交易所账户
     *
     * @param exchangeAccount 交易所账户
     * @return 操作结果
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeAccount:edit')")
    @PutMapping
    public AjaxResult edit(@RequestBody ExchangeAccount exchangeAccount) {
        return toAjax(exchangeAccountService.updateExchangeAccount(exchangeAccount));
    }

    /**
     * 删除交易所账户
     *
     * @param ids 账户ID数组
     * @return 操作结果
     */
    @PreAuthorize("@ss.hasPermi('dca:tradeAccount:remove')")
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(exchangeAccountService.deleteExchangeAccountByIds(ids));
    }
}
