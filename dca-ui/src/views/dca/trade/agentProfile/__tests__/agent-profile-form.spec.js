import { describe, expect, it } from 'vitest'

import {
  buildTradeAgentProfilePayload,
  createTradeAgentProfileForm,
  validateTradeAgentProfilePayload
} from '../index.vue'

describe('createTradeAgentProfileForm', () => {
  it('hydrates existing agent profile for editing', () => {
    expect(
      createTradeAgentProfileForm({
        id: 9,
        agentCode: 'market_agent',
        agentName: 'Market Specialist',
        agentType: 'HYBRID',
        enabled: true,
        llmEnabled: true,
        dialogueEnabled: true,
        maxDialogueRounds: 1,
        speakOrder: 20,
        timeoutSeconds: 45,
        maxRetries: 2,
        temperatureOverride: 0.25,
        topPOverride: 0.7,
        maxTokensOverride: 900,
        structuredSchemaCode: 'agent_view_v1',
        defaultModelId: 21,
        defaultTemplateCode: 'trade.market.v1',
        defaultFallbackTemplateCode: 'trade.market.fallback',
        defaultOutputSchemaCode: 'agent_view_v1',
        toolPolicyJson: '{"allow":["market_snapshot"]}',
        runtimeOptionsJson: '{"fallback":"RULE"}',
        remark: 'bounded hybrid agent'
      })
    ).toMatchObject({
      id: 9,
      agentCode: 'market_agent',
      agentName: 'Market Specialist',
      agentType: 'HYBRID',
      enabled: true,
      llmEnabled: true,
      dialogueEnabled: true,
      maxDialogueRounds: 1,
      speakOrder: 20,
      timeoutSeconds: 45,
      maxRetries: 2,
      temperatureOverride: 0.25,
      topPOverride: 0.7,
      maxTokensOverride: 900,
      structuredSchemaCode: 'agent_view_v1',
      defaultModelId: 21,
      defaultTemplateCode: 'trade.market.v1',
      defaultFallbackTemplateCode: 'trade.market.fallback',
      defaultOutputSchemaCode: 'agent_view_v1',
      toolAllowList: ['market_snapshot'],
      toolDenyList: [],
      runtimeFallback: 'RULE',
      toolPolicyJson: '',
      runtimeOptionsJson: '',
      remark: 'bounded hybrid agent'
    })
  })
})

describe('buildTradeAgentProfilePayload', () => {
  it('normalizes agent profile payload before submit', () => {
    expect(
      buildTradeAgentProfilePayload({
        id: 9,
        agentCode: ' Market_Agent ',
        agentName: ' Market Specialist ',
        agentType: ' hybrid ',
        enabled: 1,
        llmEnabled: 1,
        dialogueEnabled: 1,
        maxDialogueRounds: ' 1 ',
        speakOrder: ' 20 ',
        timeoutSeconds: ' 45 ',
        maxRetries: ' 2 ',
        temperatureOverride: ' 0.25 ',
        topPOverride: ' 0.7 ',
        maxTokensOverride: ' 900 ',
        structuredSchemaCode: ' agent_view_v1 ',
        defaultModelId: 21,
        defaultTemplateCode: ' trade.market.v1 ',
        defaultFallbackTemplateCode: ' trade.market.fallback ',
        defaultOutputSchemaCode: ' agent_view_v1 ',
        toolAllowList: ['market_snapshot'],
        toolDenyList: ['social_context'],
        runtimeFallback: 'RULE',
        toolPolicyJson: '{ "require": ["market_snapshot"] }',
        runtimeOptionsJson: '{ "timeoutMode": "soft" }',
        remark: ' bounded hybrid agent '
      })
    ).toEqual({
      id: 9,
      agentCode: 'market_agent',
      agentName: 'Market Specialist',
      agentType: 'HYBRID',
      enabled: true,
      llmEnabled: true,
      dialogueEnabled: true,
      maxDialogueRounds: 1,
      speakOrder: 20,
      timeoutSeconds: 45,
      maxRetries: 2,
      temperatureOverride: 0.25,
      topPOverride: 0.7,
      maxTokensOverride: 900,
      structuredSchemaCode: 'agent_view_v1',
      defaultModelId: 21,
      defaultTemplateCode: 'trade.market.v1',
      defaultFallbackTemplateCode: 'trade.market.fallback',
      defaultOutputSchemaCode: 'agent_view_v1',
      toolPolicyJson: '{"require":["market_snapshot"],"allow":["market_snapshot"],"deny":["social_context"]}',
      runtimeOptionsJson: '{"timeoutMode":"soft","fallback":"RULE"}',
      remark: 'bounded hybrid agent'
    })
  })
})

describe('validateTradeAgentProfilePayload', () => {
  it('rejects unsupported agent code and invalid json payloads', () => {
    expect(() =>
      validateTradeAgentProfilePayload({
        agentCode: 'planner_agent',
        agentName: 'Planner',
        agentType: 'LLM',
        structuredSchemaCode: 'agent_view_v1',
        toolPolicyJson: '{bad json}',
        runtimeOptionsJson: '{}'
      })
    ).toThrow(/代理编码|JSON/)
  })

  it('rejects dialogue rounds beyond bounded deliberation limit', () => {
    expect(() =>
      validateTradeAgentProfilePayload({
        agentCode: 'market_agent',
        agentName: 'Market Specialist',
        agentType: 'LLM',
        structuredSchemaCode: 'agent_view_v1',
        dialogueEnabled: true,
        maxDialogueRounds: 3,
        toolPolicyJson: '{}',
        runtimeOptionsJson: '{}'
      })
    ).toThrow(/对话轮数/)
  })

  it('requires default model and template when LLM is enabled', () => {
    expect(() =>
      validateTradeAgentProfilePayload({
        agentCode: 'market_agent',
        agentName: 'Market Specialist',
        agentType: 'LLM',
        llmEnabled: true,
        structuredSchemaCode: 'agent_view_v1',
        defaultOutputSchemaCode: 'agent_view_v1',
        toolPolicyJson: '{}',
        runtimeOptionsJson: '{}'
      })
    ).toThrow(/默认模型|defaultModelId|默认模板/)
  })
})
