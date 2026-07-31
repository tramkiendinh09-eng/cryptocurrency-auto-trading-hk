import { describe, expect, it } from 'vitest'

import {
  buildTradePositionGuardPayload,
  createTradePositionGuardForm,
  formatGuardThresholdPercent,
  validateTradePositionGuardPayload
} from '../index.vue'

describe('createTradePositionGuardForm', () => {
  it('hydrates persisted guard scopes for editing', () => {
    expect(
      createTradePositionGuardForm({
        id: 12,
        guardName: 'BTC Guard',
        scopeType: 'SYMBOL',
        strategyId: 7,
        symbol: 'BTCUSDT',
        exchangeCode: 'BINANCE',
        stopLossPct: 0.03,
        takeProfitPct: 0.06,
        maxHoldingMinutes: 180,
        enabled: true,
        priority: 9,
        remark: 'guard'
      })
    ).toMatchObject({
      id: 12,
      guardName: 'BTC Guard',
      scopeType: 'SYMBOL',
      strategyId: 7,
      symbol: 'BTCUSDT',
      exchangeCode: 'BINANCE',
      stopLossPct: 3,
      takeProfitPct: 6,
      maxHoldingMinutes: 180,
      enabled: true,
      priority: 9,
      remark: 'guard'
    })
  })
})

describe('buildTradePositionGuardPayload', () => {
  it('converts percent form thresholds into ratio payload fields', () => {
    expect(
      buildTradePositionGuardPayload({
        id: 12,
        guardName: ' BTC Guard ',
        scopeType: ' symbol ',
        strategyId: 7,
        symbol: ' btcusdt ',
        exchangeCode: ' binance ',
        stopLossPct: '3',
        takeProfitPct: '6',
        maxHoldingMinutes: '180',
        enabled: 1,
        priority: '9',
        remark: ' guard '
      })
    ).toEqual({
      id: 12,
      guardName: 'BTC Guard',
      scopeType: 'SYMBOL',
      strategyId: 7,
      symbol: 'BTCUSDT',
      exchangeCode: 'BINANCE',
      stopLossPct: 0.03,
      takeProfitPct: 0.06,
      maxHoldingMinutes: 180,
      enabled: true,
      priority: 9,
      remark: 'guard'
    })
  })
})

describe('position guard threshold units', () => {
  it('keeps user-facing form values in percent while API payload remains ratio', () => {
    const form = createTradePositionGuardForm({
      guardName: 'Default Guard',
      scopeType: 'GLOBAL',
      stopLossPct: 0.1,
      takeProfitPct: 0.3
    })

    expect(form.stopLossPct).toBe(10)
    expect(form.takeProfitPct).toBe(30)
    expect(buildTradePositionGuardPayload(form).stopLossPct).toBe(0.1)
    expect(buildTradePositionGuardPayload(form).takeProfitPct).toBe(0.3)
  })

  it('formats persisted ratio thresholds as percent labels', () => {
    expect(formatGuardThresholdPercent(0.1)).toBe('10%')
    expect(formatGuardThresholdPercent(null)).toBe('-')
  })
})

describe('validateTradePositionGuardPayload', () => {
  it('rejects strategy scope without strategy binding', () => {
    expect(() =>
      validateTradePositionGuardPayload({
        guardName: 'Strategy Guard',
        scopeType: 'STRATEGY',
        stopLossPct: 0.03
      })
    ).toThrow(/策略/)
  })

  it('rejects symbol scope without symbol and exchange', () => {
    expect(() =>
      validateTradePositionGuardPayload({
        guardName: 'BTC Guard',
        scopeType: 'SYMBOL',
        strategyId: 7,
        stopLossPct: 0.03
      })
    ).toThrow(/交易对|交易所/)
  })
})
