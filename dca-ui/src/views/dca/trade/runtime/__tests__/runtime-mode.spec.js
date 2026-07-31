import { describe, expect, it } from 'vitest'

import {
  buildActiveSignalWindowRows,
  buildDispatchOverviewCards,
  buildExecutionSummary,
  buildRecentTradeActionRows,
  buildRuntimeConfigPayload,
  buildRuntimeFlagsPayload,
  buildRuntimeModeSummary,
  buildSummaryCards,
  createRuntimeConfigForm,
  executionStatusTag,
  formatExecutionTotalLabel,
  formatOrderExecutionMeta,
  formatModeTag,
  parseOverviewJson,
  runtimeFlagsJsonExample,
  runtimeFlagsJsonGuideSections,
  resolveEffectiveRuntimeMode,
  validateRuntimeConfigPayload
} from '../index.vue'

describe('formatModeTag', () => {
  it('maps live mode to danger tag', () => {
    expect(formatModeTag('live')).toBe('danger')
  })
})

describe('resolveEffectiveRuntimeMode', () => {
  it('downgrades requested live mode to shadow when live trading is disabled', () => {
    expect(resolveEffectiveRuntimeMode({ defaultMode: 'live', liveEnabled: false })).toBe('shadow')
  })

  it('keeps requested mode when no downgrade is required', () => {
    expect(resolveEffectiveRuntimeMode({ defaultMode: 'shadow', liveEnabled: false })).toBe('shadow')
  })
})

describe('buildRuntimeModeSummary', () => {
  it('explains live-to-shadow downgrade semantics for operators', () => {
    expect(buildRuntimeModeSummary({ defaultMode: 'live', liveEnabled: false })).toEqual({
      requestedMode: 'live',
      effectiveMode: 'shadow',
      modeDowngraded: true,
      summary: '已请求实盘，但因实盘交易未启用，当前生效为影子模式'
    })
  })

  it('keeps healthy-live guard context when live mode is effective', () => {
    expect(
      buildRuntimeModeSummary({
        defaultMode: 'live',
        liveEnabled: true,
        liveOrderRequiresHealthyAccount: true
      })
    ).toEqual({
      requestedMode: 'live',
      effectiveMode: 'live',
      modeDowngraded: false,
      summary: '当前为实盘模式，且要求账户处于健康状态'
    })
  })
})

describe('buildSummaryCards', () => {
  it('builds operator console cards from overview payload', () => {
    const cards = buildSummaryCards({
      eventCount: 8,
      signalCount: 5,
      decisionCount: 3,
      riskHitCount: 1,
      activePositionCount: 2,
      totalUnrealizedPnl: '12.50',
      latestDailyPnl: '120.50',
      maxDrawdownPct: '4.25'
    })

    expect(cards).toHaveLength(8)
    expect(cards[0]).toMatchObject({ key: 'events', value: '8' })
    expect(cards[3]).toMatchObject({ key: 'riskHits', tone: 'danger' })
    expect(cards[5]).toMatchObject({ key: 'unrealizedPnl', value: '+12.5000' })
    expect(cards[6]).toMatchObject({ key: 'dailyPnl', value: '+120.5000' })
    expect(cards[7]).toMatchObject({ key: 'maxDrawdownPct', value: '4.25%', tone: 'warning' })
  })
})

describe('dispatch overview helpers', () => {
  it('parses stored json fragments for selected agents and combinations', () => {
    expect(parseOverviewJson('["market_agent","news_agent"]', [])).toEqual(['market_agent', 'news_agent'])
    expect(parseOverviewJson('{"code":"strong_news_then_break"}', {})).toEqual({ code: 'strong_news_then_break' })
  })

  it('builds dispatch overview cards from overview payload', () => {
    expect(
      buildDispatchOverviewCards({
        latestDispatchMode: 'RULE_ONLY',
        lastTriggerReason: 'budget_blocked',
        lastTriggerSource: 'news',
        cooldownSuppressionCount: 2,
        budgetSuppressionCount: 3,
        activeSignalWindows: [{ windowKey: 'news:BTCUSDT:15m' }]
      })
    ).toEqual([
      { key: 'dispatchMode', label: '分发模式', value: 'RULE_ONLY' },
      { key: 'triggerReason', label: '最近触发原因', value: 'budget_blocked' },
      { key: 'triggerSource', label: '最近触发来源', value: 'news' },
      { key: 'cooldownSuppressionCount', label: '冷却拦截次数', value: '2' },
      { key: 'budgetSuppressionCount', label: '预算拦截次数', value: '3' },
      { key: 'activeSignalWindows', label: '活跃窗口数', value: '1' }
    ])
  })
})

