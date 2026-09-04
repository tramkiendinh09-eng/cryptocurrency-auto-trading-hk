-- Trade runtime schema
-- Reconstructed from MyBatis mappers + Java entities: the upstream repository
-- ships no schema dump (sql/ai_trading.sql is gitignored, and the bootstrap
-- scripts referenced by deploy/prod/README.md were never committed).
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `agent_conclusion`;
CREATE TABLE `agent_conclusion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_name` varchar(255) NULL DEFAULT NULL,
  `bias` varchar(255) NULL DEFAULT NULL,
  `confidence` int NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `reason` text NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `agent_memory`;
CREATE TABLE `agent_memory` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(255) NULL DEFAULT NULL,
  `agent_code` varchar(255) NULL DEFAULT NULL,
  `confidence` decimal(36,18) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `direction` varchar(255) NULL DEFAULT NULL,
  `enabled` tinyint(1) NULL DEFAULT NULL,
  `event_tags_json` longtext NULL,
  `evidence_json` longtext NULL,
  `last_used_at` datetime NULL DEFAULT NULL,
  `lesson_text` text NULL,
  `loss_count` int NULL DEFAULT NULL,
  `market_regime` varchar(255) NULL DEFAULT NULL,
  `memory_key` varchar(255) NULL DEFAULT NULL,
  `memory_type` varchar(255) NULL DEFAULT NULL,
  `outcome_json` longtext NULL,
  `quality_score` decimal(36,18) NULL DEFAULT NULL,
  `source_trace_id` varchar(64) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `updated_at` datetime NULL DEFAULT NULL,
  `usage_count` int NULL DEFAULT NULL,
  `win_count` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_agent_memory_enabled`(`enabled`) USING BTREE,
  INDEX `idx_agent_memory_agent_code`(`agent_code`) USING BTREE,
  INDEX `idx_agent_memory_symbol`(`symbol`) USING BTREE,
  INDEX `idx_agent_memory_quality_score`(`quality_score`) USING BTREE,
  INDEX `idx_agent_memory_updated_at`(`updated_at`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `agent_memory_usage`;
CREATE TABLE `agent_memory_usage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_code` varchar(255) NULL DEFAULT NULL,
  `memory_id` bigint NULL DEFAULT NULL,
  `outcome_json` longtext NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `usage_context_json` longtext NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `agent_message`;
CREATE TABLE `agent_message` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_run_id` bigint NULL DEFAULT NULL,
  `content_json` longtext NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `message_type` varchar(255) NULL DEFAULT NULL,
  `model_code` varchar(255) NULL DEFAULT NULL,
  `round_no` int NULL DEFAULT NULL,
  `speaker_agent` varchar(255) NULL DEFAULT NULL,
  `summary_text` text NULL,
  `target_agent` varchar(255) NULL DEFAULT NULL,
  `template_code` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_agent_message_trace_id`(`trace_id`) USING BTREE,
  INDEX `idx_agent_message_round_no`(`round_no`) USING BTREE,
  INDEX `idx_agent_message_speaker_agent`(`speaker_agent`) USING BTREE,
  INDEX `idx_agent_message_message_type`(`message_type`) USING BTREE,
  INDEX `idx_agent_message_created_at`(`created_at`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `agent_observation`;
CREATE TABLE `agent_observation` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_name` varchar(255) NULL DEFAULT NULL,
  `agent_run_id` bigint NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `observation_json` longtext NULL,
  `observation_type` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `agent_run`;
