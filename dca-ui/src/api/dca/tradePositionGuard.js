import request from '@/utils/request'

/**
 * 持仓风控API模块
 * 提供持仓风控规则的接口调用
 */

/**
 * 查询持仓风控规则列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listTradePositionGuard(query) {
  return request({
    url: '/dca/trade/position-guard/list',
    method: 'get',
    params: query
  })
}

/**
 * 新增持仓风控规则
 * @param {Object} data - 风控规则数据
 * @returns {Promise} 请求Promise
 */
export function addTradePositionGuard(data) {
  return request({
    url: '/dca/trade/position-guard',
    method: 'post',
    data
  })
}

/**
 * 修改持仓风控规则
 * @param {Object} data - 风控规则数据
 * @returns {Promise} 请求Promise
 */
export function updateTradePositionGuard(data) {
  return request({
    url: '/dca/trade/position-guard',
    method: 'put',
    data
  })
}

/**
 * 删除持仓风控规则
 * @param {string} ids - 规则ID列表，逗号分隔
 * @returns {Promise} 请求Promise
 */
export function delTradePositionGuard(ids) {
  return request({
    url: `/dca/trade/position-guard/${ids}`,
    method: 'delete'
  })
}
