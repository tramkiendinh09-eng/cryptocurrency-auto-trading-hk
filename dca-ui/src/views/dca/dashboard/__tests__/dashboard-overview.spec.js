import { describe, expect, it } from 'vitest'

import {
  buildExecutionSummaryItems,
  buildOverviewState,
  buildRuntimeFeedRows,
  getDashboardShortcutPath
} from '../index.vue'

describe('buildOverviewState', () => {
  it('maps runtime activity metrics instead of legacy trigger counters', () => {
    const state = buildOverviewState({
      decisionCount: '12',
      eventCount: '30',
      signalCount: '18',
      activePositionCount: '4'
    })

    expect(state.activityStats).toEqual({
      decisionCount: 12,
      eventCount: 30,
      signalCount: 18,
      activePositionCount: 4
    })
  })

  it('keeps a stable execution stats shape from overview payload', () => {
    const state = buildOverviewState({
      executionStats: {
        filled: 3,
        partial: 2,
        blocked: 1,
        skipped: 1,
        failed: 1,
        total: 8
      }
    })

    expect(state.executionStats).toEqual({
      total: 8,
      filled: 3,
      submitted: 0,
      pending: 0,
      partial: 2,
      canceled: 0,
      expired: 0,
      failed: 1,
      blocked: 1,
      skipped: 1
    })
  })

  it('normalizes notify stats into a stable operator-facing shape', () => {
    const state = buildOverviewState({
      notifyStats: {
        successRate: '87.5',
        todayCount: '5',
        weekTotal: '8'
      }
    })

    expect(state.notifyStats).toEqual({
      successRate: 87.5,
      todayCount: 5,
      weekTotal: 8,
      weekSuccess: 0,
      weekFailed: 0
    })
  })

  it('normalizes weekly notify success/failure counts', () => {
    const state = buildOverviewState({
      notifyStats: {
        weekSuccess: '4',
        weekFailed: '1'
      }
    })

    expect(state.notifyStats.weekSuccess).toBe(4)
    expect(state.notifyStats.weekFailed).toBe(1)
  })

  it('normalizes risk stats into a stable operator-facing shape', () => {
    const state = buildOverviewState({
      riskStats: {
        todayBlocks: '2',
        blockRate: '25.0'
      }
    })

    expect(state.riskStats).toEqual({
      todayBlocks: 2,
      blockRate: 25
    })
  })

  it('normalizes runtime feed collections into stable arrays', () => {
    const state = buildOverviewState({
      recentEvents: [{ traceId: 'event-1' }],
      recentSignals: null,
      recentAgentConclusions: [{ traceId: 'agent-1' }],
      recentDecisions: undefined,
      recentRiskHits: [{ traceId: 'risk-1' }],
      recentFills: [{ traceId: 'fill-1' }],
      recentOrders: [{ traceId: 'order-1' }],
      recentPositions: [{ traceId: 'pos-1' }]
    })

    expect(state.runtimeFeed).toEqual({
      recentEvents: [{ traceId: 'event-1' }],
      recentSignals: [],
      recentAgentConclusions: [{ traceId: 'agent-1' }],
      recentDecisions: [],
      recentRiskHits: [{ traceId: 'risk-1' }],
      recentFills: [{ traceId: 'fill-1' }],
      recentOrders: [{ traceId: 'order-1' }],
      recentPositions: [{ traceId: 'pos-1' }]
    })
  })
})

describe('buildExecutionSummaryItems', () => {
  it('builds operator-facing execution summary items', () => {
    const items = buildExecutionSummaryItems({
      total: 8,
      filled: 3,
      submitted: 0,
      pending: 0,
      partial: 2,
      canceled: 0,
      expired: 0,
      failed: 1,
      blocked: 1,
      skipped: 1
    })

    expect(items).toHaveLength(9)
    expect(items[0]).toMatchObject({ key: 'filled', value: 3, tagType: 'success' })
    expect(items[1]).toMatchObject({ key: 'submitted', value: 0, tagType: 'warning' })
    expect(items[3]).toMatchObject({ key: 'partial', value: 2, tagType: 'warning' })
    expect(items[6]).toMatchObject({ key: 'failed', value: 1, tagType: 'danger' })
    expect(items[7]).toMatchObject({ key: 'blocked', value: 1, tagType: 'danger' })
    expect(items[8]).toMatchObject({ key: 'skipped', value: 1, tagType: 'info' })
  })
})

