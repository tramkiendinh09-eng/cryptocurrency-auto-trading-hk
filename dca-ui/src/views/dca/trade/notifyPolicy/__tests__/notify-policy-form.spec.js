import { describe, expect, it } from 'vitest'

import {
  buildTradeNotifyPolicyPayload,
  createTradeNotifyPolicyForm,
  validateTradeNotifyPolicyPayload
} from '../index.vue'

describe('createTradeNotifyPolicyForm', () => {
  it('hydrates persisted notify policy and channel bindings for editing', () => {
    expect(
      createTradeNotifyPolicyForm({
        id: 8,
        policyName: 'Runtime Risk',
        policyScope: 'STRATEGY',
        strategyId: 7,
        eventScopeJson: '["risk_guard_hit","decision"]',
        severityScopeJson: '["ERROR","CRITICAL"]',
        modeScopeJson: '["shadow","live"]',
        throttleSeconds: 90,
        notifyTemplateCode: 'notify.runtime.risk.v1',
        enabled: true,
        channelBindings: [{ channelId: 3, channelOrder: 1, enabled: true }]
      })
    ).toMatchObject({
      id: 8,
      policyName: 'Runtime Risk',
      policyScope: 'strategy',
      strategyId: 7,
      eventScopes: ['risk_guard_hit', 'decision'],
      severityScopes: ['ERROR', 'CRITICAL'],
      modeScopes: ['shadow', 'live'],
      notifyTemplateCode: 'notify.runtime.risk.v1',
      selectedChannelIds: [3]
    })
  })
})

describe('buildTradeNotifyPolicyPayload', () => {
  it('normalizes notify policy scopes and channel rows into db-ready payload', () => {
    expect(
      buildTradeNotifyPolicyPayload({
        id: 8,
        policyName: ' Runtime Risk ',
        policyScope: ' strategy ',
        strategyId: 7,
        eventScopes: [' risk_guard_hit ', 'Decision'],
        severityScopes: [' error ', 'critical'],
        modeScopes: [' shadow ', 'LIVE'],
        throttleSeconds: 90,
        notifyTemplateCode: ' notify.runtime.risk.v1 ',
        enabled: 1,
        selectedChannelIds: [3, 5]
      })
    ).toEqual({
      id: 8,
      policyName: 'Runtime Risk',
      policyScope: 'STRATEGY',
      strategyId: 7,
      eventScopeJson: '["risk_guard_hit","decision"]',
      severityScopeJson: '["ERROR","CRITICAL"]',
      modeScopeJson: '["shadow","live"]',
      throttleSeconds: 90,
      notifyTemplateCode: 'notify.runtime.risk.v1',
      enabled: true,
      channelBindings: [
        { channelId: 3, channelOrder: 1, enabled: true },
        { channelId: 5, channelOrder: 2, enabled: true }
      ]
    })
  })
})

describe('validateTradeNotifyPolicyPayload', () => {
  it('rejects strategy-scoped policies without strategy binding', () => {
    expect(() =>
      validateTradeNotifyPolicyPayload({
        policyName: 'Runtime Risk',
        policyScope: 'STRATEGY',
        strategyId: null,
        eventScopes: ['risk_guard_hit'],
        severityScopes: ['ERROR'],
        modeScopes: ['shadow'],
        selectedChannelIds: [3]
      })
    ).toThrow(/策略/)
  })

  it('rejects policies without notify channels', () => {
    expect(() =>
      validateTradeNotifyPolicyPayload({
        policyName: 'Runtime Risk',
        policyScope: 'GLOBAL',
        eventScopes: ['decision'],
        severityScopes: ['ERROR'],
        modeScopes: ['paper']
      })
    ).toThrow(/通知渠道/)
  })

  it('rejects policies without notify template binding', () => {
    expect(() =>
      validateTradeNotifyPolicyPayload({
        policyName: 'Runtime Risk',
        policyScope: 'GLOBAL',
        eventScopes: ['decision'],
        severityScopes: ['ERROR'],
        modeScopes: ['paper'],
        selectedChannelIds: [3]
      })
    ).toThrow(/模板/)
  })
})
