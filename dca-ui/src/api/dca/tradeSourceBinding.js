import request from '@/utils/request'

/**
 * 数据源绑定API模块
 * 提供数据源绑定配置的接口调用
 */

/**
 * 查询数据源绑定列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listTradeSourceBinding(query) {
  return request({
    url: '/dca/trade/source-binding/list',
    method: 'get',
    params: query
  })
}

/**
 * 新增数据源绑定
 * @param {Object} data - 绑定数据
 * @returns {Promise} 请求Promise
 */
export function addTradeSourceBinding(data) {
  return request({
    url: '/dca/trade/source-binding',
    method: 'post',
    data
  })
}

/**
 * 修改数据源绑定
 * @param {Object} data - 绑定数据
 * @returns {Promise} 请求Promise
 */
export function updateTradeSourceBinding(data) {
  return request({
    url: '/dca/trade/source-binding',
    method: 'put',
    data
  })
}

/**
 * 删除数据源绑定
 * @param {string} ids - 绑定ID列表，逗号分隔
 * @returns {Promise} 请求Promise
 */
export function delTradeSourceBinding(ids) {
  return request({
    url: `/dca/trade/source-binding/${ids}`,
    method: 'delete'
  })
}
