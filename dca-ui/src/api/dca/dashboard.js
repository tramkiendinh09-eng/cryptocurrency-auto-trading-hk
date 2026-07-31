import request from '@/utils/request'

// 仪表盘概览
export function getOverview(params) {
  return request({
    url: '/dca/dashboard/overview',
    method: 'get',
    params
  })
}

// Worker 状态
export function getWorkerStatus() {
  return request({
    url: '/dca/dashboard/workerStatus',
    method: 'get'
  })
}

// 通知统计
export function getNotifyStats(params) {
  return request({
    url: '/dca/dashboard/notifyStats',
    method: 'get',
    params
  })
}

// 风控统计
export function getRiskStats(params) {
  return request({
    url: '/dca/dashboard/riskStats',
    method: 'get',
    params
  })
}