describe('buildActiveSignalWindowRows', () => {
  it('builds operator-friendly signal window lifecycle rows', () => {
    expect(
      buildActiveSignalWindowRows([
        {
          windowKey: 'news:BTCUSDT:15m',
          sourceType: 'news',
          signalType: 'headline',
          direction: 'bullish',
          strengthScore: 0.82,
          active: true,
          expiresAt: '2099-01-01T00:00:00Z'
        }
      ])
    ).toEqual([
      expect.objectContaining({
        windowKey: 'news:BTCUSDT:15m',
        sourceTypeLabel: 'NEWS',
        signalTypeLabel: 'headline',
        directionLabel: 'bullish',
        strengthScoreLabel: '0.82',
        statusText: 'active'
      })
    ])
  })
})

describe('executionStatusTag', () => {
  it('maps partial execution to warning', () => {
    expect(executionStatusTag('partial')).toBe('warning')
  })

  it('maps blocked and skipped business states distinctly', () => {
    expect(executionStatusTag('blocked')).toBe('danger')
    expect(executionStatusTag('skipped')).toBe('info')
  })
})

describe('buildExecutionSummary', () => {
  it('builds execution status summary cards from overview payload', () => {
    const cards = buildExecutionSummary({
      total: 10,
      filled: 4,
      submitted: 2,
      pending: 1,
      partial: 1,
      canceled: 0,
      expired: 0,
      failed: 1,
      blocked: 1,
      skipped: 1
    })

    expect(cards).toHaveLength(9)
    expect(cards[0]).toMatchObject({ key: 'filled', value: '4', tone: 'success' })
    expect(cards[1]).toMatchObject({ key: 'submitted', value: '2', tone: 'warning' })
    expect(cards[3]).toMatchObject({ key: 'partial', value: '1', tone: 'warning' })
    expect(cards[6]).toMatchObject({ key: 'failed', value: '1', tone: 'danger' })
    expect(cards[7]).toMatchObject({ key: 'blocked', value: '1', tone: 'danger' })
    expect(cards[8]).toMatchObject({ key: 'skipped', value: '1', tone: 'info' })
  })
})

describe('formatExecutionTotalLabel', () => {
  it('formats total execution count for operator header', () => {
    expect(formatExecutionTotalLabel({ total: 8 })).toBe('总计 8')
  })
})

describe('formatOrderExecutionMeta', () => {
  it('formats enhanced OKX execution metadata for recent orders', () => {
    expect(
      formatOrderExecutionMeta({
        action: 'OPEN',
        orderType: 'limit',
        positionSide: 'long',
        reduceOnly: true,
        tdMode: 'cross',
        leverage: 3,
        limitPrice: '65000.10000000',
        quantityBase: '0.05000000',
        okxEnhancedExecution: true
      })
    ).toBe('OPEN / limit / long / reduceOnly=true / cross / 3x / px 65000.10000000 / qty 0.05000000 / OKX+')
  })

  it('shows false reduceOnly explicitly for audit clarity', () => {
    expect(formatOrderExecutionMeta({ action: 'OPEN', reduceOnly: false })).toBe('OPEN / reduceOnly=false')
  })

  it('keeps legacy orders compact when no metadata exists', () => {
    expect(formatOrderExecutionMeta({})).toBe('-')
  })
})

describe('buildRecentTradeActionRows', () => {
  it('formats actionable open close and realized pnl fields for runtime trade summaries', () => {
    expect(
      buildRecentTradeActionRows([
        {
          traceId: 'trace-short-open-1',
          action: 'OPEN_SHORT',
          positionSide: 'short',
          fillPrice: '2371.05000000',
          fillQuantity: '1.50000000',
          openPrice: '2371.05000000',
          closePrice: null,
          realizedPnl: '0'
        },
        {
          traceId: 'trace-short-close-1',
          action: 'CLOSE',
          positionSide: 'short',
          fillPrice: '2362.05000000',
          fillQuantity: '1.50000000',
          openPrice: '2371.05000000',
          closePrice: '2362.05000000',
          realizedPnl: '13.50000000'
        }
      ])
    ).toEqual([
      expect.objectContaining({
        traceId: 'trace-short-open-1',
        positionSide: 'short',
        openPriceLabel: '2371.05000000',
        closePriceLabel: '-',
        fillPriceLabel: '2371.05000000',
        fillQuantityLabel: '1.50000000',
        realizedPnlLabel: '0.0000',
        realizedPnlTone: 'neutral'
      }),
      expect.objectContaining({
        traceId: 'trace-short-close-1',
        positionSide: 'short',
        openPriceLabel: '2371.05000000',
        closePriceLabel: '2362.05000000',
        fillPriceLabel: '2362.05000000',
        fillQuantityLabel: '1.50000000',
        realizedPnlLabel: '+13.5000',
        realizedPnlTone: 'success'
      })
    ])
  })
})

