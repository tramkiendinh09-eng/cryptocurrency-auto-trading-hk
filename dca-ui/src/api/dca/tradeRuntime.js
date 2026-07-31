import request from '@/utils/request'

/**
 * 获取交易运行时配置
 *
 * @returns {Promise} 运行时配置信息
 */
export function getTradeRuntimeConfig() {
  return request({
    url: '/dca/trade/runtime/config',
    method: 'get'
  })
}

/**
 * 更新交易运行时配置
 *
 * @param {Object} data - 配置数据
 * @returns {Promise} 更新结果
 */
export function updateTradeRuntimeConfig(data) {
  return request({
    url: '/dca/trade/runtime/config',
    method: 'put',
    data
  })
}

/**
 * 获取交易运行时概览
 *
 * @returns {Promise} 运行时概览信息，包括状态、指标等
 */
export function getTradeRuntimeOverview() {
  return request({
    url: '/dca/trade/runtime/overview',
    method: 'get'
  })
}

/**
 * 获取仪表盘运行时数据流
 *
 * @returns {Promise} 运行时数据流信息，用于仪表盘展示
 */
export function getDashboardRuntimeFeed() {
  return request({
    url: '/dca/dashboard/runtimeFeed',
    method: 'get'
  })
}
