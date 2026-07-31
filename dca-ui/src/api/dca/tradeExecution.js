import request from '@/utils/request'

/**
 * 交易执行API模块
 * 提供交易执行数据相关的接口调用
 */

/**
 * 查询运行时订单列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listRuntimeOrders(query) {
  return request({
    url: '/dca/trade/execution/orders',
    method: 'get',
    params: query
  })
}

/**
 * 查询运行时持仓列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listRuntimePositions(query) {
  return request({
    url: '/dca/trade/execution/positions',
    method: 'get',
    params: query
  })
}

/**
 * 查询运行时成交列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listRuntimeFills(query) {
  return request({
    url: '/dca/trade/execution/fills',
    method: 'get',
    params: query
  })
}

/**
 * 查询运行时风控触发记录列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listRuntimeRiskHits(query) {
  return request({
    url: '/dca/trade/execution/risk-hits',
    method: 'get',
    params: query
  })
}