describe('createRuntimeConfigForm', () => {
  it('creates editable form state from runtime config', () => {
    expect(
      createRuntimeConfigForm({
        id: 9,
        defaultMode: 'shadow',
        liveEnabled: true,
        maxPositionRatio: 0.35,
        maxDailyLoss: -650,
        maxConsecutiveFailures: 5,
        allowedSymbolsJson: '["BTCUSDT","ETHUSDT"]',
        allowedExchangesJson: '["BINANCE","OKX"]',
        requireAccountBinding: true,
        liveOrderRequiresHealthyAccount: true,
        runtimeFlagsJson: '{"haltOnDataGap":true}',
        marketDataEnhancement: {
          enabled: true,
          restFallbackEnabled: true,
          klineEnabled: true,
          klineIntervals: ['1m', '15m'],
          klineLimit: 80,
          liquidationAggregateWindowsMinutes: [15, 60, 240]
        },
        wyckoffShortterm: {
          enabled: true,
          min15mBars: 10,
          effortLookbackBars: 5,
          breakoutChangePct: 0.2,
          breakoutVolumeRatio: 1.0,
          confirmedBreakoutChangePct: 0.4,
          confirmedBreakoutVolumeRatio: 1.3,
          springChangePct: 0.1,
          springVolumeRatio: 1.0,
          higherTimeframeConflictPct: 0.2,
          higherTimeframeConfirmPct: 0.4,
          rangeBalanceChangePct: 0.5,
          rangeBalanceRangePct: 2.2,
          markDeviationPenaltyPct: 0.4,
          requireRetestForReady: true,
          retestMaxDistancePct: 0.3,
          maxReadyExtensionPct: 0.8,
          trapVolumeRatio: 2.0,
          trapWickRatio: 0.5,
          trapCooldownBars: 3
        },
        triggerMode: 'EVENT_GATED',
        marketTrigger: {
          ruleOnlyPriceChangePct: 1.0,
          priceChangePct: 3.5,
          priceAccelerationPct: 1.8,
          liquidationNotionalUsd: 350000,
          klinePriceChangePct15m: 1.2,
          klinePriceChangePct60m: 2.4,
          klinePriceChangePct240m: 4.8,
          liquidationNotional15mUsd: 150000,
          liquidationNotional60mUsd: 300000,
          liquidationNotional240mUsd: 600000,
          fundingRateAbs: 0.001,
          markPriceDeviationPct: 1.2
        },
        newsTrigger: {
          scoreThreshold: 0.88,
          severityThreshold: 'critical'
        },
        signalMemoryPolicy: {
          market: { ttlSeconds: 240, decayMode: 'linear', combineWithinSeconds: 120 },
          news: { ttlSeconds: 1200, decayMode: 'linear', combineWithinSeconds: 900 },
          onchain: { ttlSeconds: 3600, decayMode: 'step', combineWithinSeconds: 2400 },
          social: { ttlSeconds: 600, decayMode: 'linear', combineWithinSeconds: 600 }
        },
        triggerMatrix: [
          { code: 'strong_news_then_break', sources: ['news', 'market'], targetDispatchMode: 'LLM_ALLOWED' }
        ],
        cooldownPolicy: {
          globalSeconds: 420,
          sameSourceSeconds: 240,
          replayBypass: true
        },
        llmBudgetPolicy: {
          perSymbolDailyLimit: 8,
          rollingWindowMinutes: 90,
          rollingWindowLimit: 3,
          exhaustToRuleOnly: true
        },
        dedupePolicy: {
          sameDirectionOnly: true,
          dedupeWindowSeconds: 360,
          preferHigherStrength: true
        },
        notifyDefaultsJson: '{"channels":["OPS"]}',
        eventRetentionDays: 45,
        replayRetentionDays: 15,
        routeSchedulerMode: 'THREAD_POOL',
        routeMaxConcurrency: 4,
        deliberationEnabled: true,
        deliberationMaxRounds: 1,
        deliberationFailOpen: false
      })
    ).toEqual({
      id: 9,
      defaultMode: 'shadow',
      liveEnabled: true,
      maxPositionRatio: 0.35,
      maxDailyLoss: -650,
      maxConsecutiveFailures: 5,
      allowedSymbols: ['BTCUSDT', 'ETHUSDT'],
      allowedExchanges: ['BINANCE', 'OKX'],
      requireAccountBinding: true,
      liveOrderRequiresHealthyAccount: true,
      runtimeFlagsJson: '{\n  "haltOnDataGap": true\n}',
      marketDataEnhancementEnabled: true,
      marketDataRestFallbackEnabled: true,
      marketDataKlineEnabled: true,
      marketDataKlineIntervalsText: '1m, 15m',
      marketDataKlineLimit: 80,
      marketDataLiquidationWindowsText: '15, 60, 240',
      haltOnDataGap: true,
      triggerMode: 'EVENT_GATED',
      marketTriggerRuleOnlyPriceChangePct: 1.0,
      marketTriggerPriceChangePct: 3.5,
      marketTriggerPriceAccelerationPct: 1.8,
      marketTriggerLiquidationNotionalUsd: 350000,
      marketTriggerKlinePriceChangePct15m: 1.2,
      marketTriggerKlinePriceChangePct60m: 2.4,
      marketTriggerKlinePriceChangePct240m: 4.8,
      marketTriggerLiquidationNotional15mUsd: 150000,
      marketTriggerLiquidationNotional60mUsd: 300000,
      marketTriggerLiquidationNotional240mUsd: 600000,
      marketTriggerFundingRateAbs: 0.001,
      marketTriggerMarkPriceDeviationPct: 1.2,
      supervisorAiFailOpen: false,
      wyckoffShorttermEnabled: true,
      wyckoffShorttermMin15mBars: 10,
      wyckoffShorttermEffortLookbackBars: 5,
      wyckoffShorttermBreakoutChangePct: 0.2,
      wyckoffShorttermBreakoutVolumeRatio: 1.0,
      wyckoffShorttermConfirmedBreakoutChangePct: 0.4,
      wyckoffShorttermConfirmedBreakoutVolumeRatio: 1.3,
      wyckoffShorttermSpringChangePct: 0.1,
      wyckoffShorttermSpringVolumeRatio: 1.0,
      wyckoffShorttermHigherTimeframeConflictPct: 0.2,
      wyckoffShorttermHigherTimeframeConfirmPct: 0.4,
      wyckoffShorttermRangeBalanceChangePct: 0.5,
      wyckoffShorttermRangeBalanceRangePct: 2.2,
      wyckoffShorttermMarkDeviationPenaltyPct: 0.4,
      wyckoffShorttermRequireRetestForReady: true,
      wyckoffShorttermRetestMaxDistancePct: 0.3,
      wyckoffShorttermMaxReadyExtensionPct: 0.8,
      wyckoffShorttermTrapVolumeRatio: 2.0,
      wyckoffShorttermTrapWickRatio: 0.5,
      wyckoffShorttermTrapCooldownBars: 3,
      newsTriggerScoreThreshold: 0.88,
      newsTriggerSeverityThreshold: 'critical',
      onchainTriggerFlowUsdThreshold: 500000,
      onchainTriggerExchangeNetflowBias: 0.65,
      socialTriggerScoreThreshold: 0.75,
      socialTriggerBurstCount: 3,
      signalMemoryRows: [
        { source: 'market', ttlSeconds: 240, decayMode: 'linear', combineWithinSeconds: 120 },
        { source: 'news', ttlSeconds: 1200, decayMode: 'linear', combineWithinSeconds: 900 },
        { source: 'onchain', ttlSeconds: 3600, decayMode: 'step', combineWithinSeconds: 2400 },
        { source: 'social', ttlSeconds: 600, decayMode: 'linear', combineWithinSeconds: 600 }
      ],
      triggerMatrixRows: [
        { code: 'strong_news_then_break', sourcesText: 'news, market', targetDispatchMode: 'LLM_ALLOWED' }
      ],
      cooldownGlobalSeconds: 420,
      cooldownSameSourceSeconds: 240,
      cooldownReplayBypass: true,
      llmBudgetPerSymbolDailyLimit: 8,
      llmBudgetRollingWindowMinutes: 90,
      llmBudgetRollingWindowLimit: 3,
      llmBudgetExhaustToRuleOnly: true,
      dedupeSameDirectionOnly: true,
      dedupeWindowSeconds: 360,
      dedupePreferHigherStrength: true,
      notifyDefaultsJson: '{\n  "channels": [\n    "OPS"\n  ]\n}',
      eventRetentionDays: 45,
      replayRetentionDays: 15,
      routeSchedulerMode: 'THREAD_POOL',
      routeMaxConcurrency: 4,
      deliberationEnabled: true,
      deliberationMaxRounds: 1,
      deliberationFailOpen: false
    })
  })
})

