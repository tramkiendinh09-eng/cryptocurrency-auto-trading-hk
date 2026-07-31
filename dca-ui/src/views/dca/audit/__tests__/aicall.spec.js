import { describe, expect, it } from 'vitest'

import {
  buildAiCallModelOptions,
  formatAiCallModel,
  normalizeAiCallRows
} from '../aicall.vue'

describe('AI call audit helpers', () => {
  it('builds dynamic model options from loaded rows', () => {
    expect(
      buildAiCallModelOptions([
        { model: 'gpt5.4' },
        { model: 'gpt-4.1' },
        { model: 'gpt5.4' }
      ])
    ).toEqual([
      { label: 'gpt-4.1', value: 'gpt-4.1' },
      { label: 'gpt5.4', value: 'gpt5.4' }
    ])
  })

  it('prefers runtime model metadata when the legacy model field is empty', () => {
    expect(formatAiCallModel({ model: '', modelCode: 'gpt5.4', modelProvider: 'openai' })).toBe('gpt5.4 / openai')
  })

  it('normalizes runtime rows for display and filtering', () => {
    expect(
      normalizeAiCallRows([
        { scene: 'trade_runtime', model: '', modelCode: 'gpt5.4', modelProvider: 'openai' }
      ])
    ).toEqual([
      expect.objectContaining({
        scene: 'trade_runtime',
        displayModel: 'gpt5.4 / openai'
      })
    ])
  })
})
