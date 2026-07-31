import request from '@/utils/request';

// 查询AI模型列表
export function listModel(query) {
  return request({
    url: '/dca/ai/models/list',
    method: 'get',
    params: query
  });
}

// 查询AI模型详细
export function getModel(id) {
  return request({
    url: '/dca/ai/models/' + id,
    method: 'get'
  });
}

// 新增AI模型
export function addModel(data) {
  return request({
    url: '/dca/ai/models',
    method: 'post',
    data: data
  });
}

// 修改AI模型
export function updateModel(data) {
  return request({
    url: '/dca/ai/models',
    method: 'put',
    data: data
  });
}

// 删除AI模型
export function delModel(ids) {
  return request({
    url: '/dca/ai/models/' + ids,
    method: 'delete'
  });
}

// 设置默认AI模型
export function setDefaultModel(id) {
  return request({
    url: '/dca/ai/models/' + id + '/setDefault',
    method: 'post'
  });
}

// 测试AI模型连接
export function testModel(id) {
  return request({
    url: '/dca/ai/models/' + id + '/test',
    method: 'post'
  });
}

// 获取AI模型使用统计
export function getStats() {
  return request({
    url: '/dca/ai/models/stats',
    method: 'get'
  });
}

// 以下是为了兼容index.vue中的引用而添加的别名导出
export const listAiModel = listModel;
export const getAiModel = getModel;
export const addAiModel = addModel;
export const updateAiModel = updateModel;
export const delAiModel = delModel;
export const setDefaultAiModel = setDefaultModel;
export const testAiModel = testModel;
export const getAiStats = getStats;