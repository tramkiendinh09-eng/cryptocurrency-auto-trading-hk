import { describe, expect, it } from 'vitest'
import * as promptTemplateModule from '../index.vue'

import {
  buildPromptTemplatePayload,
  createPromptTemplateForm,
  validatePromptTemplatePayload
} from '../index.vue'

describe('createPromptTemplateForm', () => {
  it('hydrates template fields for editing', () => {
    expect(
      createPromptTemplateForm({
        id: 3,
        name: 'Supervisor Primary',
        code: 'trade.supervisor.v1',
        content: 'You are the trading supervisor for {symbol}',
        variables: '["symbol","exchange"]',
        version: 2,
        isActive: 1,
        isDefault: 0,
        remark: 'primary runtime template'
      })
    ).toMatchObject({
      id: 3,
      name: 'Supervisor Primary',
      code: 'trade.supervisor.v1',
      content: 'You are the trading supervisor for {symbol}',
      variablesList: ['symbol', 'exchange'],
      version: 2,
      isActive: 1,
      isDefault: 0,
      remark: 'primary runtime template'
    })
  })
})

describe('promptTemplateVariableOptions', () => {
  it('includes all supported supervisor render-context variables', () => {
    expect(promptTemplateModule.promptTemplateVariableOptions).toEqual(
      expect.arrayContaining([
        'market_source_status',
        'market_context_json',
        'recent_news_context_json',
        'recent_onchain_context_json',
        'short_term_memory_json',
        'long_term_memory_json',
        'memory_usage_json',
        'current_position_opened_at',
        'current_time',
        'current_position_holding_minutes'
      ])
    )
  })
})

describe('buildPromptTemplatePayload', () => {
  it('normalizes prompt template fields into api payload', () => {
    expect(
      buildPromptTemplatePayload({
        id: 3,
        name: ' Supervisor Primary ',
        code: ' trade.supervisor.v1 ',
        content: ' You are the trading supervisor for {symbol} ',
        variablesList: [' symbol ', 'exchange', 'symbol'],
        isActive: 1,
        isDefault: 0,
        remark: ' primary runtime template '
      })
    ).toEqual({
      id: 3,
      name: 'Supervisor Primary',
      code: 'trade.supervisor.v1',
      content: 'You are the trading supervisor for {symbol}',
      variables: '["symbol","exchange"]',
      isActive: 1,
      isDefault: 0,
      remark: 'primary runtime template'
    })
  })
})

describe('validatePromptTemplatePayload', () => {
  it('requires name, code, and content', () => {
    expect(() => validatePromptTemplatePayload({})).toThrow(/模板|编码|内容/)
  })
})
