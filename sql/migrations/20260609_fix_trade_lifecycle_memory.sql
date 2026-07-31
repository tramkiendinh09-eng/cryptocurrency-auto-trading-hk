-- Fix trade lifecycle memory persistence linkage.
-- Apply to existing production databases before deploying the worker/backend changes.

ALTER TABLE position_snapshot
  ADD COLUMN entry_trace_id varchar(64) NULL DEFAULT NULL COMMENT 'original entry trace id' AFTER trace_id,
  ADD INDEX idx_position_snapshot_entry_trace_id (entry_trace_id);

UPDATE position_snapshot ps
JOIN (
  SELECT p.id,
         (
           SELECT op.trace_id
           FROM position_change_log op
           WHERE op.exchange_code = p.exchange_code
             AND op.symbol = p.symbol
             AND op.side = p.side
             AND op.change_type = 'OPEN'
             AND op.created_at <= p.created_at
           ORDER BY op.created_at DESC, op.id DESC
           LIMIT 1
         ) AS inferred_entry_trace_id
  FROM position_snapshot p
  WHERE p.position_quantity > 0
) inferred ON inferred.id = ps.id
SET ps.entry_trace_id = inferred.inferred_entry_trace_id
WHERE ps.entry_trace_id IS NULL
  AND inferred.inferred_entry_trace_id IS NOT NULL;

ALTER TABLE decision_run
  ADD COLUMN trade_memory_status_json json NULL COMMENT 'trade memory generation status' AFTER order_status,
  ADD COLUMN lifecycle_status_json json NULL COMMENT 'trade lifecycle persistence status' AFTER trade_memory_status_json;
