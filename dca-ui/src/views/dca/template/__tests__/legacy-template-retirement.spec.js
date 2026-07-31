import { describe, expect, it } from 'vitest'

import {
  createLegacyTemplateConsoleLinks,
  createLegacyTemplateGuidance,
  retiredMessage
} from '../legacyTemplateRetirement'

describe('legacy template retirement helpers', () => {
  it('exposes runtime strategy links and retirement guidance', () => {
    expect(createLegacyTemplateConsoleLinks()).toEqual([
      { label: '\u4ea4\u6613\u7b56\u7565', path: '/dca/trade/strategy' },
      { label: '\u8fd0\u884c\u6a21\u5f0f', path: '/dca/trade/runtime' },
      { label: '\u8d26\u6237\u7ed1\u5b9a', path: '/dca/trade/account' }
    ])
    expect(createLegacyTemplateGuidance()).toHaveLength(3)
    expect(retiredMessage).toContain('旧策略模板')
  })
})
