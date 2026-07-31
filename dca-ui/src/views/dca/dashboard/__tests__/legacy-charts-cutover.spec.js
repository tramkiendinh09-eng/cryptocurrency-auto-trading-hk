import { describe, expect, it } from 'vitest'

import { createLegacyDashboardLinks } from '../charts.vue'

describe('createLegacyDashboardLinks', () => {
  it('redirects legacy dashboard users to runtime trade console pages', () => {
    expect(createLegacyDashboardLinks()).toEqual([
      { label: 'Runtime Mode', path: '/dca/trade/runtime', type: 'primary' },
      { label: 'Decision Audit', path: '/dca/trade/decision', type: 'default' },
      { label: 'Replay Console', path: '/dca/trade/replay', type: 'default' },
      { label: 'Orders', path: '/dca/trade/orders', type: 'default' },
      { label: 'Positions', path: '/dca/trade/positions', type: 'default' }
    ])
  })
})
