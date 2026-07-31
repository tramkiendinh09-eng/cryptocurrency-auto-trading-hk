/**
 * 交易系统常量服务
 *
 * 从后端获取常量配置，避免前端硬编码
 * 提供缓存机制，减少重复请求
 */

import { getTradeConstants, getExchanges, getSymbols, getModes } from '@/api/dca/tradeConstants'

// 缓存的常量数据
let constantsCache = null
let cacheExpiry = 0
const CACHE_TTL = 5 * 60 * 1000 // 5分钟缓存

// 默认值（作为后备，当API不可用时使用）
const DEFAULT_CONSTANTS = {
  exchanges: {
    allowed: ['BINANCE', 'OKX'],
    binance: 'BINANCE',
    okx: 'OKX'
  },
  symbols: {
    allowed: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
  },
  modes: {
    allowed: ['paper', 'shadow', 'live'],
    paper: 'paper',
    shadow: 'shadow',
    live: 'live'
  },
  actions: {
    open: 'OPEN',
    close: 'CLOSE',
    reduce: 'REDUCE',
    hold: 'HOLD'
  },
  positionSides: {
    long: 'long',
    short: 'short',
    net: 'net'
  },
  marginModes: {
    cross: 'cross',
    isolated: 'isolated'
  },
  positionModes: {
    longShort: 'long_short_mode',
    net: 'net_mode'
  },
  orderTypes: {
    market: 'market',
    limit: 'limit'
  },
  orderStatuses: {
    new: 'NEW',
    filled: 'FILLED',
    partiallyFilled: 'PARTIALLY_FILLED',
    canceled: 'CANCELED',
    rejected: 'REJECTED',
    expired: 'EXPIRED'
  }
}

/**
 * 检查缓存是否有效
 */
function isCacheValid() {
  return constantsCache !== null && Date.now() < cacheExpiry
}

/**
 * 获取所有常量配置
 *
 * @param {boolean} forceRefresh - 是否强制刷新缓存
 * @returns {Promise<Object>} 常量配置对象
 */
export async function fetchAllConstants(forceRefresh = false) {
  if (!forceRefresh && isCacheValid()) {
    return constantsCache
  }

  try {
    const response = await getTradeConstants()
    if (response.code === 200 && response.data) {
      constantsCache = response.data
      cacheExpiry = Date.now() + CACHE_TTL
      return constantsCache
    }
  } catch (error) {
    console.warn('Failed to fetch trade constants, using defaults:', error)
  }

  // 返回默认值
  return DEFAULT_CONSTANTS
}

/**
 * 获取支持的交易所列表
 *
 * @returns {Promise<string[]>} 交易所列表
 */
export async function fetchExchanges() {
  const constants = await fetchAllConstants()
  return constants.exchanges?.allowed || DEFAULT_CONSTANTS.exchanges.allowed
}

/**
 * 获取支持的交易对列表
 *
 * @returns {Promise<string[]>} 交易对列表
 */
export async function fetchSymbols() {
  const constants = await fetchAllConstants()
  return constants.symbols?.allowed || DEFAULT_CONSTANTS.symbols.allowed
}

/**
 * 获取支持的运行模式列表
 *
 * @returns {Promise<string[]>} 运行模式列表
 */
export async function fetchModes() {
  const constants = await fetchAllConstants()
  return constants.modes?.allowed || DEFAULT_CONSTANTS.modes.allowed
}

/**
 * 获取特定常量值
 *
 * @param {string} category - 常量类别 (如 'exchanges', 'modes')
 * @param {string} key - 常量键名 (如 'binance', 'paper')
 * @returns {Promise<string>} 常量值
 */
export async function fetchConstant(category, key) {
  const constants = await fetchAllConstants()
  return constants[category]?.[key] || DEFAULT_CONSTANTS[category]?.[key]
}

/**
 * 清除缓存
 */
export function clearConstantsCache() {
  constantsCache = null
  cacheExpiry = 0
}

/**
 * 获取交易所代码（同步方法，使用缓存或默认值）
 *
 * @returns {Object} 交易所代码映射
 */
export function getExchangeCodes() {
  if (constantsCache) {
    return {
      BINANCE: constantsCache.exchanges?.binance || 'BINANCE',
      OKX: constantsCache.exchanges?.okx || 'OKX'
    }
  }
  return {
    BINANCE: DEFAULT_CONSTANTS.exchanges.binance,
    OKX: DEFAULT_CONSTANTS.exchanges.okx
  }
}

/**
 * 获取运行模式代码（同步方法，使用缓存或默认值）
 *
 * @returns {Object} 运行模式代码映射
 */
export function getModeCodes() {
  if (constantsCache) {
    return {
      PAPER: constantsCache.modes?.paper || 'paper',
      SHADOW: constantsCache.modes?.shadow || 'shadow',
      LIVE: constantsCache.modes?.live || 'live'
    }
  }
  return {
    PAPER: DEFAULT_CONSTANTS.modes.paper,
    SHADOW: DEFAULT_CONSTANTS.modes.shadow,
    LIVE: DEFAULT_CONSTANTS.modes.live
  }
}

// 导出默认常量（用于测试或紧急情况）
export { DEFAULT_CONSTANTS }