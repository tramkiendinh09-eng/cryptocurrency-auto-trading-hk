import { describe, expect, it } from 'vitest'

import {
  buildTradeSourceBindingPayload,
  createTradeSourceBindingForm,
  validateTradeSourceBindingPayload
} from '../SourceBindingPanel.vue'

describe('createTradeSourceBindingForm', () => {
  it('hydrates existing source binding scopes for editing', () => {
    expect(
      createTradeSourceBindingForm({
        id: 12,
        bindingName: 'Primary News Feed',
        strategyId: 7,
        sourceId: 21,
        eventType: 'news',
        symbolScopeJson: '["BTCUSDT","ETHUSDT"]',
        exchangeScopeJson: '["BINANCE"]',
        modeScopeJson: '["shadow","live"]',
        enabled: true
      })
    ).toMatchObject({
      id: 12,
      bindingName: 'Primary News Feed',
      strategyId: 7,
      sourceId: 21,
      eventType: 'news',
      symbols: ['BTCUSDT', 'ETHUSDT'],
      exchanges: ['BINANCE'],
      runtimeModes: ['shadow', 'live'],
      enabled: true
    })
  })
})

describe('buildTradeSourceBindingPayload', () => {
  it('normalizes source binding scopes into db-ready json payload', () => {
    expect(
      buildTradeSourceBindingPayload({
        id: 12,
        bindingName: ' Primary News Feed ',
        strategyId: 7,
        sourceId: 21,
        eventType: ' News ',
        symbols: [' btcusdt ', 'ETHUSDT'],
        exchanges: [' binance ', 'OKX'],
        runtimeModes: [' shadow ', 'LIVE'],
        enabled: 1
      })
    ).toEqual({
      id: 12,
      bindingName: 'Primary News Feed',
      strategyId: 7,
      sourceId: 21,
      eventType: 'news',
      symbolScopeJson: '["BTCUSDT","ETHUSDT"]',
      exchangeScopeJson: '["BINANCE","OKX"]',
      modeScopeJson: '["shadow","live"]',
      enabled: true
    })
  })
})

describe('validateTradeSourceBindingPayload', () => {
  it('rejects source bindings with unsupported v1 symbols', () => {
    expect(() =>
      validateTradeSourceBindingPayload({
        bindingName: 'Alt Feed',
        sourceId: 21,
        eventType: 'news',
        symbols: ['BTCUSDT', 'XRPUSDT'],
        exchanges: ['BINANCE'],
        runtimeModes: ['paper']
      })
    ).toThrow(/XRPUSDT/)
  })

  it('rejects bindings without a source config', () => {
    expect(() =>
      validateTradeSourceBindingPayload({
        bindingName: 'Primary News Feed',
        sourceId: null,
        eventType: 'news',
        symbols: ['BTCUSDT'],
        exchanges: ['BINANCE'],
        runtimeModes: ['shadow']
      })
    ).toThrow(/数据源/)
  })
})
