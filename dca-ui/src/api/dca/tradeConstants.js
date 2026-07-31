import request from '@/utils/request'

/**
 * 交易系统常量API模块
 * 提供获取系统常量的接口，避免前端硬编码
 */

/**
 * 获取所有交易系统常量配置
 * @returns {Promise} 请求Promise
 */
export function getTradeConstants() {
  return request({
    url: '/dca/trade/constants/all',
    method: 'get'
  })
}

/**
 * 获取支持的交易所列表
 * @returns {Promise} 请求Promise
 */
export function getExchanges() {
  return request({
    url: '/dca/trade/constants/exchanges',
    method: 'get'
  })
}

/**
 * 获取支持的交易对列表
 * @returns {Promise} 请求Promise
 */
export function getSymbols() {
  return request({
    url: '/dca/trade/constants/symbols',
    method: 'get'
  })
}

/**
 * 获取支持的运行模式列表
 * @returns {Promise} 请求Promise
 */
export function getModes() {
  return request({
    url: '/dca/trade/constants/modes',
    method: 'get'
  })
}