describe('buildRuntimeFlagsPayload', () => {
  it('serializes structured trigger policy fields into runtime flags json payload', () => {
    expect(
      buildRuntimeFlagsPayload({
        runtimeFlagsJson: '{"legacyFlag":true}',
        haltOnDataGap: true,
        triggerMode: 'EVENT_GATED',
        marketTriggerRuleOnlyPriceChangePct: 1.0,
        marketTriggerPriceChangePct: 2.8,
        marketTriggerPriceAccelerationPct: 1.1,
        marketTriggerLiquidationNotionalUsd: 260000,
        marketTriggerKlinePriceChangePct15m: 1.5,
        marketTriggerKlinePriceChangePct60m: 2.5,
        marketTriggerKlinePriceChangePct240m: 5,
        marketTriggerLiquidationNotional15mUsd: 150000,
        marketTriggerLiquidationNotional60mUsd: 300000,
        marketTriggerLiquidationNotional240mUsd: 600000,
        marketTriggerFundingRateAbs: 0.001,
        marketDataEnhancementEnabled: true,
        marketDataRestFallbackEnabled: true,
        marketDataKlineEnabled: true,
        marketDataKlineIntervalsText: '1m, 15m, 1h',
        marketDataKlineLimit: 80,
        marketDataLiquidationWindowsText: '15,60,240',
        marketTriggerMarkPriceDeviationPct: 1.2,
        supervisorAiFailOpen: true,
        newsTriggerScoreThreshold: 0.81,
        newsTriggerSeverityThreshold: 'high',
        onchainTriggerFlowUsdThreshold: 510000,
        onchainTriggerExchangeNetflowBias: 0.66,
        socialTriggerScoreThreshold: 0.79,
        socialTriggerBurstCount: 5,
        signalMemoryRows: [
          { source: 'market', ttlSeconds: 180, decayMode: 'linear', combineWithinSeconds: 120 }
        ],
        triggerMatrixRows: [
          { code: 'strong_news_then_break', sourcesText: 'news, market', targetDispatchMode: 'LLM_ALLOWED' }
        ],
        cooldownGlobalSeconds: 300,
        cooldownSameSourceSeconds: 180,
        cooldownReplayBypass: true,
        llmBudgetPerSymbolDailyLimit: 6,
        llmBudgetRollingWindowMinutes: 60,
        llmBudgetRollingWindowLimit: 2,
        llmBudgetExhaustToRuleOnly: true,
        dedupeSameDirectionOnly: true,
        dedupeWindowSeconds: 300,
        dedupePreferHigherStrength: true
      })
    ).toMatchObject({
      legacyFlag: true,
      haltOnDataGap: true,
      triggerMode: 'EVENT_GATED',
      marketTrigger: {
        ruleOnlyPriceChangePct: 1.0,
        priceChangePct: 2.8,
        klinePriceChangePct15m: 1.5,
        liquidationNotional60mUsd: 300000,
        fundingRateAbs: 0.001,
        markPriceDeviationPct: 1.2
      },
      supervisorAiFailOpen: true,
      marketDataEnhancement: {
        enabled: true,
        restFallbackEnabled: true,
        klineEnabled: true,
        klineIntervals: ['1m', '15m', '1h'],
        klineLimit: 80,
        liquidationAggregateWindowsMinutes: [15, 60, 240]
      },
      triggerMatrix: [
        { code: 'strong_news_then_break', sources: ['news', 'market'], targetDispatchMode: 'LLM_ALLOWED' }
      ]
    })
  })

  it('keeps trigger matrix compatibility with legacy upgradeTo payloads', () => {
    const form = createRuntimeConfigForm({
      runtimeFlagsJson: JSON.stringify({
        triggerMatrix: [
          { code: 'news_onchain_market_confirmation', sources: ['news', 'onchain', 'market'], upgradeTo: 'LLM_ALLOWED' }
        ]
      })
    })

    expect(form.triggerMatrixRows).toEqual([
      {
        code: 'news_onchain_market_confirmation',
        sourcesText: 'news, onchain, market',
        targetDispatchMode: 'LLM_ALLOWED'
      }
    ])

    expect(
      buildRuntimeFlagsPayload({
        runtimeFlagsJson: '{}',
        triggerMatrixRows: form.triggerMatrixRows
      })
    ).toMatchObject({
      triggerMatrix: [
        {
          code: 'news_onchain_market_confirmation',
          sources: ['news', 'onchain', 'market'],
          targetDispatchMode: 'LLM_ALLOWED',
          upgradeTo: 'LLM_ALLOWED'
        }
      ]
    })
  })

  it('serializes now-active market trigger keys from structured form fields', () => {
    expect(
      buildRuntimeFlagsPayload({
        runtimeFlagsJson: JSON.stringify({
          marketTrigger: {
            ruleOnlyPriceChangePct: 1.0
          }
        }),
        marketTriggerRuleOnlyPriceChangePct: 0.8,
        marketTriggerPriceChangePct: 2.8,
        marketTriggerPriceAccelerationPct: 1.1,
        marketTriggerLiquidationNotionalUsd: 260000,
        marketTriggerKlinePriceChangePct15m: 1.2,
        marketTriggerKlinePriceChangePct60m: 2.4,
        marketTriggerKlinePriceChangePct240m: 4.8,
        marketTriggerLiquidationNotional15mUsd: 150000,
        marketTriggerLiquidationNotional60mUsd: 300000,
        marketTriggerLiquidationNotional240mUsd: 600000,
        marketTriggerFundingRateAbs: 0.001,
        marketTriggerMarkPriceDeviationPct: 1.2
      })
    ).toMatchObject({
      marketTrigger: {
        ruleOnlyPriceChangePct: 0.8,
        fundingRateAbs: 0.001,
        markPriceDeviationPct: 1.2,
        priceChangePct: 2.8,
        priceAccelerationPct: 1.1,
        liquidationNotionalUsd: 260000,
        klinePriceChangePct15m: 1.2,
        klinePriceChangePct60m: 2.4,
        klinePriceChangePct240m: 4.8,
        liquidationNotional15mUsd: 150000,
        liquidationNotional60mUsd: 300000,
        liquidationNotional240mUsd: 600000
      }
    })
  })

  it('preserves advanced market data enhancement keys while structured fields override known values', () => {
    expect(
      buildRuntimeFlagsPayload({
        runtimeFlagsJson: JSON.stringify({
          marketDataEnhancement: {
            enabled: false,
            restFallbackEnabled: false,
            customSourcePriority: ['ws', 'rest']
          }
        }),
        marketDataEnhancementEnabled: true,
        marketDataRestFallbackEnabled: true,
        marketDataKlineEnabled: true,
        marketDataKlineIntervalsText: '1m, 5m',
        marketDataKlineLimit: 60,
        marketDataLiquidationWindowsText: '15,60'
      })
    ).toMatchObject({
      marketDataEnhancement: {
        enabled: true,
        restFallbackEnabled: true,
        klineEnabled: true,
        klineIntervals: ['1m', '5m'],
        klineLimit: 60,
        liquidationAggregateWindowsMinutes: [15, 60],
        customSourcePriority: ['ws', 'rest']
      }
    })
  })

  it('serializes wyckoff short-term policy from structured fields', () => {
    expect(
      buildRuntimeFlagsPayload({
        runtimeFlagsJson: JSON.stringify({
          wyckoffShortterm: {
            customTrapNote: 'keep'
          }
        }),
        wyckoffShorttermEnabled: true,
        wyckoffShorttermMin15mBars: 9,
        wyckoffShorttermEffortLookbackBars: 5,
        wyckoffShorttermBreakoutChangePct: 0.2,
        wyckoffShorttermBreakoutVolumeRatio: 1.1,
        wyckoffShorttermConfirmedBreakoutChangePct: 0.45,
        wyckoffShorttermConfirmedBreakoutVolumeRatio: 1.4,
        wyckoffShorttermSpringChangePct: 0.12,
        wyckoffShorttermSpringVolumeRatio: 1.05,
        wyckoffShorttermHigherTimeframeConflictPct: 0.2,
        wyckoffShorttermHigherTimeframeConfirmPct: 0.4,
        wyckoffShorttermRangeBalanceChangePct: 0.5,
        wyckoffShorttermRangeBalanceRangePct: 2.4,
        wyckoffShorttermMarkDeviationPenaltyPct: 0.35,
        wyckoffShorttermRequireRetestForReady: true,
        wyckoffShorttermRetestMaxDistancePct: 0.3,
        wyckoffShorttermMaxReadyExtensionPct: 0.8,
        wyckoffShorttermTrapVolumeRatio: 2.1,
        wyckoffShorttermTrapWickRatio: 0.5,
        wyckoffShorttermTrapCooldownBars: 3
      })
    ).toMatchObject({
      wyckoffShortterm: {
        customTrapNote: 'keep',
        enabled: true,
        min15mBars: 9,
        requireRetestForReady: true,
        maxReadyExtensionPct: 0.8,
        trapVolumeRatio: 2.1,
        trapWickRatio: 0.5,
        trapCooldownBars: 3
      }
    })
  })


  it('reads supervisor fail-open from runtime flags but defaults to safe disabled', () => {
    expect(createRuntimeConfigForm({ runtimeFlagsJson: '{"supervisorAiFailOpen":true}' }).supervisorAiFailOpen).toBe(true)
    expect(createRuntimeConfigForm({ runtimeFlagsJson: '{}' }).supervisorAiFailOpen).toBe(false)
  })

  it('preserves advanced json switch values when structured switch fields are omitted', () => {
    expect(
      buildRuntimeFlagsPayload({
        runtimeFlagsJson: '{"haltOnDataGap":true,"supervisorAiFailOpen":true}'
      })
    ).toMatchObject({
      haltOnDataGap: true,
      supervisorAiFailOpen: true
    })
  })
})

