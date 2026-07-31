import { describe, expect, it } from 'vitest'

import {
  buildTradeStrategyBindingsPayload,
  buildTradeStrategyPayload,
  createTradeStrategyBindingRows,
  createTradeStrategyForm,
  formatVersionConfig,
  summarizeTradeStrategyConfig
} from '../index.vue'

describe('createTradeStrategyForm', () => {
  it('hydrates editable fields from row payload', () => {
    expect(
      createTradeStrategyForm({
        id: 4,
        strategyKey: 'btc-breakout',
        strategyName: 'BTC Breakout',
        runtimeMode: 'shadow',
        symbolsJson: '["BTCUSDT","ETHUSDT"]',
        exchangesJson: '["BINANCE","OKX"]',
        configJson: '{"aiModelId":31,"strategyKey":"btc-breakout","triggerPolicy":{"wyckoffShortterm":{"requireRetestForReady":true,"maxReadyExtensionPct":0.8,"trapVolumeRatio":2.1,"trapWickRatio":0.5,"trapCooldownBars":3}}}',
        enabled: true
      })
    ).toEqual({
      id: 4,
      strategyKey: 'btc-breakout',
      strategyName: 'BTC Breakout',
      runtimeMode: 'shadow',
      symbols: ['BTCUSDT', 'ETHUSDT'],
      exchanges: ['BINANCE', 'OKX'],
      marketDataConfigId: null,
      riskMaxPositionRatio: null,
      riskMaxDailyLoss: null,
      riskMaxConsecutiveFailures: null,
      triggerPolicyMode: '',
      wyckoffOverrideEnabled: true,
      wyckoffRequireRetestForReady: true,
      wyckoffMaxReadyExtensionPct: 0.8,
      wyckoffTrapVolumeRatio: 2.1,
      wyckoffTrapWickRatio: 0.5,
      wyckoffTrapCooldownBars: 3,
      supervisorPolicyMode: '',
      configJson: '',
      enabled: true
    })
  })
})

describe('buildTradeStrategyPayload', () => {
  it('serializes multiline scope input into JSON arrays', () => {
    expect(
      buildTradeStrategyPayload({
        id: 4,
        strategyKey: 'btc-breakout',
        strategyName: 'BTC Breakout',
        runtimeMode: ' LIVE ',
        symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
        exchanges: ['BINANCE', 'OKX'],
        riskMaxPositionRatio: 0.2,
        triggerPolicyMode: 'RULE_ONLY',
        supervisorPolicyMode: 'RULE_ONLY',
        wyckoffOverrideEnabled: true,
        wyckoffRequireRetestForReady: true,
        wyckoffMaxReadyExtensionPct: 0.8,
        wyckoffTrapVolumeRatio: 2.1,
        wyckoffTrapWickRatio: 0.5,
        wyckoffTrapCooldownBars: 3,
        configJson: '{\n  "specialistRouting": {\n    "market_agent": [\n      "market"\n    ]\n  }\n}',
        enabled: 1
      })
    ).toEqual({
      id: 4,
      strategyKey: 'btc-breakout',
      strategyName: 'BTC Breakout',
      runtimeMode: 'live',
      symbolsJson: '["BTCUSDT","ETHUSDT","SOLUSDT"]',
      exchangesJson: '["BINANCE","OKX"]',
      configJson: '{"specialistRouting":{"market_agent":["market"]},"riskConfig":{"maxPositionRatio":0.2},"triggerPolicy":{"mode":"RULE_ONLY","wyckoffShortterm":{"requireRetestForReady":true,"maxReadyExtensionPct":0.8,"trapVolumeRatio":2.1,"trapWickRatio":0.5,"trapCooldownBars":3}},"supervisorPolicy":{"enabledWhen":"RULE_ONLY"}}',
      enabled: true
    })
  })
})

describe('formatVersionConfig', () => {
  it('pretty prints stored version config JSON', () => {
    expect(formatVersionConfig({ symbolsJson: '["BTCUSDT"]' })).toContain('\n')
  })
})

describe('summarizeTradeStrategyConfig', () => {
  it('extracts trigger policy guidance from version config json', () => {
    expect(
      summarizeTradeStrategyConfig(
        JSON.stringify({
          triggerPolicy: { mode: 'RULE_ONLY' },
          supervisorPolicy: { enabledWhen: 'EVENT_GATED' },
          specialistRouting: {
            market_agent: ['market'],
            news_agent: ['news']
          },
          signalMemoryOverrides: {
            news: { ttlSeconds: 1200 }
          },
          triggerMatrixOverrides: [
            { code: 'strong_news_then_break' }
          ]
        })
      )
    ).toEqual({
      triggerPolicyMode: 'RULE_ONLY',
      supervisorPolicyMode: 'EVENT_GATED',
      wyckoffShorttermEnabled: false,
      specialistRouting: ['market_agent', 'news_agent'],
      signalMemoryOverrides: ['news'],
      triggerMatrixOverridesCount: 1
    })
  })
})

describe('createTradeStrategyBindingRows', () => {
  it('maps existing accounts into editable binding rows for strategy exchanges', () => {
    expect(
      createTradeStrategyBindingRows(
        {
          exchangesJson: '["BINANCE","OKX"]'
        },
        [
          { id: 10, exchangeCode: 'BINANCE', accountName: 'Main', enabled: true },
          { id: 11, exchangeCode: 'BYBIT', accountName: 'Ignore', enabled: true },
          { id: 12, exchangeCode: 'OKX', accountName: 'Backup', enabled: false }
        ],
        [
          { accountId: 10, exchangeCode: 'BINANCE', enabled: true },
          { accountId: 12, exchangeCode: 'OKX', enabled: false }
        ]
      )
    ).toEqual([
      {
        accountId: 10,
        exchangeCode: 'BINANCE',
        accountName: 'Main',
        accountEnabled: true,
        bindingEnabled: true
      },
      {
        accountId: 12,
        exchangeCode: 'OKX',
        accountName: 'Backup',
        accountEnabled: false,
        bindingEnabled: false
      }
    ])
  })
})

describe('buildTradeStrategyBindingsPayload', () => {
  it('serializes only selected binding rows back to controller payload shape', () => {
    expect(
      buildTradeStrategyBindingsPayload([
        { accountId: 10, exchangeCode: 'BINANCE', bindingEnabled: true },
        { accountId: 12, exchangeCode: 'OKX', bindingEnabled: false }
      ])
    ).toEqual([
      { accountId: 10, exchangeCode: 'BINANCE', enabled: true }
    ])
  })
})
