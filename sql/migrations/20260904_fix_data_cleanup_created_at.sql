-- 补回数据清理任务依赖、但 schema 重建时漏掉的 created_at 列。
--
-- 背景：本库的 schema 是从 MyBatis mapper + Java 实体反推重建的（作者未提交
-- sql/ai_trading.sql）。重建时只还原了 insert/resultMap 里出现过的列，而
-- TradeDataCleanupMapper 的 delete 语句里用到的 created_at 没有出现在任何
-- insert 中，于是这 6 张表全都少了这一列。
--
-- 后果：TradeDataCleanupTask 每天 10:30 (Asia/Shanghai) 跑，第 4 步
-- deleteMarketEventsBefore 抛 BadSqlGrammarException("Unknown column
-- 'created_at'")，整个任务中断——**后面 6 步从未执行过一次**，其中包含
-- event_raw(592MB) 和 market_metric_snapshot(298MB) 这两张最大的表。
-- 实测库以 1065MB/天 增长，剩余磁盘约 15 天写满，而保留期是 30 天，
-- 也就是说这套清理永远轮不到生效。
--
-- 用 DEFAULT CURRENT_TIMESTAMP，这样新插入自动带值，Java 侧无需改动。

ALTER TABLE market_event
  ADD COLUMN created_at datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  ADD INDEX idx_market_event_created_at (created_at);

ALTER TABLE market_kline_snapshot
  ADD COLUMN created_at datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  ADD INDEX idx_market_kline_snapshot_created_at (created_at);

ALTER TABLE market_metric_snapshot
  ADD COLUMN created_at datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  ADD INDEX idx_market_metric_snapshot_created_at (created_at);

ALTER TABLE news_event
  ADD COLUMN created_at datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  ADD INDEX idx_news_event_created_at (created_at);

ALTER TABLE onchain_event
  ADD COLUMN created_at datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  ADD INDEX idx_onchain_event_created_at (created_at);

ALTER TABLE social_event
  ADD COLUMN created_at datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  ADD INDEX idx_social_event_created_at (created_at);

-- 回填历史行。两张快照表有自己的时间列可用；四张事件表没有任何时间来源，
-- 从 event_raw 按 trace_id 取，取不到的保持 CURRENT_TIMESTAMP 默认值
-- （宁可多留一个保留周期，也不要把无法定年的行提前删掉）。
UPDATE market_metric_snapshot SET created_at = observed_at WHERE observed_at IS NOT NULL;
UPDATE market_kline_snapshot   SET created_at = open_time   WHERE open_time   IS NOT NULL;

UPDATE market_event t JOIN (SELECT trace_id, MIN(created_at) c FROM event_raw GROUP BY trace_id) e
  ON e.trace_id = t.trace_id SET t.created_at = e.c;
UPDATE news_event t JOIN (SELECT trace_id, MIN(created_at) c FROM event_raw GROUP BY trace_id) e
  ON e.trace_id = t.trace_id SET t.created_at = e.c;
UPDATE onchain_event t JOIN (SELECT trace_id, MIN(created_at) c FROM event_raw GROUP BY trace_id) e
  ON e.trace_id = t.trace_id SET t.created_at = e.c;
UPDATE social_event t JOIN (SELECT trace_id, MIN(created_at) c FROM event_raw GROUP BY trace_id) e
  ON e.trace_id = t.trace_id SET t.created_at = e.c;

-- 清理任务按 created_at 逐表 delete，但这两张最大的表上没有该列的索引，
-- 实测 signal_event 一次 delete 慢查 2218ms（90 万行全表扫），行数只会更多。
ALTER TABLE signal_event ADD INDEX idx_signal_event_created_at (created_at);
ALTER TABLE signal_score ADD INDEX idx_signal_score_created_at (created_at);
