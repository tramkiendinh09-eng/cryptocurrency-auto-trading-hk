import { beforeEach, describe, expect, it, vi } from 'vitest'

const { requestMock } = vi.hoisted(() => ({
  requestMock: vi.fn((config) => config)
}))

vi.mock('@/utils/request', () => ({
  default: requestMock
}))

import {
  addApi,
  deleteApi,
  listApi,
  testApi,
  updateApi
} from '../market'
import * as taskApi from '../taskApi'

describe('market api config request contract', () => {
  beforeEach(() => {
    requestMock.mockClear()
  })

  it('routes market api config CRUD calls through /dca/market/api endpoints', () => {
    const query = { dataCategory: 'PRICE' }
    const payload = { configName: 'Binance Spot Ticker' }

    expect(listApi(query)).toEqual({
      url: '/dca/market/api/list',
      method: 'get',
      params: query
    })
    expect(addApi(payload)).toEqual({
      url: '/dca/market/api',
      method: 'post',
      data: payload
    })
    expect(updateApi(payload)).toEqual({
      url: '/dca/market/api',
      method: 'put',
      data: payload
    })
    expect(deleteApi(7)).toEqual({
      url: '/dca/market/api/7',
      method: 'delete'
    })
    expect(testApi(7)).toEqual({
      url: '/dca/market/api/test/7',
      method: 'post'
    })
  })

  it('keeps market api config exports out of the legacy task api module', () => {
    expect(taskApi.listApi).toBeUndefined()
    expect(taskApi.addApi).toBeUndefined()
    expect(taskApi.updateApi).toBeUndefined()
    expect(taskApi.deleteApi).toBeUndefined()
    expect(taskApi.testApi).toBeUndefined()
  })
})
