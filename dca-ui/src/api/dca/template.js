import request from '@/utils/request';

// 查询提示词模板列表
export function listTemplate(query) {
  return request({
    url: '/dca/template/list',
    method: 'get',
    params: query
  });
}

// 查询提示词模板详细
export function getTemplate(id) {
  return request({
    url: '/dca/template/' + id,
    method: 'get'
  });
}

// 新增提示词模板
export function addTemplate(data) {
  return request({
    url: '/dca/template',
    method: 'post',
    data: data
  });
}

// 修改提示词模板
export function updateTemplate(data) {
  return request({
    url: '/dca/template',
    method: 'put',
    data: data
  });
}

// 删除提示词模板
export function delTemplate(ids) {
  return request({
    url: '/dca/template/' + ids,
    method: 'delete'
  });
}

// 启用/禁用提示词模板
export function toggleTemplate(id, isActive) {
  return request({
    url: '/dca/template/' + id + '/toggle',
    method: 'put',
    params: { isActive }
  });
}