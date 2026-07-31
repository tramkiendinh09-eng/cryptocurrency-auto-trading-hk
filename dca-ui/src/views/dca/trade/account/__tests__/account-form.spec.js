import { describe, expect, it } from 'vitest'

import {
  buildExchangeAccountPayload,
  createExchangeAccountForm,
  maskSecret,
  validateExchangeAccountPayload
} from '../index.vue'

describe('maskSecret', () => {
  it('keeps the head and tail visible for long secrets', () => {
    expect(maskSecret('abcd1234wxyz5678')).toBe('abcd***5678')
  })
})

describe('createExchangeAccountForm', () => {
  it('hydrates editable account form values', () => {
    expect(
      createExchangeAccountForm({
        id: 3,
        exchangeCode: 'binance',
        accountName: 'primary',
        accountKey: 'binance-main',
        accountRole: 'execution',
        apiKeyCiphertext: 'key-1',
        apiSecretCiphertext: 'secret-1',
        passphraseCiphertext: 'pass-1',
        apiBaseUrl: 'https://api.exchange.local',
        marginMode: 'isolated',
        leverageMode: 'auto',
        positionMode: 'hedge',
        settleCurrency: 'usdt',
        healthStatus: 'healthy',
        lastValidatedAt: '2026-04-16 12:00:00',
        lastErrorMessage: 'none',
        testnet: true,
        demoTrading: false,
        enabled: true
      })
    ).toEqual({
      id: 3,
      exchangeCode: 'BINANCE',
      accountName: 'primary',
      accountKey: 'binance-main',
      accountRole: 'EXECUTION',
      apiKeyCiphertext: 'key-1',
      apiSecretCiphertext: 'secret-1',
      passphraseCiphertext: 'pass-1',
      apiBaseUrl: 'https://api.exchange.local',
      marginMode: 'isolated',
      leverageMode: 'auto',
      positionMode: 'hedge',
      settleCurrency: 'USDT',
      healthStatus: 'healthy',
      lastValidatedAt: '2026-04-16 12:00:00',
      lastErrorMessage: 'none',
      testnet: true,
      demoTrading: false,
      enabled: true
    })
  })
})

describe('buildExchangeAccountPayload', () => {
  it('normalizes exchange code and enabled flag before submit', () => {
    expect(
      buildExchangeAccountPayload({
        id: 3,
        exchangeCode: ' okx ',
        accountName: 'primary',
        accountKey: ' main ',
        accountRole: ' execution ',
        apiKeyCiphertext: 'key-1',
        apiSecretCiphertext: 'secret-1',
        passphraseCiphertext: ' pass-1 ',
        apiBaseUrl: ' https://okx.local ',
        marginMode: ' ISOLATED ',
        leverageMode: ' AUTO ',
        positionMode: ' HEDGE ',
        settleCurrency: ' usdt ',
        healthStatus: ' HEALTHY ',
        lastValidatedAt: ' 2026-04-16T12:00:00Z ',
        lastErrorMessage: ' recovered ',
        testnet: 0,
        demoTrading: 1,
        enabled: 1
      })
    ).toEqual({
      id: 3,
      exchangeCode: 'OKX',
      accountName: 'primary',
      accountKey: 'main',
      accountRole: 'EXECUTION',
      apiKeyCiphertext: 'key-1',
      apiSecretCiphertext: 'secret-1',
      passphraseCiphertext: 'pass-1',
      apiBaseUrl: 'https://okx.local',
      marginMode: 'isolated',
      leverageMode: 'auto',
      positionMode: 'hedge',
      settleCurrency: 'USDT',
      healthStatus: 'healthy',
      lastValidatedAt: '2026-04-16T12:00:00Z',
      lastErrorMessage: 'recovered',
      testnet: false,
      demoTrading: true,
      enabled: true
    })
  })
})

describe('validateExchangeAccountPayload', () => {
  it('requires passphrase for okx accounts', () => {
    expect(
      validateExchangeAccountPayload({
        exchangeCode: 'OKX',
        accountName: 'primary',
        apiKeyCiphertext: 'key-1',
        apiSecretCiphertext: 'secret-1',
        passphraseCiphertext: ''
      })
    ).toBe('OKX 账户必须填写 Passphrase')
  })

  it('accepts a complete runtime account payload', () => {
    expect(
      validateExchangeAccountPayload({
        exchangeCode: 'BINANCE',
        accountName: 'primary',
        apiKeyCiphertext: 'key-1',
        apiSecretCiphertext: 'secret-1',
        passphraseCiphertext: ''
      })
    ).toBe('')
  })
})
