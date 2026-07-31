import request from '@/utils/request'

/**
 * 追踪审计API模块
 * 提供交易追踪详情的查询接口
 */

/**
 * 获取追踪审计详情
 * @param {string} traceId - 追踪ID
 * @returns {Promise} 请求Promise
 */
export function getTraceAuditDetail(traceId) {
  return request({
    url: '/dca/trade/trace/detail',
    method: 'get',
    params: { traceId }
  })
}
