import request from '@/utils/request'

/**
 * 交易所账户API模块
 * 提供交易所账户相关的接口调用
 */

/**
 * 查询交易所账户列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listExchangeAccount(query) {
  return request({
    url: '/dca/trade/account/list',
    method: 'get',
    params: query
  })
}

/**
 * 新增交易所账户
 * @param {Object} data - 账户数据
 * @returns {Promise} 请求Promise
 */
export function addExchangeAccount(data) {
  return request({
    url: '/dca/trade/account',
    method: 'post',
    data
  })
}

/**
 * 修改交易所账户
 * @param {Object} data - 账户数据
 * @returns {Promise} 请求Promise
 */
export function updateExchangeAccount(data) {
  return request({
    url: '/dca/trade/account',
    method: 'put',
    data
  })
}

/**
 * 删除交易所账户
 * @param {string} ids - 账户ID列表，逗号分隔
 * @returns {Promise} 请求Promise
 */
export function delExchangeAccount(ids) {
  return request({
    url: `/dca/trade/account/${ids}`,
    method: 'delete'
  })
}
