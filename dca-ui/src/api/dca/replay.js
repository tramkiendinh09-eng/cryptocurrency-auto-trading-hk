import request from '@/utils/request'

/**
 * 回放API模块
 * 提供交易回放相关的接口调用
 */

/**
 * 查询回放会话列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listReplaySessions(query) {
  return request({
    url: '/dca/trade/replay/sessions',
    method: 'get',
    params: query
  })
}

/**
 * 查询回放事件列表
 * @param {string} sessionId - 会话ID
 * @returns {Promise} 请求Promise
 */
export function listReplayEvents(sessionId) {
  return request({
    url: '/dca/trade/replay/events',
    method: 'get',
    params: sessionId ? { sessionId } : {}
  })
}

/**
 * 获取回放对比结果
 * @param {string} sessionId - 会话ID
 * @returns {Promise} 请求Promise
 */
export function getReplayComparison(sessionId) {
  return request({
    url: '/dca/trade/replay/compare',
    method: 'get',
    params: { sessionId }
  })
}

/**
 * 获取回放源数据
 * @param {string} traceId - 追踪ID
 * @returns {Promise} 请求Promise
 */
export function getReplaySource(traceId) {
  return request({
    url: '/dca/trade/replay/source',
    method: 'get',
    params: { traceId }
  })
}

/**
 * 分发回放任务
 * @param {string} traceId - 追踪ID
 * @returns {Promise} 请求Promise
 */
export function dispatchReplay(traceId) {
  return request({
    url: '/dca/trade/replay/dispatch',
    method: 'post',
    params: { traceId }
  })
}
