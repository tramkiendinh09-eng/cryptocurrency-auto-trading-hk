import { describe, expect, it } from 'vitest'

import { extractRiskHitRows } from '../index.vue'

describe('extractRiskHitRows', () => {
  it('prefers data arrays and falls back to rows arrays', () => {
    expect(extractRiskHitRows({ data: [{ ruleCode: 'daily_loss_limit' }] })).toEqual([{ ruleCode: 'daily_loss_limit' }])
    expect(extractRiskHitRows({ rows: [{ ruleCode: 'market_source_abnormal' }] })).toEqual([{ ruleCode: 'market_source_abnormal' }])
    expect(extractRiskHitRows({})).toEqual([])
  })
})
