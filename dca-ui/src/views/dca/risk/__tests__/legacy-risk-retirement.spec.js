import { describe, expect, it } from 'vitest'

import { createLegacyRiskConsoleLinks } from '../index.vue'

describe('createLegacyRiskConsoleLinks', () => {
  it('routes frozen legacy risk users to runtime trade consoles', () => {
    expect(createLegacyRiskConsoleLinks()).toEqual([
      { label: '运行模式', path: '/dca/trade/runtime', type: 'primary' },
      { label: '风险熔断', path: '/dca/trade/risk-hits', type: 'default' },
      { label: '决策审计', path: '/dca/trade/decision', type: 'default' },
      { label: '通知策略', path: '/dca/trade/notify-policy', type: 'default' }
    ])
  })
})
