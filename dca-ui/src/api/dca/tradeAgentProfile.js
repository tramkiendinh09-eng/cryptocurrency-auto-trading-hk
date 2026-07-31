import request from '@/utils/request'

/**
 * 交易代理配置API模块
 * 提供交易代理配置的接口调用
 */

/**
 * 查询交易代理配置列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listTradeAgentProfile(query) {
  return request({
    url: '/dca/trade/agent-profile/list',
    method: 'get',
    params: query
  })
}

/**
 * 新增交易代理配置
 * @param {Object} data - 代理配置数据
 * @returns {Promise} 请求Promise
 */
export function addTradeAgentProfile(data) {
  return request({
    url: '/dca/trade/agent-profile',
    method: 'post',
    data
  })
}

/**
 * 修改交易代理配置
 * @param {Object} data - 代理配置数据
 * @returns {Promise} 请求Promise
 */
export function updateTradeAgentProfile(data) {
  return request({
    url: '/dca/trade/agent-profile',
    method: 'put',
    data
  })
}

/**
 * 删除交易代理配置
 * @param {string} ids - 配置ID列表，逗号分隔
 * @returns {Promise} 请求Promise
 */
export function delTradeAgentProfile(ids) {
  return request({
    url: `/dca/trade/agent-profile/${ids}`,
    method: 'delete'
  })
}
