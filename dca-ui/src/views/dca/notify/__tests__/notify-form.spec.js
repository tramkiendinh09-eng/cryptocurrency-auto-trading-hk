import { describe, expect, it } from 'vitest'

import {
  buildChannelPayload,
  createChannelForm,
  createRecordQuery,
  createSupportedChannelTypes,
  validateChannelPayload
} from '../index.vue'

describe('createSupportedChannelTypes', () => {
  it('exposes specs-aligned persisted notify channels including webhook', () => {
    expect(createSupportedChannelTypes().map((item) => item.value)).toEqual([
      'email',
      'telegram',
      'dingtalk',
      'feishu',
      'webhook'
    ])
  })
})

describe('createChannelForm', () => {
  it('hydrates telegram channel fields for UI editing', () => {
    expect(
      createChannelForm({
        id: 3,
        channelType: 'telegram',
        channelName: 'Ops Bot',
        token: 'bot-token',
        recipient: 'chat-1',
        isEnabled: 1
      })
    ).toMatchObject({
      id: 3,
      channelType: 'telegram',
      channelName: 'Ops Bot',
      botToken: 'bot-token',
      chatId: 'chat-1',
      isEnabled: 1
    })
  })
})

describe('buildChannelPayload', () => {
  it('normalizes email channel form into notify_channel payload', () => {
    expect(
      buildChannelPayload({
        channelType: 'email',
        channelName: '  Runtime Ops  ',
        smtpHost: ' smtp.qq.com ',
        smtpPort: 587,
        mailUsername: 'ops@example.com',
        mailPassword: 'secret',
        mailFrom: 'Ops',
        emailAddress: 'ops@example.com',
        webhookUrl: 'https://should-clear.invalid',
        token: 'should-clear',
        recipient: 'should-clear',
        isEnabled: true,
        remark: ' runtime '
      })
    ).toEqual({
      id: undefined,
      channelType: 'email',
      channelName: 'Runtime Ops',
      webhookUrl: '',
      token: '',
      recipient: 'ops@example.com',
      smtpHost: 'smtp.qq.com',
      smtpPort: 587,
      mailUsername: 'ops@example.com',
      mailPassword: 'secret',
      mailFrom: 'Ops',
      isEnabled: 1,
      remark: 'runtime'
    })
  })
})

describe('validateChannelPayload', () => {
  it('rejects non-https webhook channels before submit', () => {
    expect(() =>
      validateChannelPayload({
        channelType: 'webhook',
        channelName: 'Audit Webhook',
        webhookUrl: 'http://callback.internal'
      })
    ).toThrow(/https/i)
  })
})

describe('createRecordQuery', () => {
  it('preserves trace-based audit filters for notify_record queries', () => {
    expect(
      createRecordQuery({
        pageNum: 1,
        pageSize: 20,
        channelType: 'telegram',
        status: 3,
        title: 'risk',
        traceId: 'trace-ops-1',
        recipient: '@ops'
      })
    ).toEqual({
      pageNum: 1,
      pageSize: 20,
      channelType: 'telegram',
      status: 3,
      title: 'risk',
      traceId: 'trace-ops-1',
      recipient: '@ops'
    })
  })
})
