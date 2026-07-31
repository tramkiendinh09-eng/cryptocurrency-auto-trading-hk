import request from '@/utils/request'

/**
 * 通知策略API模块
 * 提供通知策略配置的接口调用
 */

/**
 * 查询通知策略列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listTradeNotifyPolicy(query) {
  return request({
    url: '/dca/trade/notify-policy/list',
    method: 'get',
    params: query
  })
}

/**
 * 新增通知策略
 * @param {Object} data - 通知策略数据
 * @returns {Promise} 请求Promise
 */
export function addTradeNotifyPolicy(data) {
  return request({
    url: '/dca/trade/notify-policy',
    method: 'post',
    data
  })
}

/**
 * 修改通知策略
 * @param {Object} data - 通知策略数据
 * @returns {Promise} 请求Promise
 */
export function updateTradeNotifyPolicy(data) {
  return request({
    url: '/dca/trade/notify-policy',
    method: 'put',
    data
  })
}

/**
 * 删除通知策略
 * @param {string} ids - 策略ID列表，逗号分隔
 * @returns {Promise} 请求Promise
 */
export function delTradeNotifyPolicy(ids) {
  return request({
    url: `/dca/trade/notify-policy/${ids}`,
    method: 'delete'
  })
}