describe('buildOverviewState worker status normalization', () => {
  it('stabilizes worker task counters and metadata', () => {
    const state = buildOverviewState({
      workerStatus: {
        online: '1',
        workerId: 'worker-123',
        workerType: 'generic',
        pid: '987',
        host: 'worker-host',
        totalTasks: '10',
        successTasks: '7',
        failedTasks: '3',
        queueLength: '2',
        lastHeartbeat: '2026-04-14T12:00:00Z'
      }
    })

    expect(state.workerStatus).toEqual({
      online: true,
      workerId: 'worker-123',
      workerType: 'generic',
      pid: '987',
      host: 'worker-host',
      totalTasks: 10,
      successTasks: 7,
      failedTasks: 3,
      queueLength: 2,
      lastHeartbeat: '2026-04-14T12:00:00Z'
    })
  })
})

describe('buildRuntimeFeedRows', () => {
  it('flattens runtime read models into a sorted feed', () => {
    const rows = buildRuntimeFeedRows({
      recentSignals: [
        { createdAt: '2026-04-15T08:00:00Z', traceId: 'trace-signal', symbol: 'ETHUSDT', signalType: 'VOL_SPIKE' }
      ],
      recentOrders: [
        { createdAt: '2026-04-15T09:00:00Z', traceId: 'trace-order', symbol: 'BTCUSDT', side: 'BUY', status: 'filled' }
      ],
      recentFills: [
        { createdAt: '2026-04-15T08:30:00Z', traceId: 'trace-fill', orderRef: 'ord-1' }
      ],
      recentEvents: [
        { createdAt: '2026-04-15T07:00:00Z', traceId: 'trace-event', eventType: 'ticker' }
      ]
    })

    expect(rows).toHaveLength(4)
    expect(rows[0]).toMatchObject({
      feedType: 'order',
      traceId: 'trace-order',
      symbol: 'BTCUSDT'
    })
    expect(rows[1]).toMatchObject({
      feedType: 'fill',
      traceId: 'trace-fill'
    })
    expect(rows[2]).toMatchObject({
      feedType: 'signal',
      traceId: 'trace-signal',
      symbol: 'ETHUSDT'
    })
    expect(rows[3]).toMatchObject({
      feedType: 'event',
      traceId: 'trace-event'
    })
  })

  it('uses decision execution status before raw action text in runtime feed rows', () => {
    const rows = buildRuntimeFeedRows({
      recentDecisions: [
        {
          createdAt: '2026-04-15T10:00:00Z',
          traceId: 'trace-decision',
          symbol: 'BTCUSDT',
          action: 'OPEN_LONG',
          executionStatus: 'filled',
          orderStatus: 'FILLED'
        }
      ]
    })

    expect(rows).toHaveLength(1)
    expect(rows[0]).toMatchObject({
      feedType: 'decision',
      traceId: 'trace-decision',
      status: 'filled'
    })
  })
})

describe('getDashboardShortcutPath', () => {
  it('routes cutover shortcuts to new runtime pages', () => {
    expect(getDashboardShortcutPath('strategy')).toBe('/dca/trade/strategy')
    expect(getDashboardShortcutPath('runtime')).toBe('/dca/trade/runtime')
    expect(getDashboardShortcutPath('market-api')).toBe('/dca/market')
    expect(getDashboardShortcutPath('source-binding')).toBe('/dca/market?tab=bindings')
    expect(getDashboardShortcutPath('accounts')).toBe('/dca/trade/account')
    expect(getDashboardShortcutPath('notify-policy')).toBe('/dca/trade/notify-policy')
    expect(getDashboardShortcutPath('notify-channels')).toBe('/dca/notify')
    expect(getDashboardShortcutPath('notify-records')).toBe('/dca/notify/record')
    expect(getDashboardShortcutPath('replay')).toBe('/dca/trade/replay')
    expect(getDashboardShortcutPath('risk-hits')).toBe('/dca/trade/risk-hits')
    expect(getDashboardShortcutPath('fills')).toBe('/dca/trade/fills')
    expect(getDashboardShortcutPath('orders')).toBe('/dca/trade/orders')
    expect(getDashboardShortcutPath('positions')).toBe('/dca/trade/positions')
  })
})
