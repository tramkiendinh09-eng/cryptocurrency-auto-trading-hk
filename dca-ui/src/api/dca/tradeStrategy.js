import request from '@/utils/request'

/**
 * 交易策略API模块
 * 提供交易策略相关的接口调用
 */

/**
 * 查询交易策略列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listTradeStrategy(query) {
  return request({
    url: '/dca/trade/strategy/list',
    method: 'get',
    params: query
  })
}

/**
 * 获取策略版本列表
 * @param {number|string} strategyId - 策略ID
 * @returns {Promise} 请求Promise
 */
export function listTradeStrategyVersions(strategyId) {
  return request({
    url: `/dca/trade/strategy/${strategyId}/versions`,
    method: 'get'
  })
}

/**
 * 获取策略账户绑定列表
 * @param {number|string} strategyId - 策略ID
 * @returns {Promise} 请求Promise
 */
export function listTradeStrategyBindings(strategyId) {
  return request({
    url: `/dca/trade/strategy/${strategyId}/bindings`,
    method: 'get'
  })
}

/**
 * 新增交易策略
 * @param {Object} data - 策略数据
 * @returns {Promise} 请求Promise
 */
export function addTradeStrategy(data) {
  return request({
    url: '/dca/trade/strategy',
    method: 'post',
    data
  })
}

/**
 * 修改交易策略
 * @param {Object} data - 策略数据
 * @returns {Promise} 请求Promise
 */
export function updateTradeStrategy(data) {
  return request({
    url: '/dca/trade/strategy',
    method: 'put',
    data
  })
}

/**
 * 更新策略账户绑定
 * @param {number|string} strategyId - 策略ID
 * @param {Object} data - 绑定数据
 * @returns {Promise} 请求Promise
 */
export function updateTradeStrategyBindings(strategyId, data) {
  return request({
    url: `/dca/trade/strategy/${strategyId}/bindings`,
    method: 'put',
    data
  })
}

/**
 * 删除交易策略
 * @param {string} ids - 策略ID列表，逗号分隔
 * @returns {Promise} 请求Promise
 */
export function delTradeStrategy(ids) {
  return request({
    url: `/dca/trade/strategy/${ids}`,
    method: 'delete'
  })
}