CREATE TABLE `agent_run` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_name` varchar(255) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `event_strength` varchar(255) NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `ai_model_config`;
CREATE TABLE `ai_model_config` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `api_endpoint` varchar(500) NULL DEFAULT NULL,
  `api_key_encrypted` varchar(255) NULL DEFAULT NULL,
  `api_version` varchar(255) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `daily_limit` int NULL DEFAULT NULL,
  `description` text NULL,
  `is_default` int NULL DEFAULT NULL,
  `is_enabled` int NULL DEFAULT NULL,
  `max_temperature` decimal(36,18) NULL DEFAULT NULL,
  `max_tokens` int NULL DEFAULT NULL,
  `model_code` varchar(255) NULL DEFAULT NULL,
  `model_key` varchar(255) NULL DEFAULT NULL,
  `model_name` varchar(255) NULL DEFAULT NULL,
  `model_version` varchar(255) NULL DEFAULT NULL,
  `monthly_token_limit` bigint NULL DEFAULT NULL,
  `priority` int NULL DEFAULT NULL,
  `provider` varchar(255) NULL DEFAULT NULL,
  `retry_times` int NULL DEFAULT NULL,
  `temperature` decimal(36,18) NULL DEFAULT NULL,
  `timeout_seconds` int NULL DEFAULT NULL,
  `top_p` decimal(36,18) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `usage_count` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_ai_model_config_is_default`(`is_default`) USING BTREE,
  INDEX `idx_ai_model_config_priority`(`priority`) USING BTREE,
  INDEX `idx_ai_model_config_is_enabled`(`is_enabled`) USING BTREE,
  INDEX `idx_ai_model_config_model_code`(`model_code`) USING BTREE,
  INDEX `idx_ai_model_config_provider`(`provider`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `audit_ai_call_log`;
CREATE TABLE `audit_ai_call_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `call_time` datetime NULL DEFAULT NULL,
  `completion_tokens` int NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `error_msg` varchar(255) NULL DEFAULT NULL,
  `model` varchar(255) NULL DEFAULT NULL,
  `prompt` text NULL,
  `prompt_tokens` int NULL DEFAULT NULL,
  `remark` text NULL,
  `response` text NULL,
  `response_time` bigint NULL DEFAULT NULL,
  `scene` varchar(255) NULL DEFAULT NULL,
  `status` int NULL DEFAULT NULL,
  `template_id` bigint NULL DEFAULT NULL,
  `total_tokens` int NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `user_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_audit_ai_call_log_model`(`model`) USING BTREE,
  INDEX `idx_audit_ai_call_log_status`(`status`) USING BTREE,
  INDEX `idx_audit_ai_call_log_call_time`(`call_time`) USING BTREE,
  INDEX `idx_audit_ai_call_log_user_id`(`user_id`) USING BTREE,
  INDEX `idx_audit_ai_call_log_scene`(`scene`) USING BTREE,
  INDEX `idx_audit_ai_call_log_total_tokens`(`total_tokens`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `audit_operation_log`;
CREATE TABLE `audit_operation_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `description` text NULL,
  `error_msg` varchar(255) NULL DEFAULT NULL,
  `execution_time` bigint NULL DEFAULT NULL,
  `module` varchar(255) NULL DEFAULT NULL,
  `operation` varchar(255) NULL DEFAULT NULL,
  `operation_time` datetime NULL DEFAULT NULL,
  `remark` text NULL,
  `request_ip` varchar(255) NULL DEFAULT NULL,
  `request_method` varchar(255) NULL DEFAULT NULL,
  `request_params` text NULL,
  `request_url` varchar(500) NULL DEFAULT NULL,
  `response_data` varchar(255) NULL DEFAULT NULL,
  `status` int NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `user_id` bigint NULL DEFAULT NULL,
  `username` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_audit_operation_log_operation_time`(`operation_time`) USING BTREE,
  INDEX `idx_audit_operation_log_user_id`(`user_id`) USING BTREE,
  INDEX `idx_audit_operation_log_module`(`module`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `audit_strategy_trigger`;
CREATE TABLE `audit_strategy_trigger` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `after_price` decimal(36,18) NULL DEFAULT NULL,
  `before_price` decimal(36,18) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `phase` int NULL DEFAULT NULL,
  `price_change` decimal(36,18) NULL DEFAULT NULL,
  `remark` text NULL,
  `result` text NULL,
  `result_desc` varchar(255) NULL DEFAULT NULL,
  `strategy_id` bigint NULL DEFAULT NULL,
  `strategy_snapshot` text NULL,
  `threshold` decimal(36,18) NULL DEFAULT NULL,
  `trigger_time` datetime NULL DEFAULT NULL,
  `trigger_type` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `user_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_audit_strategy_trigger_trigger_time`(`trigger_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `card_key`;
CREATE TABLE `card_key` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `active_time` datetime NULL DEFAULT NULL,
  `batch_no` int NULL DEFAULT NULL,
  `bind_machine` varchar(255) NULL DEFAULT NULL,
  `bind_user_id` bigint NULL DEFAULT NULL,
  `card_key` varchar(255) NULL DEFAULT NULL,
  `card_level` varchar(255) NULL DEFAULT NULL,
  `card_type` varchar(255) NULL DEFAULT NULL,
  `counts` int NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `days` int NULL DEFAULT NULL,
  `expire_time` datetime NULL DEFAULT NULL,
  `feature_flags` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_card_key_status`(`status`) USING BTREE,
  INDEX `idx_card_key_expire_time`(`expire_time`) USING BTREE,
  INDEX `idx_card_key_create_time`(`create_time`) USING BTREE,
  INDEX `idx_card_key_batch_no`(`batch_no`) USING BTREE,
  INDEX `idx_card_key_bind_user_id`(`bind_user_id`) USING BTREE,
  INDEX `idx_card_key_card_key`(`card_key`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `decision_action`;
CREATE TABLE `decision_action` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(255) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `decision_run_id` bigint NULL DEFAULT NULL,
  `execution_status` varchar(255) NULL DEFAULT NULL,
  `order_ref` varchar(255) NULL DEFAULT NULL,
  `order_status` varchar(255) NULL DEFAULT NULL,
  `side` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `decision_run`;
CREATE TABLE `decision_run` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(255) NULL DEFAULT NULL,
  `active_signal_refs_json` longtext NULL,
  `binding_template_code` varchar(255) NULL DEFAULT NULL,
  `budget_blocked` tinyint(1) NULL DEFAULT NULL,
  `combination_match_json` longtext NULL,
  `confidence` int NULL DEFAULT NULL,
  `cooldown_blocked` tinyint(1) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `dispatch_mode` varchar(255) NULL DEFAULT NULL,
  `execution_status` varchar(255) NULL DEFAULT NULL,
  `fallback_template_code` varchar(255) NULL DEFAULT NULL,
  `lifecycle_status_json` longtext NULL,
  `mode` varchar(255) NULL DEFAULT NULL,
  `model_code` varchar(255) NULL DEFAULT NULL,
  `model_provider` varchar(255) NULL DEFAULT NULL,
  `order_status` varchar(255) NULL DEFAULT NULL,
  `prompt_source` varchar(255) NULL DEFAULT NULL,
  `prompt_template_fallback_used` tinyint(1) NULL DEFAULT NULL,
  `resolved_template_code` varchar(255) NULL DEFAULT NULL,
  `selected_agents_json` longtext NULL,
  `summary_reason` text NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `trade_memory_status_json` longtext NULL,
  `trigger_reason` text NULL,
  `trigger_source` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_decision_run_trace_id`(`trace_id`) USING BTREE,
  INDEX `idx_decision_run_created_at`(`created_at`) USING BTREE,
  INDEX `idx_decision_run_cooldown_blocked`(`cooldown_blocked`) USING BTREE,
  INDEX `idx_decision_run_budget_blocked`(`budget_blocked`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `event_raw`;
CREATE TABLE `event_raw` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime NULL DEFAULT NULL,
  `event_type` varchar(255) NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `payload_json` longtext NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_event_raw_event_type`(`event_type`) USING BTREE,
  INDEX `idx_event_raw_symbol`(`symbol`) USING BTREE,
  INDEX `idx_event_raw_exchange_code`(`exchange_code`) USING BTREE,
  INDEX `idx_event_raw_created_at`(`created_at`) USING BTREE,
  INDEX `idx_event_raw_trace_id`(`trace_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `exchange_account`;
CREATE TABLE `exchange_account` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `account_key` varchar(255) NULL DEFAULT NULL,
  `account_name` varchar(255) NULL DEFAULT NULL,
  `account_role` varchar(255) NULL DEFAULT NULL,
  `api_base_url` varchar(500) NULL DEFAULT NULL,
  `api_key_ciphertext` varchar(255) NULL DEFAULT NULL,
  `api_secret_ciphertext` varchar(255) NULL DEFAULT NULL,
  `demo_trading` tinyint(1) NULL DEFAULT NULL,
  `enabled` tinyint(1) NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `health_status` varchar(255) NULL DEFAULT NULL,
  `last_error_message` text NULL,
  `last_validated_at` datetime NULL DEFAULT NULL,
  `leverage_mode` varchar(255) NULL DEFAULT NULL,
  `margin_mode` varchar(255) NULL DEFAULT NULL,
  `passphrase_ciphertext` varchar(255) NULL DEFAULT NULL,
  `position_mode` varchar(255) NULL DEFAULT NULL,
  `settle_currency` varchar(255) NULL DEFAULT NULL,
  `testnet` tinyint(1) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `exchange_account_binding`;
CREATE TABLE `exchange_account_binding` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `account_id` bigint NULL DEFAULT NULL,
  `enabled` tinyint(1) NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `strategy_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_exchange_account_binding_strategy_id`(`strategy_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `exchange_fill`;
CREATE TABLE `exchange_fill` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `exec_type` varchar(255) NULL DEFAULT NULL,
  `fee` decimal(36,18) NULL DEFAULT NULL,
  `fee_ccy` varchar(255) NULL DEFAULT NULL,
  `fill_price` decimal(36,18) NULL DEFAULT NULL,
  `fill_quantity` decimal(36,18) NULL DEFAULT NULL,
  `filled_at` datetime NULL DEFAULT NULL,
  `is_maker` tinyint(1) NULL DEFAULT NULL,
  `order_ref` varchar(255) NULL DEFAULT NULL,
  `position_side` varchar(255) NULL DEFAULT NULL,
  `raw_payload` text NULL,
  `realized_pnl` decimal(36,18) NULL DEFAULT NULL,
  `side` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `trade_id` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_exchange_fill_trade_id`(`trade_id`) USING BTREE,
  INDEX `idx_exchange_fill_exchange_code`(`exchange_code`) USING BTREE,
  INDEX `idx_exchange_fill_trace_id`(`trace_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `exchange_order`;
CREATE TABLE `exchange_order` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(255) NULL DEFAULT NULL,
  `avg_fill_price` decimal(36,18) NULL DEFAULT NULL,
  `client_order_id` varchar(255) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `fee` decimal(36,18) NULL DEFAULT NULL,
  `fee_ccy` varchar(255) NULL DEFAULT NULL,
  `filled_at` datetime NULL DEFAULT NULL,
  `filled_quantity` decimal(36,18) NULL DEFAULT NULL,
  `leverage` decimal(36,18) NULL DEFAULT NULL,
  `limit_price` decimal(36,18) NULL DEFAULT NULL,
  `mode` varchar(255) NULL DEFAULT NULL,
  `okx_enhanced_execution` tinyint(1) NULL DEFAULT NULL,
  `order_ref` varchar(255) NULL DEFAULT NULL,
  `order_status` varchar(255) NULL DEFAULT NULL,
  `order_type` varchar(255) NULL DEFAULT NULL,
  `position_side` varchar(255) NULL DEFAULT NULL,
  `post_only` tinyint(1) NULL DEFAULT NULL,
  `quantity_base` decimal(36,18) NULL DEFAULT NULL,
  `raw_payload` text NULL,
  `reduce_only` tinyint(1) NULL DEFAULT NULL,
  `side` varchar(255) NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `td_mode` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `updated_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_exchange_order_trace_id`(`trace_id`) USING BTREE,
  INDEX `idx_exchange_order_order_status`(`order_status`) USING BTREE,
  INDEX `idx_exchange_order_created_at`(`created_at`) USING BTREE,
  INDEX `idx_exchange_order_exchange_code`(`exchange_code`) USING BTREE,
  INDEX `idx_exchange_order_order_ref`(`order_ref`) USING BTREE,
  INDEX `idx_exchange_order_symbol`(`symbol`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `feature_snapshot`;
CREATE TABLE `feature_snapshot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime NULL DEFAULT NULL,
  `event_strength` varchar(255) NULL DEFAULT NULL,
  `snapshot_json` longtext NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_feature_snapshot_trace_id`(`trace_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `market_api_config`;
CREATE TABLE `market_api_config` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `api_name` varchar(255) NULL DEFAULT NULL,
  `api_url` varchar(500) NULL DEFAULT NULL,
  `apply_symbols` varchar(255) NULL DEFAULT NULL,
  `config_name` varchar(255) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `data_category` varchar(255) NULL DEFAULT NULL,
  `data_sub_type` varchar(255) NULL DEFAULT NULL,
  `data_transform` text NULL,
  `doc_reference_url` varchar(500) NULL DEFAULT NULL,
  `enabled` varchar(255) NULL DEFAULT NULL,
  `field_mapping` text NULL,
  `http_method` varchar(255) NULL DEFAULT NULL,
  `market_scope` varchar(16) NULL DEFAULT NULL,
  `priority` int NULL DEFAULT NULL,
  `proxy_url` varchar(500) NULL DEFAULT NULL,
  `remark` text NULL,
  `request_body` text NULL,
  `request_headers` text NULL,
  `response_path` varchar(500) NULL DEFAULT NULL,
  `retry_count` int NULL DEFAULT NULL,
  `retry_interval` int NULL DEFAULT NULL,
  `timeout` int NULL DEFAULT NULL,
  `transport_type` varchar(16) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `use_proxy` varchar(255) NULL DEFAULT NULL,
  `vendor_code` varchar(32) NULL DEFAULT NULL,
  `version_no` int NOT NULL DEFAULT 1,
  `ws_base_url` varchar(255) NULL DEFAULT NULL,
  `ws_combined_enabled` tinyint(1) NULL DEFAULT NULL,
  `ws_connection_ttl_hours` int NULL DEFAULT NULL,
  `ws_control_messages_per_second` int NULL DEFAULT NULL,
  `ws_max_streams_per_connection` int NULL DEFAULT NULL,
  `ws_path` varchar(500) NULL DEFAULT NULL,
  `ws_ping_interval_seconds` int NULL DEFAULT NULL,
  `ws_pong_timeout_seconds` int NULL DEFAULT NULL,
  `ws_stream_name_template` text NULL,
  `ws_symbol_lowercase` tinyint(1) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_market_api_config_priority`(`priority`) USING BTREE,
  INDEX `idx_market_api_config_enabled`(`enabled`) USING BTREE,
  INDEX `idx_market_api_config_data_category`(`data_category`) USING BTREE,
  INDEX `idx_market_api_config_api_name`(`api_name`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `market_collect_task`;
CREATE TABLE `market_collect_task` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `collect_fear_greed` varchar(255) NULL DEFAULT NULL,
  `collect_gas` varchar(255) NULL DEFAULT NULL,
  `collect_interval` int NULL DEFAULT NULL,
  `collect_kline_1d` varchar(255) NULL DEFAULT NULL,
  `collect_kline_1h` varchar(255) NULL DEFAULT NULL,
  `collect_kline_4h` varchar(255) NULL DEFAULT NULL,
  `collect_onchain` varchar(255) NULL DEFAULT NULL,
  `collect_price` varchar(255) NULL DEFAULT NULL,
  `collect_volume` varchar(255) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `enabled` varchar(255) NULL DEFAULT NULL,
  `gas_api_id` bigint NULL DEFAULT NULL,
  `kline_api_id` bigint NULL DEFAULT NULL,
  `onchain_api_id` bigint NULL DEFAULT NULL,
  `price_api_id` bigint NULL DEFAULT NULL,
  `remark` text NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `task_name` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `volume_api_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_market_collect_task_enabled`(`enabled`) USING BTREE,
  INDEX `idx_market_collect_task_symbol`(`symbol`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `market_data`;
CREATE TABLE `market_data` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `collection_time` datetime NULL DEFAULT NULL,
  `data_source` varchar(255) NULL DEFAULT NULL,
  `exchange_inflow` decimal(36,18) NULL DEFAULT NULL,
  `exchange_outflow` decimal(36,18) NULL DEFAULT NULL,
  `fear_greed_classification` varchar(255) NULL DEFAULT NULL,
  `fear_greed_index` int NULL DEFAULT NULL,
  `high_24h` decimal(36,18) NULL DEFAULT NULL,
  `kline_1d_close` decimal(36,18) NULL DEFAULT NULL,
  `kline_1d_high` decimal(36,18) NULL DEFAULT NULL,
  `kline_1d_low` decimal(36,18) NULL DEFAULT NULL,
  `kline_1d_open` decimal(36,18) NULL DEFAULT NULL,
  `kline_1d_timestamp` bigint NULL DEFAULT NULL,
  `kline_1d_volume` decimal(36,18) NULL DEFAULT NULL,
  `kline_1h_close` decimal(36,18) NULL DEFAULT NULL,
  `kline_1h_high` decimal(36,18) NULL DEFAULT NULL,
  `kline_1h_low` decimal(36,18) NULL DEFAULT NULL,
  `kline_1h_open` decimal(36,18) NULL DEFAULT NULL,
  `kline_1h_timestamp` bigint NULL DEFAULT NULL,
  `kline_1h_volume` decimal(36,18) NULL DEFAULT NULL,
  `kline_4h_close` decimal(36,18) NULL DEFAULT NULL,
  `kline_4h_high` decimal(36,18) NULL DEFAULT NULL,
  `kline_4h_low` decimal(36,18) NULL DEFAULT NULL,
  `kline_4h_open` decimal(36,18) NULL DEFAULT NULL,
  `kline_4h_timestamp` bigint NULL DEFAULT NULL,
  `kline_4h_volume` decimal(36,18) NULL DEFAULT NULL,
  `low_24h` decimal(36,18) NULL DEFAULT NULL,
  `net_flow` decimal(36,18) NULL DEFAULT NULL,
  `price` decimal(36,18) NULL DEFAULT NULL,
  `price_change_24h` decimal(36,18) NULL DEFAULT NULL,
  `price_change_percent_24h` decimal(36,18) NULL DEFAULT NULL,
  `raw_data` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `timestamp` bigint NULL DEFAULT NULL,
  `volume_24h` decimal(36,18) NULL DEFAULT NULL,
  `volume_24h_base` decimal(36,18) NULL DEFAULT NULL,
  `whale_transactions` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_market_data_symbol`(`symbol`) USING BTREE,
  INDEX `idx_market_data_timestamp`(`timestamp`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `market_data_collect_log`;
CREATE TABLE `market_data_collect_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `collect_type` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `data_sources_used` varchar(255) NULL DEFAULT NULL,
  `duration_ms` bigint NULL DEFAULT NULL,
  `error_message` text NULL,
  `fail_count` int NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `success_count` int NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `market_data_config`;
CREATE TABLE `market_data_config` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `api_key_config` text NULL,
  `collect_fear_greed` varchar(255) NULL DEFAULT NULL,
  `collect_interval` int NULL DEFAULT NULL,
  `collect_kline` varchar(255) NULL DEFAULT NULL,
  `collect_onchain` varchar(255) NULL DEFAULT NULL,
  `config_name` varchar(255) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `data_sources` varchar(255) NULL DEFAULT NULL,
  `enabled` varchar(255) NULL DEFAULT NULL,
  `kline_periods` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_market_data_config_enabled`(`enabled`) USING BTREE,
  INDEX `idx_market_data_config_symbol`(`symbol`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `market_event`;
CREATE TABLE `market_event` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `price` decimal(36,18) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `volume` decimal(36,18) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX idx_market_event_created_at (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `market_kline_snapshot`;
CREATE TABLE `market_kline_snapshot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `close_price` decimal(36,18) NULL DEFAULT NULL,
  `close_time` datetime NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `high_price` decimal(36,18) NULL DEFAULT NULL,
  `interval_code` varchar(255) NULL DEFAULT NULL,
  `low_price` decimal(36,18) NULL DEFAULT NULL,
  `open_price` decimal(36,18) NULL DEFAULT NULL,
  `open_time` datetime NULL DEFAULT NULL,
  `payload_json` longtext NULL,
  `quote_volume` decimal(36,18) NULL DEFAULT NULL,
  `source` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `trade_count` bigint NULL DEFAULT NULL,
  `volume` decimal(36,18) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX idx_market_kline_snapshot_created_at (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `market_metric_snapshot`;
CREATE TABLE `market_metric_snapshot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `funding_rate` decimal(36,18) NULL DEFAULT NULL,
  `largest_liquidation_notional_usd` decimal(36,18) NULL DEFAULT NULL,
  `largest_liquidation_side` varchar(255) NULL DEFAULT NULL,
  `latest_price` decimal(36,18) NULL DEFAULT NULL,
  `liquidation_notional_15m` decimal(36,18) NULL DEFAULT NULL,
  `liquidation_notional_240m` decimal(36,18) NULL DEFAULT NULL,
  `liquidation_notional_60m` decimal(36,18) NULL DEFAULT NULL,
  `mark_price` decimal(36,18) NULL DEFAULT NULL,
  `mark_price_deviation_pct` decimal(36,18) NULL DEFAULT NULL,
  `observed_at` datetime NULL DEFAULT NULL,
  `open_interest` decimal(36,18) NULL DEFAULT NULL,
  `payload_json` longtext NULL,
  `quote_volume_24h` decimal(36,18) NULL DEFAULT NULL,
  `source_status` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `volume_24h` decimal(36,18) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX idx_market_metric_snapshot_created_at (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `news_event`;
CREATE TABLE `news_event` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `headline` varchar(255) NULL DEFAULT NULL,
  `source` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX idx_news_event_created_at (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `notify_channel`;
CREATE TABLE `notify_channel` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `channel_name` varchar(255) NULL DEFAULT NULL,
  `channel_type` varchar(255) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `is_enabled` int NULL DEFAULT NULL,
  `mail_from` varchar(255) NULL DEFAULT NULL,
  `mail_password` varchar(255) NULL DEFAULT NULL,
  `mail_username` varchar(255) NULL DEFAULT NULL,
  `recipient` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `smtp_host` varchar(255) NULL DEFAULT NULL,
  `smtp_port` int NULL DEFAULT NULL,
  `token` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `user_id` bigint NULL DEFAULT NULL,
  `webhook_url` varchar(500) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_notify_channel_create_time`(`create_time`) USING BTREE,
  INDEX `idx_notify_channel_user_id`(`user_id`) USING BTREE,
  INDEX `idx_notify_channel_is_enabled`(`is_enabled`) USING BTREE,
  INDEX `idx_notify_channel_channel_type`(`channel_type`) USING BTREE,
  INDEX `idx_notify_channel_channel_name`(`channel_name`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `notify_record`;
CREATE TABLE `notify_record` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `channel_id` bigint NULL DEFAULT NULL,
  `channel_name` varchar(255) NULL DEFAULT NULL,
  `channel_type` varchar(255) NULL DEFAULT NULL,
  `content` text NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `error_msg` varchar(255) NULL DEFAULT NULL,
  `ext_data` varchar(255) NULL DEFAULT NULL,
  `recipient` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `retry_count` int NULL DEFAULT NULL,
  `send_time` datetime NULL DEFAULT NULL,
  `status` int NULL DEFAULT NULL,
  `template_id` bigint NULL DEFAULT NULL,
  `template_vars` varchar(255) NULL DEFAULT NULL,
  `title` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_notify_record_create_time`(`create_time`) USING BTREE,
  INDEX `idx_notify_record_status`(`status`) USING BTREE,
  INDEX `idx_notify_record_channel_id`(`channel_id`) USING BTREE,
  INDEX `idx_notify_record_trace_id`(`trace_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `notify_template`;
CREATE TABLE `notify_template` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `code` varchar(255) NULL DEFAULT NULL,
  `content_template` text NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `is_active` int NULL DEFAULT NULL,
  `is_default` int NULL DEFAULT NULL,
  `name` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `title_template` text NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `variables` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_notify_template_code`(`code`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `onchain_event`;
CREATE TABLE `onchain_event` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `payload_json` longtext NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `wallet` varchar(255) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX idx_onchain_event_created_at (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `order_request`;
CREATE TABLE `order_request` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(255) NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `leverage` decimal(36,18) NULL DEFAULT NULL,
  `limit_price` decimal(36,18) NULL DEFAULT NULL,
  `mode` varchar(255) NULL DEFAULT NULL,
  `okx_enhanced_execution` tinyint(1) NULL DEFAULT NULL,
  `order_type` varchar(255) NULL DEFAULT NULL,
  `position_side` varchar(255) NULL DEFAULT NULL,
  `quantity_base` decimal(36,18) NULL DEFAULT NULL,
  `quote_amount` decimal(36,18) NULL DEFAULT NULL,
  `reduce_only` tinyint(1) NULL DEFAULT NULL,
  `side` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `td_mode` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `paper_trade_order`;
CREATE TABLE `paper_trade_order` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `execution_status` varchar(255) NULL DEFAULT NULL,
  `mode` varchar(255) NULL DEFAULT NULL,
  `order_ref` varchar(255) NULL DEFAULT NULL,
  `order_status` varchar(255) NULL DEFAULT NULL,
  `quote_amount` decimal(36,18) NULL DEFAULT NULL,
  `side` varchar(255) NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `pnl_snapshot`;
CREATE TABLE `pnl_snapshot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `account_equity` decimal(36,18) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `daily_pnl` decimal(36,18) NULL DEFAULT NULL,
  `max_drawdown_pct` decimal(36,18) NULL DEFAULT NULL,
  `mode` varchar(255) NULL DEFAULT NULL,
  `peak_account_equity` decimal(36,18) NULL DEFAULT NULL,
  `realized_pnl` decimal(36,18) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `unrealized_pnl` decimal(36,18) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_pnl_snapshot_created_at`(`created_at`) USING BTREE,
  INDEX `idx_pnl_snapshot_mode`(`mode`) USING BTREE,
  INDEX `idx_pnl_snapshot_trace_id`(`trace_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `position_change_log`;
CREATE TABLE `position_change_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `after_quantity` decimal(36,18) NULL DEFAULT NULL,
  `before_quantity` decimal(36,18) NULL DEFAULT NULL,
  `change_type` varchar(255) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `delta_quantity` decimal(36,18) NULL DEFAULT NULL,
  `entry_price` decimal(36,18) NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `side` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `unrealized_pnl` decimal(36,18) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_position_change_log_exchange_code`(`exchange_code`) USING BTREE,
  INDEX `idx_position_change_log_symbol`(`symbol`) USING BTREE,
  INDEX `idx_position_change_log_side`(`side`) USING BTREE,
  INDEX `idx_position_change_log_after_quantity`(`after_quantity`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `position_snapshot`;
CREATE TABLE `position_snapshot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime NULL DEFAULT NULL,
  `entry_price` decimal(36,18) NULL DEFAULT NULL,
  `entry_trace_id` varchar(64) NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `position_quantity` decimal(36,18) NULL DEFAULT NULL,
  `side` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `unrealized_pnl` decimal(36,18) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_position_snapshot_created_at`(`created_at`) USING BTREE,
  INDEX `idx_position_snapshot_exchange_code`(`exchange_code`) USING BTREE,
  INDEX `idx_position_snapshot_symbol`(`symbol`) USING BTREE,
  INDEX `idx_position_snapshot_position_quantity`(`position_quantity`) USING BTREE,
  INDEX `idx_position_snapshot_side`(`side`) USING BTREE,
  INDEX `idx_position_snapshot_trace_id`(`trace_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `prompt_template`;
CREATE TABLE `prompt_template` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `code` varchar(255) NULL DEFAULT NULL,
  `content` text NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `is_active` int NULL DEFAULT NULL,
  `is_default` int NULL DEFAULT NULL,
  `name` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `variables` varchar(255) NULL DEFAULT NULL,
  `version` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_prompt_template_code`(`code`) USING BTREE,
  INDEX `idx_prompt_template_version`(`version`) USING BTREE,
  INDEX `idx_prompt_template_is_active`(`is_active`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `replay_event`;
CREATE TABLE `replay_event` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_type` varchar(255) NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `payload_json` longtext NULL,
  `session_id` bigint NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `replay_session`;
CREATE TABLE `replay_session` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `mode` varchar(255) NULL DEFAULT NULL,
  `replay_trace_id` varchar(64) NULL DEFAULT NULL,
  `session_name` varchar(255) NULL DEFAULT NULL,
  `source_trace_id` varchar(64) NULL DEFAULT NULL,
  `source_type` varchar(255) NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `risk_guard_hit`;
CREATE TABLE `risk_guard_hit` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime NULL DEFAULT NULL,
  `reason` text NULL,
  `rule_code` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_risk_guard_hit_trace_id`(`trace_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `shadow_decision_log`;
CREATE TABLE `shadow_decision_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(255) NULL DEFAULT NULL,
  `binding_template_code` varchar(255) NULL DEFAULT NULL,
  `confidence` int NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `execution_status` varchar(255) NULL DEFAULT NULL,
  `fallback_template_code` varchar(255) NULL DEFAULT NULL,
  `mode` varchar(255) NULL DEFAULT NULL,
  `model_code` varchar(255) NULL DEFAULT NULL,
  `model_provider` varchar(255) NULL DEFAULT NULL,
  `order_status` varchar(255) NULL DEFAULT NULL,
  `prompt_source` varchar(255) NULL DEFAULT NULL,
  `prompt_template_fallback_used` tinyint(1) NULL DEFAULT NULL,
  `resolved_template_code` varchar(255) NULL DEFAULT NULL,
  `side` varchar(255) NULL DEFAULT NULL,
  `summary_reason` text NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_shadow_decision_log_trace_id`(`trace_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `signal_event`;
CREATE TABLE `signal_event` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime NULL DEFAULT NULL,
  `feature_json` longtext NULL,
  `signal_type` varchar(255) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_signal_event_trace_id`(`trace_id`) USING BTREE,
  INDEX `idx_signal_event_created_at`(`created_at`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `signal_score`;
CREATE TABLE `signal_score` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime NULL DEFAULT NULL,
  `score` decimal(36,18) NULL DEFAULT NULL,
  `signal_event_id` bigint NULL DEFAULT NULL,
  `signal_type` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_signal_score_created_at`(`created_at`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `signal_window_state`;
CREATE TABLE `signal_window_state` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `combine_until_at` datetime NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `decay_score` decimal(36,18) NULL DEFAULT NULL,
  `dedupe_key` varchar(255) NULL DEFAULT NULL,
  `direction` varchar(255) NULL DEFAULT NULL,
  `expires_at` datetime NULL DEFAULT NULL,
  `is_active` tinyint(1) NULL DEFAULT NULL,
  `last_confirmed_at` datetime NULL DEFAULT NULL,
  `last_event_at` datetime NULL DEFAULT NULL,
  `opened_at` datetime NULL DEFAULT NULL,
  `signal_type` varchar(255) NULL DEFAULT NULL,
  `source_type` varchar(255) NULL DEFAULT NULL,
  `state_json` longtext NULL,
  `strength_score` decimal(36,18) NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `window_key` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_signal_window_state_is_active`(`is_active`) USING BTREE,
  INDEX `idx_signal_window_state_symbol`(`symbol`) USING BTREE,
  INDEX `idx_signal_window_state_expires_at`(`expires_at`) USING BTREE,
  INDEX `idx_signal_window_state_last_event_at`(`last_event_at`) USING BTREE,
  INDEX `idx_signal_window_state_created_at`(`created_at`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `social_event`;
CREATE TABLE `social_event` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `payload_json` longtext NULL,
  `score` double NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'row create time',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX idx_social_event_created_at (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_agent_profile`;
CREATE TABLE `trade_agent_profile` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_code` varchar(255) NULL DEFAULT NULL,
  `agent_name` varchar(255) NULL DEFAULT NULL,
  `agent_type` varchar(255) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `default_fallback_template_code` varchar(255) NULL DEFAULT NULL,
  `default_model_id` bigint NULL DEFAULT NULL,
  `default_output_schema_code` varchar(64) NULL DEFAULT NULL,
  `default_template_code` varchar(64) NULL DEFAULT NULL,
  `dialogue_enabled` tinyint(1) NULL DEFAULT NULL,
  `enabled` tinyint(1) NULL DEFAULT NULL,
  `llm_enabled` tinyint(1) NULL DEFAULT NULL,
  `max_dialogue_rounds` int NULL DEFAULT NULL,
  `max_retries` int NULL DEFAULT NULL,
  `max_tokens_override` int NULL DEFAULT NULL,
  `remark` text NULL,
  `runtime_options_json` longtext NULL,
  `speak_order` int NULL DEFAULT NULL,
  `structured_schema_code` varchar(255) NULL DEFAULT NULL,
  `temperature_override` decimal(36,18) NULL DEFAULT NULL,
  `timeout_seconds` int NULL DEFAULT NULL,
  `tool_policy_json` longtext NULL,
  `top_p_override` decimal(36,18) NULL DEFAULT NULL,
  `updated_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_trade_agent_profile_speak_order`(`speak_order`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_data_source_binding`;
CREATE TABLE `trade_data_source_binding` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `binding_name` varchar(255) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `enabled` tinyint(1) NULL DEFAULT NULL,
  `event_type` varchar(255) NULL DEFAULT NULL,
  `exchange_scope_json` longtext NULL,
  `mode_scope_json` longtext NULL,
  `source_id` bigint NULL DEFAULT NULL,
  `strategy_id` bigint NULL DEFAULT NULL,
  `symbol_scope_json` longtext NULL,
  `updated_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_data_source_health_log`;
CREATE TABLE `trade_data_source_health_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `check_type` varchar(255) NULL DEFAULT NULL,
  `error_message` text NULL,
  `latency_ms` bigint NULL DEFAULT NULL,
  `response_excerpt` varchar(255) NULL DEFAULT NULL,
  `source_id` bigint NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_lifecycle`;
CREATE TABLE `trade_lifecycle` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `add_operations_json` longtext NULL,
  `agent_views_json` longtext NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `entry_conditions_json` longtext NULL,
  `entry_price` decimal(36,18) NULL DEFAULT NULL,
  `entry_reason` text NULL,
  `entry_time` datetime NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `exit_price` decimal(36,18) NULL DEFAULT NULL,
  `exit_reason` text NULL,
  `exit_time` datetime NULL DEFAULT NULL,
  `holding_minutes` int NULL DEFAULT NULL,
  `lesson_text` text NULL,
  `max_adverse_pct` decimal(36,18) NULL DEFAULT NULL,
  `max_favorable_pct` decimal(36,18) NULL DEFAULT NULL,
  `memory_generated` tinyint(1) NULL DEFAULT NULL,
  `memory_reason` text NULL,
  `memory_status` varchar(255) NULL DEFAULT NULL,
  `price_trajectory_json` longtext NULL,
  `realized_pnl_pct` decimal(36,18) NULL DEFAULT NULL,
  `reduce_operations_json` longtext NULL,
  `side` varchar(255) NULL DEFAULT NULL,
  `supervisor_decision_json` longtext NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `trace_id` varchar(64) NULL DEFAULT NULL,
  `updated_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_trade_lifecycle_trace_id`(`trace_id`) USING BTREE,
  INDEX `idx_trade_lifecycle_memory_status`(`memory_status`) USING BTREE,
  INDEX `idx_trade_lifecycle_memory_generated`(`memory_generated`) USING BTREE,
  INDEX `idx_trade_lifecycle_exit_time`(`exit_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_notify_policy`;
CREATE TABLE `trade_notify_policy` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime NULL DEFAULT NULL,
  `enabled` tinyint(1) NULL DEFAULT NULL,
  `event_scope_json` longtext NULL,
  `mode_scope_json` longtext NULL,
  `policy_name` varchar(255) NULL DEFAULT NULL,
  `policy_scope` varchar(255) NULL DEFAULT NULL,
  `severity_scope_json` longtext NULL,
  `strategy_id` bigint NULL DEFAULT NULL,
  `template_code` varchar(255) NULL DEFAULT NULL,
  `throttle_seconds` int NULL DEFAULT NULL,
  `updated_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_notify_policy_channel`;
CREATE TABLE `trade_notify_policy_channel` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `channel_id` bigint NULL DEFAULT NULL,
  `channel_order` int NULL DEFAULT NULL,
  `enabled` tinyint(1) NULL DEFAULT NULL,
  `policy_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_trade_notify_policy_channel_policy_id`(`policy_id`) USING BTREE,
  INDEX `idx_trade_notify_policy_channel_channel_order`(`channel_order`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_position_guard`;
CREATE TABLE `trade_position_guard` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `create_time` datetime NULL DEFAULT NULL,
  `enabled` tinyint(1) NULL DEFAULT NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `guard_name` varchar(255) NULL DEFAULT NULL,
  `max_holding_minutes` int NULL DEFAULT NULL,
  `priority` int NULL DEFAULT NULL,
  `remark` text NULL,
  `scope_type` varchar(255) NULL DEFAULT NULL,
  `stop_loss_pct` decimal(36,18) NULL DEFAULT NULL,
  `strategy_id` bigint NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `take_profit_pct` decimal(36,18) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_trade_position_guard_scope_type`(`scope_type`) USING BTREE,
  INDEX `idx_trade_position_guard_symbol`(`symbol`) USING BTREE,
  INDEX `idx_trade_position_guard_priority`(`priority`) USING BTREE,
  INDEX `idx_trade_position_guard_enabled`(`enabled`) USING BTREE,
  INDEX `idx_trade_position_guard_strategy_id`(`strategy_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_prompt_binding`;
CREATE TABLE `trade_prompt_binding` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `binding_name` varchar(255) NULL DEFAULT NULL,
  `binding_scope` varchar(255) NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `enabled` tinyint(1) NULL DEFAULT NULL,
  `event_strength_scope_json` longtext NULL,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `fallback_template_code` varchar(255) NULL DEFAULT NULL,
  `mode_scope_json` longtext NULL,
  `model_id` bigint NULL DEFAULT NULL,
  `output_schema_code` varchar(64) NULL DEFAULT NULL,
  `priority` int NULL DEFAULT NULL,
  `remark` text NULL,
  `strategy_id` bigint NULL DEFAULT NULL,
  `strategy_version_id` bigint NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  `template_code` varchar(64) NULL DEFAULT NULL,
  `updated_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_trade_prompt_binding_priority`(`priority`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_runtime_config`;
CREATE TABLE `trade_runtime_config` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `allowed_exchanges_json` longtext NULL,
  `allowed_symbols_json` longtext NULL,
  `default_mode` varchar(255) NULL DEFAULT NULL,
  `deliberation_enabled` tinyint(1) NULL DEFAULT NULL,
  `deliberation_fail_open` tinyint(1) NULL DEFAULT NULL,
  `deliberation_max_rounds` int NULL DEFAULT NULL,
  `event_retention_days` int NULL DEFAULT NULL,
  `live_enabled` tinyint(1) NULL DEFAULT NULL,
  `live_order_requires_healthy_account` tinyint(1) NULL DEFAULT NULL,
  `max_consecutive_failures` int NULL DEFAULT NULL,
  `max_daily_loss` decimal(36,18) NULL DEFAULT NULL,
  `max_position_ratio` decimal(36,18) NULL DEFAULT NULL,
  `notify_defaults_json` longtext NULL,
  `replay_retention_days` int NULL DEFAULT NULL,
  `require_account_binding` tinyint(1) NULL DEFAULT NULL,
  `route_max_concurrency` int NULL DEFAULT NULL,
  `route_scheduler_mode` varchar(255) NULL DEFAULT NULL,
  `runtime_flags_json` longtext NULL,
  `singleton_key` tinyint NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_trade_runtime_config_singleton`(`singleton_key`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_strategy`;
CREATE TABLE `trade_strategy` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `enabled` tinyint(1) NULL DEFAULT NULL,
  `exchanges_json` longtext NULL,
  `runtime_mode` varchar(255) NULL DEFAULT NULL,
  `strategy_key` varchar(255) NULL DEFAULT NULL,
  `strategy_name` varchar(255) NULL DEFAULT NULL,
  `symbols_json` longtext NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_strategy_version`;
CREATE TABLE `trade_strategy_version` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `config_json` longtext NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `strategy_id` bigint NULL DEFAULT NULL,
  `version_no` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_trade_strategy_version_strategy_id`(`strategy_id`) USING BTREE,
  INDEX `idx_trade_strategy_version_version_no`(`version_no`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `trade_symbol_scope`;
CREATE TABLE `trade_symbol_scope` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `exchange_code` varchar(255) NULL DEFAULT NULL,
  `strategy_id` bigint NULL DEFAULT NULL,
  `symbol` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_trade_symbol_scope_strategy_id`(`strategy_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;