describe('runtime JSON guides', () => {
  it('documents market trigger json-only fields for operators', () => {
    expect(runtimeFlagsJsonGuideSections[0].items).toContain(
      'marketTrigger.ruleOnlyPriceChangePct：弱波动阈值，低于该值时优先走规则，尽量不调 market_agent LLM。'
    )
    expect(runtimeFlagsJsonGuideSections[0].items).toContain(
      'marketTrigger.fundingRateAbs：资金费率绝对值阈值，只有达到该值才把 funding_rate 视为值得调模型的显著事件。'
    )
    expect(runtimeFlagsJsonExample).toContain('"markPriceDeviationPct": 1.0')
  })
})

describe('buildRuntimeConfigPayload', () => {
  it('normalizes runtime config form before submit', () => {
    const payload = buildRuntimeConfigPayload({
        id: 12,
        defaultMode: ' LIVE ',
        liveEnabled: 1,
        maxPositionRatio: ' 0.35 ',
        maxDailyLoss: ' -650 ',
        maxConsecutiveFailures: ' 5 ',
        allowedSymbols: [' solusdt ', 'BTCUSDT'],
        allowedExchanges: [' okx ', 'BINANCE'],
        requireAccountBinding: 1,
        liveOrderRequiresHealthyAccount: 0,
        runtimeFlagsJson: '{ "haltOnDataGap": true }',
        haltOnDataGap: false,
        notifyDefaultsJson: '{ "channels": ["OPS"] }',
        eventRetentionDays: ' 40 ',
        replayRetentionDays: ' 14 ',
        routeSchedulerMode: ' thread_pool ',
        routeMaxConcurrency: ' 3 ',
        deliberationEnabled: 1,
        deliberationMaxRounds: ' 1 ',
        deliberationFailOpen: 1,
        triggerMode: ' event_gated ',
        marketTriggerRuleOnlyPriceChangePct: ' 0.9 ',
        marketTriggerPriceChangePct: ' 3.6 ',
        marketTriggerPriceAccelerationPct: ' 1.4 ',
        marketTriggerLiquidationNotionalUsd: ' 450000 ',
        marketTriggerFundingRateAbs: ' 0.001 ',
        marketTriggerMarkPriceDeviationPct: ' 1.2 ',
        supervisorAiFailOpen: 1,
        newsTriggerScoreThreshold: ' 0.82 ',
        newsTriggerSeverityThreshold: ' critical ',
        onchainTriggerFlowUsdThreshold: ' 600000 ',
        onchainTriggerExchangeNetflowBias: ' 0.72 ',
        socialTriggerScoreThreshold: ' 0.77 ',
        socialTriggerBurstCount: ' 4 ',
        signalMemoryRows: [
          { source: 'market', ttlSeconds: ' 180 ', decayMode: 'linear', combineWithinSeconds: ' 120 ' },
          { source: 'news', ttlSeconds: ' 900 ', decayMode: 'linear', combineWithinSeconds: ' 900 ' },
          { source: 'onchain', ttlSeconds: ' 3600 ', decayMode: 'step', combineWithinSeconds: ' 2400 ' },
          { source: 'social', ttlSeconds: ' 600 ', decayMode: 'linear', combineWithinSeconds: ' 600 ' }
        ],
        triggerMatrixRows: [
          { code: 'strong_news_then_break', sourcesText: 'news, market', targetDispatchMode: ' llm_allowed ' }
        ],
        cooldownGlobalSeconds: ' 360 ',
        cooldownSameSourceSeconds: ' 180 ',
        cooldownReplayBypass: 1,
        llmBudgetPerSymbolDailyLimit: ' 7 ',
        llmBudgetRollingWindowMinutes: ' 75 ',
        llmBudgetRollingWindowLimit: ' 3 ',
        llmBudgetExhaustToRuleOnly: 1,
        dedupeSameDirectionOnly: 1,
        dedupeWindowSeconds: ' 420 ',
        dedupePreferHigherStrength: 1
      })

    expect(payload).toMatchObject({
      id: 12,
      defaultMode: 'live',
      liveEnabled: true,
      maxPositionRatio: 0.35,
      maxDailyLoss: -650,
      maxConsecutiveFailures: 5,
      allowedSymbolsJson: '["SOLUSDT","BTCUSDT"]',
      allowedExchangesJson: '["OKX","BINANCE"]',
      requireAccountBinding: true,
      liveOrderRequiresHealthyAccount: false,
      notifyDefaultsJson: '{"channels":["OPS"]}',
      eventRetentionDays: 40,
      replayRetentionDays: 14,
      routeSchedulerMode: 'THREAD_POOL',
      routeMaxConcurrency: 3,
      deliberationEnabled: true,
      deliberationMaxRounds: 1,
      deliberationFailOpen: true
    })
    expect(JSON.parse(payload.runtimeFlagsJson)).toMatchObject({
      haltOnDataGap: false,
      triggerMode: 'EVENT_GATED',
      marketTrigger: {
        ruleOnlyPriceChangePct: 0.9,
        priceChangePct: 3.6,
        priceAccelerationPct: 1.4,
        liquidationNotionalUsd: 450000,
        klinePriceChangePct15m: 1,
        liquidationNotional60mUsd: 500000,
        fundingRateAbs: 0.001,
        markPriceDeviationPct: 1.2
      },
      marketDataEnhancement: {
        enabled: true,
        restFallbackEnabled: true,
        klineEnabled: true,
        klineIntervals: ['1m', '3m', '15m', '1h', '4h'],
        klineLimit: 120,
        liquidationAggregateWindowsMinutes: [15, 60, 240]
      },
      supervisorAiFailOpen: true
    })
  })
})

describe('validateRuntimeConfigPayload', () => {
  it('rejects invalid advanced JSON blocks before submit', () => {
    expect(() =>
      validateRuntimeConfigPayload({
        allowedSymbols: ['BTCUSDT'],
        allowedExchanges: ['BINANCE'],
        runtimeFlagsJson: '{bad json}',
        notifyDefaultsJson: '{}',
        signalMemoryRows: [{ source: 'market', ttlSeconds: 120, decayMode: 'linear', combineWithinSeconds: 60 }]
      })
    ).toThrow(/运行时 Flags JSON/)
  })

  it('rejects invalid scheduler settings before submit', () => {
    expect(() =>
      validateRuntimeConfigPayload({
        allowedSymbols: ['BTCUSDT'],
        allowedExchanges: ['BINANCE'],
        runtimeFlagsJson: '{}',
        notifyDefaultsJson: '{}',
        routeSchedulerMode: 'BAD_MODE',
        routeMaxConcurrency: 0,
        deliberationMaxRounds: -1,
        signalMemoryRows: [{ source: 'market', ttlSeconds: 120, decayMode: 'linear', combineWithinSeconds: 60 }]
      })
    ).toThrow(/路由调度器/)
  })
})
