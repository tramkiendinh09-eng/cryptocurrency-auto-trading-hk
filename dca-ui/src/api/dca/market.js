import request from '@/utils/request'

// 查询市场数据采集配置列表
export function listConfig(query) {
  return request({
    url: '/dca/market/config/list',
    method: 'get',
    params: query
  })
}

// 查询市场数据采集配置详细
export function getConfig(id) {
  return request({
    url: '/dca/market/config/' + id,
    method: 'get'
  })
}

// 新增市场数据采集配置
export function addConfig(data) {
  return request({
    url: '/dca/market/config',
    method: 'post',
    data: data
  })
}

// 修改市场数据采集配置
export function updateConfig(data) {
  return request({
    url: '/dca/market/config',
    method: 'put',
    data: data
  })
}

// 删除市场数据采集配置
export function delConfig(ids) {
  return request({
    url: '/dca/market/config/' + ids,
    method: 'delete'
  })
}

// 获取市场数据
export function getMarketData(symbol) {
  return request({
    url: '/dca/market/data/' + symbol,
    method: 'get'
  })
}

// 获取市场数据历史
export function getMarketDataHistory(symbol, days) {
  return request({
    url: '/dca/market/data/' + symbol + '/history',
    method: 'get',
    params: { days }
  })
}

// 获取恐慌贪婪指数
export function getFearGreedIndex() {
  return request({
    url: '/dca/market/feargreed',
    method: 'get'
  })
}

// 触发数据采集
export function triggerCollection(data) {
  return request({
    url: '/dca/market/collect/trigger',
    method: 'post',
    data: data
  })
}

// 查询采集日志
export function listLog(query) {
  return request({
    url: '/dca/market/log/list',
    method: 'get',
    params: query
  })
}

// 获取仪表盘数据
export function getDashboard() {
  return request({
    url: '/dca/market/dashboard',
    method: 'get'
  })
}

// 查询市场 API 配置列表
export function listApi(params) {
  return request({
    url: '/dca/market/api/list',
    method: 'get',
    params: params
  })
}

// 新增市场 API 配置
export function addApi(data) {
  return request({
    url: '/dca/market/api',
    method: 'post',
    data: data
  })
}

// 修改市场 API 配置
export function updateApi(data) {
  return request({
    url: '/dca/market/api',
    method: 'put',
    data: data
  })
}

// 删除市场 API 配置
export function deleteApi(ids) {
  return request({
    url: '/dca/market/api/' + ids,
    method: 'delete'
  })
}

// 测试市场 API 配置
export function testApi(id) {
  return request({
    url: '/dca/market/api/test/' + id,
    method: 'post'
  })
}
