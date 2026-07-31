import { describe, expect, it } from 'vitest'

import { extractPositionRows, formatPositionSide } from '../index.vue'

describe('extractPositionRows', () => {
  it('returns data when payload contains a data array', () => {
    expect(extractPositionRows({
      data: [{ symbol: 'BTCUSDT' }]
    })).toEqual([{ symbol: 'BTCUSDT' }])
  })

  it('falls back to rows when data is not an array', () => {
    expect(extractPositionRows({
      data: { symbol: 'BTCUSDT' },
      rows: [{ symbol: 'ETHUSDT' }]
    })).toEqual([{ symbol: 'ETHUSDT' }])
  })

  it('returns an empty array when payload does not contain a list', () => {
    expect(extractPositionRows({
      data: { symbol: 'BTCUSDT' }
    })).toEqual([])
  })
})

describe('formatPositionSide', () => {
  it('normalizes legacy order side aliases before displaying position direction', () => {
    expect(formatPositionSide('buy')).toBe(formatPositionSide('long'))
    expect(formatPositionSide('sell')).toBe(formatPositionSide('short'))
  })
})

