import request from '@/utils/request'

// 查询卡密列表
export function listCard(query) {
  return request({
    url: '/dca/card/list',
    method: 'get',
    params: query
  })
}

// 查询卡密详细
export function getCard(id) {
  return request({
    url: '/dca/card/' + id,
    method: 'get'
  })
}

// 批量生成卡密
export function generateCards(data) {
  return request({
    url: '/dca/card/generate',
    method: 'post',
    data: data
  })
}

// 激活卡密
export function activateCard(data) {
  return request({
    url: '/dca/card/activate',
    method: 'post',
    data: data
  })
}

// 删除卡密
export function delCard(ids) {
  return request({
    url: '/dca/card/' + ids,
    method: 'delete'
  })
}

// 禁用卡密
export function disableCard(id) {
  return request({
    url: '/dca/card/' + id + '/disable',
    method: 'post'
  })
}

// 查询使用统计
export function getCardUsage(id) {
  return request({
    url: '/dca/card/usage/' + id,
    method: 'get'
  })
}

// 我的卡密
export function getMyCard() {
  return request({
    url: '/dca/card/my',
    method: 'get'
  })
}

// 导出卡密
export function exportCards(query) {
  return request({
    url: '/dca/card/export',
    method: 'post',
    params: query
  })
}
