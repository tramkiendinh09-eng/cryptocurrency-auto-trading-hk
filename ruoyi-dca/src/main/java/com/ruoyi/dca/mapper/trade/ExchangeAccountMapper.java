package com.ruoyi.dca.mapper.trade;

import com.ruoyi.dca.domain.trade.ExchangeAccount;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 交易所账户Mapper接口
 * 提供交易所账户的数据库访问操作
 *
 * @author ruoyi-dca
 */
public interface ExchangeAccountMapper {

    /**
     * 查询交易所账户列表
     *
     * @param query 查询条件
     * @return 账户列表
     */
    List<ExchangeAccount> selectExchangeAccountList(ExchangeAccount query);

    /**
     * 根据ID查询交易所账户
     *
     * @param id 账户ID
     * @return 账户信息
     */
    ExchangeAccount selectExchangeAccountById(@Param("id") Long id);

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
    int deleteExchangeAccountByIds(@Param("ids") Long[] ids);
}
