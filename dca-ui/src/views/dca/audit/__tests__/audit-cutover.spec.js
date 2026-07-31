import { describe, expect, it } from 'vitest'

import { auditTabItems } from '../index.vue'

describe('audit tabs', () => {
  it('keeps only the AI call log tab', () => {
    expect(auditTabItems).toEqual([
      { label: 'AI调用日志', name: 'aicall' }
    ])
  })
})
