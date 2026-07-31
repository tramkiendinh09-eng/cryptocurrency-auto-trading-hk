import { shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import {
  buildApiPayload,
  createApiForm,
  marketWsTemplateBinanceExampleJson,
  marketWsTemplateExampleJson,
  marketWsTemplateGuideItems,
  marketWsTemplateOkxExampleJson,
  validateApiPayload
} from '../index.vue'
import MarketDataIndex from '../index.vue'

vi.mock('@/api/dca/market', () => ({
  listApi: vi.fn(() => Promise.resolve({ rows: [] })),
  addApi: vi.fn(() => Promise.resolve({})),
  updateApi: vi.fn(() => Promise.resolve({})),
  deleteApi: vi.fn(() => Promise.resolve({})),
  testApi: vi.fn(() => Promise.resolve({ data: {} }))
}))

const elementStubs = {
  'el-alert': true,
  'el-button': true,
  'el-tabs': true,
  'el-tab-pane': true,
  'el-card': true,
  'el-select': true,
  'el-option': true,
  'el-table': true,
  'el-table-column': true,
  'el-dialog': true,
  'el-form': true,
  'el-form-item': true,
  'el-input': true,
  'el-radio-group': true,
  'el-radio': true,
  'el-switch': true,
  'el-input-number': true
}

describe('createApiForm', () => {
  it('hydrates websocket config fields for editing', () => {
    expect(
      createApiForm({
        id: 5,
        configName: 'Binance Futures Ticker',
        dataCategory: 'PRICE',
        apiName: 'BINANCE_FUTURES_TICKER_WS',
        transportType: 'websocket',
        vendorCode: 'binance',
        marketScope: 'futures',
        wsBaseUrl: 'wss://fstream.binance.com',
        wsPath: '/stream',
        wsStreamNameTemplate: '{symbol_lower}@ticker',
        wsCombinedEnabled: true,
        wsSymbolLowercase: true,
        wsPingIntervalSeconds: 20,
        wsPongTimeoutSeconds: 60,
        wsConnectionTtlHours: 24,
        wsMaxStreamsPerConnection: 1024,
        wsControlMessagesPerSecond: 5,
        docReferenceUrl: 'https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams',
        enabled: '1'
      })
    ).toEqual({
      id: 5,
      configName: 'Binance Futures Ticker',
      dataCategory: 'PRICE',
      dataSubType: '',
      apiName: 'BINANCE_FUTURES_TICKER_WS',
      apiUrl: '',
      transportType: 'WEBSOCKET',
      vendorCode: 'BINANCE',
      marketScope: 'FUTURES',
      wsBaseUrl: 'wss://fstream.binance.com',
      wsPath: '/stream',
      wsStreamNameTemplate: '{symbol_lower}@ticker',
      wsCombinedEnabled: true,
      wsSymbolLowercase: true,
      wsPingIntervalSeconds: 20,
      wsPongTimeoutSeconds: 60,
      wsConnectionTtlHours: 24,
      wsMaxStreamsPerConnection: 1024,
      wsControlMessagesPerSecond: 5,
      docReferenceUrl: 'https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams',
      httpMethod: 'GET',
      responsePath: '',
      fieldMapping: '',
      priority: 100,
      timeout: 10,
      enabled: '1',
      enabledValue: '1',
      remark: ''
    })
  })
})

describe('buildApiPayload', () => {
  it('normalizes binance websocket payload before submit', () => {
    expect(
      buildApiPayload({
        id: 5,
        configName: ' Binance Futures Ticker ',
        dataCategory: 'PRICE',
        dataSubType: ' ticker ',
        apiName: ' BINANCE_FUTURES_TICKER_WS ',
        apiUrl: ' ',
        transportType: ' websocket ',
        vendorCode: ' binance ',
        marketScope: ' futures ',
        wsBaseUrl: ' wss://fstream.binance.com ',
        wsPath: ' /stream ',
        wsStreamNameTemplate: ' {symbol_lower}@ticker ',
        wsCombinedEnabled: 1,
        wsSymbolLowercase: 1,
        wsPingIntervalSeconds: '20',
        wsPongTimeoutSeconds: '60',
        wsConnectionTtlHours: '24',
        wsMaxStreamsPerConnection: '1024',
        wsControlMessagesPerSecond: '5',
        docReferenceUrl: ' https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams ',
        httpMethod: ' get ',
        responsePath: ' $ ',
        fieldMapping: ' {"symbol":"s"} ',
        priority: '3',
        timeout: '15',
        enabledValue: '1',
        remark: ' ticker stream '
      })
    ).toEqual({
      id: 5,
      configName: 'Binance Futures Ticker',
      dataCategory: 'PRICE',
      dataSubType: 'TICKER',
      apiName: 'BINANCE_FUTURES_TICKER_WS',
      apiUrl: '',
      transportType: 'WEBSOCKET',
      vendorCode: 'BINANCE',
      marketScope: 'FUTURES',
      wsBaseUrl: 'wss://fstream.binance.com',
      wsPath: '/stream',
      wsStreamNameTemplate: '{symbol_lower}@ticker',
      wsCombinedEnabled: true,
      wsSymbolLowercase: true,
      wsPingIntervalSeconds: 20,
      wsPongTimeoutSeconds: 60,
      wsConnectionTtlHours: 24,
      wsMaxStreamsPerConnection: 1024,
      wsControlMessagesPerSecond: 5,
      docReferenceUrl: 'https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams',
      httpMethod: 'GET',
      responsePath: '$',
      fieldMapping: '{"symbol":"s"}',
      priority: 3,
      timeout: 15,
      enabled: '1',
      remark: 'ticker stream'
    })
  })
})

describe('validateApiPayload', () => {
  it('rejects combined stream on raw binance websocket path', () => {
    expect(
      validateApiPayload({
        configName: 'Binance Futures Ticker',
        dataCategory: 'PRICE',
        apiName: 'BINANCE_FUTURES_TICKER_WS',
        transportType: 'WEBSOCKET',
        vendorCode: 'BINANCE',
        wsBaseUrl: 'wss://fstream.binance.com',
        wsPath: '/ws',
        wsStreamNameTemplate: '{symbol_lower}@ticker',
        wsCombinedEnabled: true,
        wsSymbolLowercase: true
      })
    ).toBe('Binance combined streams must use /stream')
  })

  it('accepts valid binance websocket payload', () => {
    expect(
      validateApiPayload({
        configName: 'Binance Futures Ticker',
        dataCategory: 'PRICE',
        apiName: 'BINANCE_FUTURES_TICKER_WS',
        transportType: 'WEBSOCKET',
        vendorCode: 'BINANCE',
        wsBaseUrl: 'wss://fstream.binance.com',
        wsPath: '/stream',
        wsStreamNameTemplate: '{symbol_lower}@ticker',
        wsCombinedEnabled: true,
        wsSymbolLowercase: true
      })
    ).toBe('')
  })

  it('accepts okx public websocket subscribe args json', () => {
    expect(
      validateApiPayload({
        configName: 'OKX Swap Ticker WebSocket',
        dataCategory: 'PRICE',
        apiName: 'OKX_SWAP_TICKER_WS',
        transportType: 'WEBSOCKET',
        vendorCode: 'OKX',
        wsBaseUrl: 'wss://ws.okx.com:8443',
        wsPath: '/ws/v5/public',
        wsStreamNameTemplate: marketWsTemplateOkxExampleJson,
        wsCombinedEnabled: false,
        wsSymbolLowercase: false
      })
    ).toBe('')
  })
})

describe('market websocket guides', () => {
  it('documents stream template formats and examples for operators', () => {
    expect(marketWsTemplateGuideItems).toContain(
      'Binance 使用流名称模板，组合流必须走 /stream，例如 ticker、markPrice、forceOrder。'
    )
    expect(marketWsTemplateGuideItems).toContain(
      'OKX 使用 subscribe args JSON，公共频道走 /ws/v5/public，例如 tickers、mark-price、funding-rate、open-interest、liquidation-orders。'
    )
    expect(marketWsTemplateBinanceExampleJson).toContain('"{symbol_lower}@markPrice"')
    expect(marketWsTemplateOkxExampleJson).toContain('"channel": "mark-price"')
    expect(marketWsTemplateOkxExampleJson).toContain('"channel": "funding-rate"')
    expect(marketWsTemplateOkxExampleJson).toContain('"channel": "open-interest"')
    expect(marketWsTemplateOkxExampleJson).toContain('"channel": "liquidation-orders"')
    expect(marketWsTemplateExampleJson).toBe(marketWsTemplateOkxExampleJson)
  })

  it('exposes websocket guide constants on the component instance for template render', () => {
    const wrapper = shallowMount(MarketDataIndex, {
      global: {
        stubs: elementStubs,
        mocks: {
          $router: { push: vi.fn() }
        }
      }
    })

    expect(wrapper.vm.marketPageTitle).toContain('数据源')
    expect(wrapper.vm.marketWsTemplateGuideItems).toEqual(marketWsTemplateGuideItems)
    expect(wrapper.vm.marketWsTemplateExampleJson).toBe(marketWsTemplateExampleJson)
  })
})
