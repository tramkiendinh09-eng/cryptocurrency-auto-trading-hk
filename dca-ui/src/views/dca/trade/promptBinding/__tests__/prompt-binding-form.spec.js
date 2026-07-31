import { describe, expect, it } from 'vitest'

import {
  buildTradePromptBindingPayload,
  createTradePromptBindingForm,
  validateTradePromptBindingPayload
} from '../index.vue'

describe('createTradePromptBindingForm', () => {
  it('hydrates existing prompt binding scopes for editing', () => {
    expect(
      createTradePromptBindingForm({
        id: 12,
        bindingName: 'Supervisor Shadow Binding',
        strategyId: 7,
        strategyVersionId: 11,
        symbol: 'BTCUSDT',
        exchangeCode: 'BINANCE',
        bindingScope: 'SUPERVISOR',
        templateCode: 'trade.supervisor.v1',
        fallbackTemplateCode: 'trade.supervisor.fallback',
        modelId: 21,
        outputSchemaCode: 'supervisor_decision_v1',
        priority: 90,
        modeScopeJson: '["shadow","live"]',
        eventStrengthScopeJson: '["strong","normal"]',
        enabled: true,
        remark: 'use exact binding first'
      })
    ).toMatchObject({
      id: 12,
      bindingName: 'Supervisor Shadow Binding',
      strategyId: 7,
      strategyVersionId: 11,
      symbol: 'BTCUSDT',
      exchangeCode: 'BINANCE',
      bindingScope: 'SUPERVISOR',
      templateCode: 'trade.supervisor.v1',
      fallbackTemplateCode: 'trade.supervisor.fallback',
      modelId: 21,
      outputSchemaCode: 'supervisor_decision_v1',
      priority: 90,
      runtimeModes: ['shadow', 'live'],
      eventStrengths: ['strong', 'normal'],
      enabled: true,
      remark: 'use exact binding first'
    })
  })
})

describe('buildTradePromptBindingPayload', () => {
  it('normalizes prompt binding form into db-ready payload', () => {
    expect(
      buildTradePromptBindingPayload({
        id: 12,
        bindingName: ' Supervisor Shadow Binding ',
        strategyId: 7,
        strategyVersionId: 11,
        symbol: ' btcusdt ',
        exchangeCode: ' binance ',
        bindingScope: ' supervisor ',
        templateCode: ' trade.supervisor.v1 ',
        fallbackTemplateCode: ' trade.supervisor.fallback ',
        modelId: 21,
        outputSchemaCode: ' supervisor_decision_v1 ',
        priority: ' 90 ',
        runtimeModes: [' shadow ', 'LIVE'],
        eventStrengths: [' strong ', 'NORMAL'],
        enabled: 1,
        remark: ' exact binding '
      })
    ).toEqual({
      id: 12,
      bindingName: 'Supervisor Shadow Binding',
      strategyId: 7,
      strategyVersionId: 11,
      symbol: 'BTCUSDT',
      exchangeCode: 'BINANCE',
      bindingScope: 'SUPERVISOR',
      templateCode: 'trade.supervisor.v1',
      fallbackTemplateCode: 'trade.supervisor.fallback',
      modelId: 21,
      outputSchemaCode: 'supervisor_decision_v1',
      priority: 90,
      modeScopeJson: '["shadow","live"]',
      eventStrengthScopeJson: '["strong","normal"]',
      enabled: true,
      remark: 'exact binding'
    })
  })

  it('drops stale model references that are no longer selectable', () => {
    expect(
      buildTradePromptBindingPayload(
        {
          bindingName: 'Supervisor Shadow Binding',
          bindingScope: 'SUPERVISOR',
          templateCode: 'trade.supervisor.v1',
          modelId: 21,
          outputSchemaCode: 'supervisor_decision_v1',
          runtimeModes: ['shadow'],
          eventStrengths: ['strong'],
          enabled: true
        },
        {
          modelOptions: [{ id: 8 }, { id: 9 }]
        }
      )
    ).toMatchObject({
      modelId: null
    })
  })

  it('allows model-only override without template or schema', () => {
    expect(
      buildTradePromptBindingPayload({
        bindingName: 'Market Model Override',
        bindingScope: 'market_agent',
        modelId: 21,
        runtimeModes: ['shadow'],
        eventStrengths: ['strong'],
        enabled: true
      })
    ).toMatchObject({
      bindingName: 'Market Model Override',
      bindingScope: 'MARKET_AGENT',
      templateCode: null,
      fallbackTemplateCode: null,
      modelId: 21,
      outputSchemaCode: null
    })
  })
})

describe('validateTradePromptBindingPayload', () => {
  it('rejects unsupported v1 symbols and schema mismatches', () => {
    expect(() =>
      validateTradePromptBindingPayload({
        bindingName: 'Bad Binding',
        bindingScope: 'SUPERVISOR',
        templateCode: 'trade.supervisor.v1',
        outputSchemaCode: 'agent_view_v1',
        symbol: 'XRPUSDT',
        exchangeCode: 'BINANCE',
        runtimeModes: ['shadow'],
        eventStrengths: ['strong']
      })
    ).toThrow(/XRPUSDT|输出模式/)
  })

  it('requires at least one runtime mode and event strength', () => {
    expect(() =>
      validateTradePromptBindingPayload({
        bindingName: 'Supervisor Binding',
        bindingScope: 'SUPERVISOR',
        templateCode: 'trade.supervisor.v1',
        outputSchemaCode: 'supervisor_decision_v1',
        runtimeModes: [],
        eventStrengths: []
      })
    ).toThrow(/运行模式|事件强度/)
  })

  it('rejects template codes that are not present in current template options', () => {
    expect(() =>
      validateTradePromptBindingPayload(
        {
          bindingName: 'Supervisor Binding',
          bindingScope: 'SUPERVISOR',
          templateCode: 'trade.supervisor.missing',
          outputSchemaCode: 'supervisor_decision_v1',
          runtimeModes: ['shadow'],
          eventStrengths: ['normal']
        },
        {
          templateOptions: [{ code: 'trade.supervisor.v1' }]
        }
      )
    ).toThrow(/模板/)
  })

  it('validates model-only override as an optional advanced override rule', () => {
    expect(
      validateTradePromptBindingPayload({
        bindingName: 'Market Model Override',
        bindingScope: 'MARKET_AGENT',
        modelId: 21,
        runtimeModes: ['shadow'],
        eventStrengths: ['strong'],
        enabled: true
      })
    ).toMatchObject({
      modelId: 21,
      templateCode: null,
      outputSchemaCode: null
    })
  })
})
