package com.ruoyi.dca.service.trade;

import com.ruoyi.dca.domain.trade.ExchangeAccount;

import java.util.List;

/**
 * 交易所账户服务接口
 * 提供交易所账户的增删改查等业务逻辑
 *
 * @author ruoyi-dca
 */
public interface IExchangeAccountService {

    /**
     * 查询交易所账户列表
     *
     * @param query 查询条件
     * @return 账户列表
     */
    List<ExchangeAccount> selectExchangeAccountList(ExchangeAccount query);

    /**
     * 新增交易所账户
     *
     * @param exchangeAccount 交易所账户
     * @return 影响行数
     */
    int insertExchangeAccount(ExchangeAccount exchangeAccount);

    /**
     * 修改交易所账户
     *
     * @param exchangeAccount 交易所账户
     * @return 影响行数
     */
    int updateExchangeAccount(ExchangeAccount exchangeAccount);

    /**
     * 批量删除交易所账户
     *
     * @param ids 账户ID数组
     * @return 影响行数
     */
    int deleteExchangeAccountByIds(Long[] ids);
}
