package com.ruoyi.dca.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;

/**
 * 行情终端的 K 线数据源。
 *
 * <p>控制台此前一张行情图都没有：{@code dashboard/charts.vue} 名字叫 charts，
 * 内容是五个跳转按钮。K 线数据在 worker 侧一直有，但只以 {@code market_kline}
 * 事件形式落在 event_raw 里——每轮抓取 500 根全量重发，两小时一万两千行，
 * 拿它画图要先去重再排序，很不划算。
 *
 * <p>所以这里直接代理交易所的公开 K 线接口：一次请求拿到完整的一段历史，
 * 不依赖数据库。浏览器不直连交易所有两个原因：用户所在网络未必能通，
 * 以及浏览器直连会把交易所的限流配额按客户端 IP 分散掉、难以观测。
 */
@RestController
@RequestMapping("/dca/market")
public class TerminalMarketController extends BaseController {

    private static final Logger log = LoggerFactory.getLogger(TerminalMarketController.class);

    /** 只允许形如 BTCUSDT 的合约代码：这条路径会把参数拼进外部 URL。 */
    private static final Pattern SYMBOL = Pattern.compile("^[A-Z0-9]{2,20}$");

    /** 交易所支持的周期白名单，避免把任意字符串透传出去。 */
    private static final Set<String> INTERVALS = Set.of(
        "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w");

    private static final int MAX_LIMIT = 1000;

    /** 缓存 TTL。终端每 15 秒轮询一次，10 秒的窗口足以挡掉多开标签页的重复请求。 */
    private static final long CACHE_TTL_MS = 10_000L;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Map<String, CacheEntry> cache = new ConcurrentHashMap<>();

    @Autowired
    private RestTemplate restTemplate;

    @Value("${dca.terminal.klineBaseUrl:https://fapi.binance.com/fapi/v1/klines}")
    private String klineBaseUrl;

    @Value("${dca.terminal.tickerUrl:https://fapi.binance.com/fapi/v1/ticker/24hr}")
    private String tickerUrl;

    private static final String TICKER_CACHE_KEY = "__tickers__";

    @PreAuthorize("@ss.hasPermi('dca:market:query')")
    @GetMapping("/klines")
    public AjaxResult klines(
        @RequestParam String symbol,
        @RequestParam(defaultValue = "15m") String interval,
        @RequestParam(defaultValue = "300") int limit) {

        String normalizedSymbol = symbol == null ? "" : symbol.trim().toUpperCase();
        if (!SYMBOL.matcher(normalizedSymbol).matches()) {
            return AjaxResult.error("illegal symbol");
        }
        if (!INTERVALS.contains(interval)) {
            return AjaxResult.error("illegal interval");
        }
        int boundedLimit = Math.max(1, Math.min(limit, MAX_LIMIT));

        String cacheKey = normalizedSymbol + ":" + interval + ":" + boundedLimit;
        CacheEntry cached = cache.get(cacheKey);
        long now = System.currentTimeMillis();
        if (cached != null && now - cached.fetchedAt < CACHE_TTL_MS) {
            return AjaxResult.success(cached.rows);
        }

        try {
            String url = klineBaseUrl + "?symbol=" + normalizedSymbol
                + "&interval=" + interval + "&limit=" + boundedLimit;
            String body = restTemplate.getForObject(url, String.class);
            List<List<Object>> raw = objectMapper.readValue(body, new TypeReference<List<List<Object>>>() {});
            List<Map<String, Object>> rows = new ArrayList<>(raw.size());
            for (List<Object> k : raw) {
                // 交易所返回的是定长数组：[开盘时间, 开, 高, 低, 收, 成交量, 收盘时间, 成交额, ...]
                if (k == null || k.size() < 6) {
                    continue;
                }
                Map<String, Object> row = new LinkedHashMap<>(6);
                // Lightweight Charts 的时间单位是秒，不是毫秒。
                row.put("t", Long.parseLong(String.valueOf(k.get(0))) / 1000L);
                row.put("o", Double.parseDouble(String.valueOf(k.get(1))));
                row.put("h", Double.parseDouble(String.valueOf(k.get(2))));
                row.put("l", Double.parseDouble(String.valueOf(k.get(3))));
                row.put("c", Double.parseDouble(String.valueOf(k.get(4))));
                row.put("v", Double.parseDouble(String.valueOf(k.get(5))));
                rows.add(row);
            }
            cache.put(cacheKey, new CacheEntry(now, rows));
            return AjaxResult.success(rows);
        } catch (Exception e) {
            log.warn("kline fetch failed symbol={} interval={}: {}", normalizedSymbol, interval, e.getMessage());
            // 拿不到就退回上一次的缓存，宁可给一张旧图也好过整块空白。
            if (cached != null) {
                AjaxResult stale = AjaxResult.success(cached.rows);
                stale.put("stale", true);
                return stale;
            }
            return AjaxResult.error("kline fetch failed: " + e.getMessage());
        }
    }

    /**
     * 自选列表的批量报价。
     *
     * <p>一次请求拿回交易所的全量 24h ticker 再按 symbols 过滤，而不是每个标的
     * 发一次——自选有十几个标的，逐个请求会把首屏拖成十几个串行往返。
     */
    @PreAuthorize("@ss.hasPermi('dca:market:query')")
    @GetMapping("/tickers")
    public AjaxResult tickers(@RequestParam String symbols) {
        Set<String> wanted = new LinkedHashSet<>();
        for (String item : symbols == null ? new String[0] : symbols.split(",")) {
            String normalized = item.trim().toUpperCase();
            if (SYMBOL.matcher(normalized).matches()) {
                wanted.add(normalized);
            }
        }
        if (wanted.isEmpty()) {
            return AjaxResult.success(new ArrayList<Map<String, Object>>());
        }

        CacheEntry cached = cache.get(TICKER_CACHE_KEY);
        long now = System.currentTimeMillis();
        List<Map<String, Object>> all;
        if (cached != null && now - cached.fetchedAt < CACHE_TTL_MS) {
            all = cached.rows;
        } else {
            try {
                String body = restTemplate.getForObject(tickerUrl, String.class);
                all = objectMapper.readValue(body, new TypeReference<List<Map<String, Object>>>() {});
                cache.put(TICKER_CACHE_KEY, new CacheEntry(now, all));
            } catch (Exception e) {
                log.warn("ticker fetch failed: {}", e.getMessage());
                if (cached == null) {
                    return AjaxResult.error("ticker fetch failed: " + e.getMessage());
                }
                all = cached.rows;
            }
        }

        List<Map<String, Object>> rows = new ArrayList<>(wanted.size());
        for (Map<String, Object> item : all) {
            String code = String.valueOf(item.get("symbol"));
            if (!wanted.contains(code)) {
                continue;
            }
            Map<String, Object> row = new LinkedHashMap<>(3);
            row.put("symbol", code);
            row.put("price", item.get("lastPrice"));
            row.put("changePct", item.get("priceChangePercent"));
            rows.add(row);
        }
        return AjaxResult.success(rows);
    }

    private static final class CacheEntry {
        private final long fetchedAt;
        private final List<Map<String, Object>> rows;

        private CacheEntry(long fetchedAt, List<Map<String, Object>> rows) {
            this.fetchedAt = fetchedAt;
            this.rows = rows;
        }
    }
}
