import request from '@/utils/request'

/**
 * 通知API模块
 * 提供通知渠道和通知记录的接口调用
 */

/**
 * 查询通知渠道列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listChannel(query) {
  return request({
    url: '/dca/notify/channels/list',
    method: 'get',
    params: query
  })
}

/**
 * 查询已启用的通知渠道列表
 * @returns {Promise} 请求Promise
 */
export function listEnabledChannel() {
  return request({
    url: '/dca/notify/channels/enabled',
    method: 'get'
  })
}

/**
 * 获取通知渠道详情
 * @param {number} id - 渠道ID
 * @returns {Promise} 请求Promise
 */
export function getChannel(id) {
  return request({
    url: '/dca/notify/channels/' + id,
    method: 'get'
  })
}

/**
 * 新增通知渠道
 * @param {Object} data - 渠道数据
 * @returns {Promise} 请求Promise
 */
export function addChannel(data) {
  return request({
    url: '/dca/notify/channels',
    method: 'post',
    data
  })
}

/**
 * 修改通知渠道
 * @param {Object} data - 渠道数据
 * @returns {Promise} 请求Promise
 */
export function updateChannel(data) {
  return request({
    url: '/dca/notify/channels',
    method: 'put',
    data
  })
}

/**
 * 删除通知渠道
 * @param {string} ids - 渠道ID列表，逗号分隔
 * @returns {Promise} 请求Promise
 */
export function delChannel(ids) {
  return request({
    url: '/dca/notify/channels/' + ids,
    method: 'delete'
  })
}

/**
 * 切换通知渠道启用状态
 * @param {number} id - 渠道ID
 * @param {boolean} isEnabled - 是否启用
 * @returns {Promise} 请求Promise
 */
export function toggleChannel(id, isEnabled) {
  return request({
    url: '/dca/notify/channels/' + id + '/status',
    method: 'put',
    params: { isEnabled }
  })
}

/**
 * 测试通知渠道
 * @param {number} id - 渠道ID
 * @returns {Promise} 请求Promise
 */
export function testChannel(id) {
  return request({
    url: '/dca/notify/channels/' + id + '/test',
    method: 'post'
  })
}

/**
 * 查询通知记录列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listNotifyRecord(query) {
  return request({
    url: '/dca/notify/records/list',
    method: 'get',
    params: query
  })
}

/**
 * 获取通知记录详情
 * @param {number} id - 记录ID
 * @returns {Promise} 请求Promise
 */
export function getNotifyRecord(id) {
  return request({
    url: '/dca/notify/records/' + id,
    method: 'get'
  })
}

/**
 * 重发通知
 * @param {number} id - 记录ID
 * @returns {Promise} 请求Promise
 */
export function resendNotify(id) {
  return request({
    url: '/dca/notify/records/retry/' + id,
    method: 'post'
  })
}

/**
 * 导出通知记录
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function exportNotifyRecord(query) {
  return request({
    url: '/dca/notify/records/export',
    method: 'get',
    params: query
  })
}

/**
 * 获取通知统计概览
 * @returns {Promise} 请求Promise
 */
export function getNotifyStats() {
  return request({
    url: '/dca/notify/records/overview',
    method: 'get'
  })
}

/**
 * 测试邮件连接
 * @param {number} id - 渠道ID
 * @returns {Promise} 请求Promise
 */
export function testMailConnection(id) {
  return request({
    url: '/dca/notify/channels/' + id + '/testConnection',
    method: 'post'
  })
}
