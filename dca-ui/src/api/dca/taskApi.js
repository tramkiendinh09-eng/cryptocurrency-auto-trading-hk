import request from '@/utils/request'

// Legacy market task endpoints stay as compatibility-only exports.

// 查询采集任务列表
export function listTask() {
  return request({
    url: '/dca/market/task/list',
    method: 'get'
  })
}

// 新增采集任务
export function addTask(data) {
  return request({
    url: '/dca/market/task',
    method: 'post',
    data: data
  })
}

// 修改采集任务
export function updateTask(data) {
  return request({
    url: '/dca/market/task',
    method: 'put',
    data: data
  })
}

// 删除采集任务
export function deleteTask(ids) {
  return request({
    url: '/dca/market/task/' + ids,
    method: 'delete'
  })
}

// 查询API配置列表

// 新增API配置

// 修改API配置

// 删除API配置

// 测试API连接
