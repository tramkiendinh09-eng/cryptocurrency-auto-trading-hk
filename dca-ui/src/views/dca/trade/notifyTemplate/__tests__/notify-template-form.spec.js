import { describe, expect, it } from 'vitest'

import {
  buildNotifyTemplatePayload,
  createNotifyTemplateForm,
  validateNotifyTemplatePayload
} from '../index.vue'

describe('createNotifyTemplateForm', () => {
  it('hydrates variables into structured tag input', () => {
    expect(
      createNotifyTemplateForm({
        id: 7,
        name: '风险通知',
        code: 'notify.runtime.risk.v1',
        titleTemplate: '[{{symbol}}] 风险提醒',
        contentTemplate: '事件：{event_type}',
        variables: '["symbol","event_type","severity"]',
        isActive: 1,
        isDefault: 0
      })
    ).toEqual({
      id: 7,
      name: '风险通知',
      code: 'notify.runtime.risk.v1',
      titleTemplate: '[{{symbol}}] 风险提醒',
      contentTemplate: '事件：{event_type}',
      variablesList: ['symbol', 'event_type', 'severity'],
      isActive: 1,
      isDefault: 0,
      remark: ''
    })
  })
})

describe('buildNotifyTemplatePayload', () => {
  it('serializes structured variables list back to json array', () => {
    expect(
      buildNotifyTemplatePayload({
        id: 7,
        name: '风险通知',
        code: 'notify.runtime.risk.v1',
        titleTemplate: '[{{symbol}}] 风险提醒',
        contentTemplate: '事件：{event_type}',
        variablesList: ['symbol', 'event_type', 'severity'],
        isActive: 1,
        isDefault: 0,
        remark: '模板说明'
      })
    ).toEqual({
      id: 7,
      name: '风险通知',
      code: 'notify.runtime.risk.v1',
      titleTemplate: '[{{symbol}}] 风险提醒',
      contentTemplate: '事件：{event_type}',
      variables: '["symbol","event_type","severity"]',
      isActive: 1,
      isDefault: 0,
      remark: '模板说明'
    })
  })
})

describe('validateNotifyTemplatePayload', () => {
  it('rejects empty required fields with Chinese messages', () => {
    expect(() =>
      validateNotifyTemplatePayload({
        name: '',
        code: '',
        titleTemplate: '',
        contentTemplate: ''
      })
    ).toThrow(/模板名称不能为空/)
  })
})
