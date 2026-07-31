import request from '@/utils/request'

// 查询操作日志
export function listOperationLog(query) {
  return request({
    url: '/dca/audit/operations',
    method: 'get',
    params: query
  })
}

// 查询策略触发日志
export function listTriggerLog(query) {
  return request({
    url: '/dca/audit/triggers',
    method: 'get',
    params: query
  })
}

// 查询AI调用日志
export function listAiCallLog(query) {
  return request({
    url: '/dca/audit/aiCalls',
    method: 'get',
    params: query
  })
}

// 获取审计统计
export function getAuditStatistics() {
  return request({
    url: '/dca/audit/statistics',
    method: 'get'
  })
}

// 导出日志
export function exportLog(type, query) {
  return request({
    url: '/dca/audit/' + type + '/export',
    method: 'post',
    params: query
  })
}
