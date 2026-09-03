import { describe, expect, it } from 'vitest'

import { createLegacyDashboardLinks } from '../charts.vue'

describe('createLegacyDashboardLinks', () => {
  it('redirects legacy dashboard users to runtime trade console pages', () => {
    expect(createLegacyDashboardLinks()).toEqual([
      { label: '运行模式', path: '/dca/trade/runtime', type: 'primary' },
      { label: '决策审计', path: '/dca/trade/decision', type: 'default' },
      { label: '历史回放', path: '/dca/trade/replay', type: 'default' },
      { label: '订单', path: '/dca/trade/orders', type: 'default' },
      { label: '仓位', path: '/dca/trade/positions', type: 'default' }
    ])
  })
})
