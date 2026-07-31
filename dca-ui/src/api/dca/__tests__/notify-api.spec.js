import { beforeEach, describe, expect, it, vi } from 'vitest'

const { requestMock } = vi.hoisted(() => ({
  requestMock: vi.fn((config) => config)
}))

vi.mock('@/utils/request', () => ({
  default: requestMock
}))

import {
  getNotifyStats,
  resendNotify
} from '../notify'

describe('notify api request contract', () => {
  beforeEach(() => {
    requestMock.mockClear()
  })

  it('routes notify record retry and overview stats calls through the live notify record endpoints', () => {
    expect(resendNotify(9)).toEqual({
      url: '/dca/notify/records/retry/9',
      method: 'post'
    })

    expect(getNotifyStats()).toEqual({
      url: '/dca/notify/records/overview',
      method: 'get'
    })
  })
})
