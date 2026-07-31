import { describe, expect, it } from 'vitest'

import { createLegacyRiskConsoleLinks } from '../index.vue'

describe('createLegacyRiskConsoleLinks', () => {
  it('routes frozen legacy risk users to runtime trade consoles', () => {
    expect(createLegacyRiskConsoleLinks()).toEqual([
      { label: 'Runtime Mode', path: '/dca/trade/runtime', type: 'primary' },
      { label: 'Risk Hits', path: '/dca/trade/risk-hits', type: 'default' },
      { label: 'Decision Audit', path: '/dca/trade/decision', type: 'default' },
      { label: 'Notify Policy', path: '/dca/trade/notify-policy', type: 'default' }
    ])
  })
})
