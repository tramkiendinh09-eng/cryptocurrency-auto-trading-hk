import { describe, expect, it } from 'vitest'

import { createLegacyTriggerConsoleLinks, retiredMessage } from '../legacyTriggerRetirement'

describe('createLegacyTriggerConsoleLinks', () => {
  it('routes legacy trigger audit users to runtime consoles', () => {
    expect(createLegacyTriggerConsoleLinks()).toEqual([
      { label: '\u8fd0\u884c\u65f6\u603b\u89c8', path: '/dca/trade/runtime' },
      { label: '\u51b3\u7b56\u5ba1\u8ba1', path: '/dca/trade/decision' },
      { label: '\u5386\u53f2\u56de\u653e', path: '/dca/trade/replay' }
    ])
    expect(retiredMessage).toContain('DCA')
  })
})
