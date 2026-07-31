import request from '@/utils/request'

/**
 * 决策审计API模块
 * 提供决策运行记录的查询接口
 */

/**
 * 查询决策运行记录列表
 * @param {Object} query - 查询参数
 * @returns {Promise} 请求Promise
 */
export function listDecisionRuns(query) {
  return request({
    url: '/dca/decision/runs',
    method: 'get',
    params: query
  })
}

