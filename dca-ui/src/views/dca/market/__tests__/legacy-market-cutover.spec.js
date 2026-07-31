import { describe, expect, it } from 'vitest'

import {
  createLegacyMarketConsoleLinks,
  defaultMarketActiveTab,
  legacyMarketCompatibilityMessage,
  marketBindingTabName,
  marketDataSourceConsolePath,
  marketPageTitle
} from '../index.vue'

describe('legacy market page cutover', () => {
  it('defaults the market page to api config management instead of legacy dashboard tabs', () => {
    expect(defaultMarketActiveTab).toBe('apis')
  })

  it('keeps source bindings inside the unified market data source console', () => {
    expect(marketBindingTabName).toBe('bindings')
    expect(marketDataSourceConsolePath).toBe('/dca/market?tab=bindings')
    expect(createLegacyMarketConsoleLinks()).toEqual([
      expect.objectContaining({ path: '/dca/trade/runtime', type: 'default' }),
      expect.objectContaining({ path: '/dca/trade/decision', type: 'default' })
    ])
    expect(createLegacyMarketConsoleLinks().map(item => item.path)).not.toContain('/dca/trade/source-binding')
    expect(legacyMarketCompatibilityMessage).toContain('WebSocket')
  })

  it('frames the page itself as the unified market data source control plane', () => {
    expect(marketPageTitle).toContain('数据源')
    expect(legacyMarketCompatibilityMessage).toContain('REST / WebSocket')
  })
})
