import { describe, expect, it } from 'vitest'

import {
  buildTradeAuditSummaryRows,
  buildTraceAuditState,
  formatTradeMemoryOutcome,
  formatTraceAuditEventMeta,
  formatPositionSide,
  formatMemorySummary,
  formatOrderExecutionMeta,
  tradeMemoryStatusTag,
  traceAuditStatusTag
} from '../index.vue'

describe('buildTraceAuditState', () => {
  it('normalizes empty response payload', () => {
    expect(buildTraceAuditState()).toEqual({
      summary: {},
      events: [],
      decision: null,
      riskHits: [],
      order: null,
      fills: [],
      tradeSummary: null,
      positionSnapshot: null,
      pnlSnapshot: null,
      notifications: []
    })
  })

  it('keeps trade memory and lifecycle status payloads for lifecycle review', () => {
    expect(
      buildTraceAuditState({
        decision: {
          tradeMemoryStatus: {
            status: 'stored',
            lesson_text: 'Wait for reclaim confirmation before exiting.'
          },
          lifecycleStatus: {
            status: 'recorded',
            memory_status: 'stored'
          }
        }
      }).decision
    ).toEqual({
      tradeMemoryStatus: {
        status: 'stored',
        lesson_text: 'Wait for reclaim confirmation before exiting.'
      },
      lifecycleStatus: {
        status: 'recorded',
        memory_status: 'stored'
      }
    })
  })
})

describe('formatTraceAuditEventMeta', () => {
  it('formats market tick details for audit timeline', () => {
    expect(
      formatTraceAuditEventMeta({
        eventType: 'market_tick',
        payload: { price: 1048.6, volume: 11807865499.84 }
      })
    ).toContain('价格')
  })
})

describe('traceAuditStatusTag', () => {
  it('maps blocked status to danger tag', () => {
    expect(traceAuditStatusTag('blocked')).toBe('danger')
  })
})

describe('formatPositionSide', () => {
  it('normalizes legacy buy/sell aliases for position snapshots', () => {
    expect(formatPositionSide('buy')).toBe(formatPositionSide('long'))
    expect(formatPositionSide('sell')).toBe(formatPositionSide('short'))
  })
})



describe('formatMemorySummary', () => {
  it('summarizes memory usage in trace audit', () => {
    expect(formatMemorySummary({ memoryUsage: { short_term_counts: { news: 2 }, long_term_count: 1 } })).toBe('?? 2 / ?? 1')
  })
})

describe('trade memory outcome helpers', () => {
  it('shows readable lifecycle lesson text for completed trades', () => {
    expect(
      formatTradeMemoryOutcome({
        decision: {
          tradeMemoryStatus: {
            status: 'stored',
            lesson_text: 'Wait for reclaim confirmation before exiting.'
          }
        }
      })
    ).toBe('Wait for reclaim confirmation before exiting.')
    expect(tradeMemoryStatusTag('stored')).toBe('success')
  })

  it('falls back to feature snapshot memory payload when direct detail fields are absent', () => {
    expect(
      formatTradeMemoryOutcome({
        decision: {
          featureSnapshot: {
            snapshot: {
              tradeMemoryStatus: {
                status: 'stored',
                lesson_text: 'Read memory outcome from feature snapshot fallback.'
              },
              lifecycleStatus: {
                memory_status: 'stored'
              }
            }
          }
        }
      })
    ).toBe('Read memory outcome from feature snapshot fallback.')
  })

  it('shows status and reason when no lesson was learned', () => {
    expect(
      formatTradeMemoryOutcome({
        decision: {
          tradeMemoryStatus: {
            status: 'failed',
            reason: 'memory_store_create_failed'
          }
        }
      })
    ).toBe('failed / memory_store_create_failed')
    expect(tradeMemoryStatusTag('failed')).toBe('danger')
  })
})

describe('formatOrderExecutionMeta', () => {
  it('formats order metadata in trace audit', () => {
    expect(
      formatOrderExecutionMeta({
        action: 'REDUCE',
        orderType: 'limit',
        positionSide: 'short',
        reduceOnly: false,
        tdMode: 'cross',
        leverage: 2,
        limitPrice: 65000,
        quantityBase: 0.05,
        okxEnhancedExecution: true
      })
    ).toBe('REDUCE / limit / short / reduceOnly=false / cross / 2x / px 65000 / qty 0.05 / OKX+')
  })
})

describe('buildTradeAuditSummaryRows', () => {
  it('surfaces open close quantity and realized pnl directly for audit readers', () => {
    expect(
      buildTradeAuditSummaryRows({
        tradeSummary: {
          positionSide: 'short',
          fillQuantity: '1.50000000',
          openPrice: '2371.05000000',
          closePrice: '2362.05000000',
          realizedPnl: '13.50000000',
          entryPrice: '0.00000000',
          positionQuantity: '0.00000000'
        },
        positionSnapshot: {
          side: 'short',
          positionQuantity: '0.00000000',
          entryPrice: '0.00000000',
          unrealizedPnl: '0.00000000'
        },
        pnlSnapshot: {
          accountEquity: '10013.50000000',
          unrealizedPnl: '0.00000000',
          realizedPnl: '13.50000000',
          dailyPnl: '13.50000000'
        }
      })
    ).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'positionSide', value: formatPositionSide('short') }),
      expect.objectContaining({ key: 'fillQuantity', value: '1.50000000' }),
      expect.objectContaining({ key: 'openPrice', value: '2371.05000000' }),
      expect.objectContaining({ key: 'closePrice', value: '2362.05000000' }),
      expect.objectContaining({ key: 'realizedPnl', value: '+13.5000', tone: 'success' }),
      expect.objectContaining({ key: 'positionQuantity', value: '0.00000000' }),
      expect.objectContaining({ key: 'entryPrice', value: '0.00000000' }),
      expect.objectContaining({ key: 'unrealizedPnl', value: '0.00000000' }),
      expect.objectContaining({ key: 'accountEquity', value: '10013.50000000' }),
      expect.objectContaining({ key: 'dailyPnl', value: '13.50000000' })
    ]))
  })

  it('includes post-trade memory outcome rows for lifecycle learning review', () => {
    expect(
      buildTradeAuditSummaryRows({
        decision: {
          tradeMemoryStatus: {
            status: 'stored',
            reason: '',
            lesson_text: 'Wait for reclaim confirmation before exiting.'
          }
        }
      })
    ).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'tradeMemoryStatus', value: 'stored' }),
      expect.objectContaining({ key: 'tradeMemoryLesson', value: 'Wait for reclaim confirmation before exiting.' })
    ]))
  })

  it('includes feature snapshot fallback memory outcome rows for lifecycle review', () => {
    expect(
      buildTradeAuditSummaryRows({
        decision: {
          featureSnapshot: {
            snapshot: {
              tradeMemoryStatus: {
                status: 'stored',
                lesson_text: 'Read memory outcome from feature snapshot fallback.'
              },
              lifecycleStatus: {
                memory_status: 'stored'
              }
            }
          }
        }
      })
    ).toEqual(expect.arrayContaining([
      expect.objectContaining({ key: 'tradeMemoryStatus', value: 'stored' }),
      expect.objectContaining({ key: 'tradeMemoryLesson', value: 'Read memory outcome from feature snapshot fallback.' })
    ]))
  })
})
