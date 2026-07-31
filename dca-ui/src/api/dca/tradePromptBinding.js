import request from '@/utils/request'

/**
 * 提示词绑定API模块
 * 提供提示词绑定配置的接口调用
 */

/**
 * 查询提示词绑定列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listTradePromptBinding(query) {
  return request({
    url: '/dca/trade/prompt-binding/list',
    method: 'get',
    params: query
  })
}

/**
 * 新增提示词绑定
 * @param {Object} data - 绑定数据
 * @returns {Promise} 请求Promise
 */
export function addTradePromptBinding(data) {
  return request({
    url: '/dca/trade/prompt-binding',
    method: 'post',
    data
  })
}

/**
 * 修改提示词绑定
 * @param {Object} data - 绑定数据
 * @returns {Promise} 请求Promise
 */
export function updateTradePromptBinding(data) {
  return request({
    url: '/dca/trade/prompt-binding',
    method: 'put',
    data
  })
}

/**
 * 删除提示词绑定
 * @param {string} ids - 绑定ID列表，逗号分隔
 * @returns {Promise} 请求Promise
 */
export function delTradePromptBinding(ids) {
  return request({
    url: `/dca/trade/prompt-binding/${ids}`,
    method: 'delete'
  })
}
