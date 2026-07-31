import request from '@/utils/request'

/**
 * 通知模板API模块
 * 提供通知模板配置的接口调用
 */

/**
 * 查询通知模板列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listTradeNotifyTemplate(query) {
  return request({
    url: '/dca/notify-template/list',
    method: 'get',
    params: query
  })
}

/**
 * 获取通知模板详情
 * @param {number} id - 模板ID
 * @returns {Promise} 请求Promise
 */
export function getTradeNotifyTemplate(id) {
  return request({
    url: `/dca/notify-template/${id}`,
    method: 'get'
  })
}

/**
 * 新增通知模板
 * @param {Object} data - 模板数据
 * @returns {Promise} 请求Promise
 */
export function addTradeNotifyTemplate(data) {
  return request({
    url: '/dca/notify-template',
    method: 'post',
    data
  })
}

/**
 * 修改通知模板
 * @param {Object} data - 模板数据
 * @returns {Promise} 请求Promise
 */
export function updateTradeNotifyTemplate(data) {
  return request({
    url: '/dca/notify-template',
    method: 'put',
    data
  })
}

/**
 * 删除通知模板
 * @param {string} ids - 模板ID列表，逗号分隔
 * @returns {Promise} 请求Promise
 */
export function delTradeNotifyTemplate(ids) {
  return request({
    url: `/dca/notify-template/${ids}`,
    method: 'delete'
  })
}
