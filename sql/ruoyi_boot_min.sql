-- Minimal RuoYi framework schema
-- Reconstructed from MyBatis mappers + Java entities: the upstream repository
-- ships no schema dump (sql/ai_trading.sql is gitignored, and the bootstrap
-- scripts referenced by deploy/prod/README.md were never committed).
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `gen_table`;
CREATE TABLE `gen_table` (
  `table_id` bigint NOT NULL AUTO_INCREMENT,
  `business_name` varchar(255) NULL DEFAULT NULL,
  `class_name` varchar(255) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `function_author` varchar(255) NULL DEFAULT NULL,
  `function_name` varchar(255) NULL DEFAULT NULL,
  `gen_path` varchar(500) NULL DEFAULT NULL,
  `gen_type` varchar(255) NULL DEFAULT NULL,
  `module_name` varchar(255) NULL DEFAULT NULL,
  `options` varchar(255) NULL DEFAULT NULL,
  `package_name` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `sub_table_fk_name` varchar(255) NULL DEFAULT NULL,
  `sub_table_name` varchar(255) NULL DEFAULT NULL,
  `table_comment` varchar(255) NULL DEFAULT NULL,
  `table_name` varchar(255) NULL DEFAULT NULL,
  `tpl_category` varchar(255) NULL DEFAULT NULL,
  `tpl_web_type` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`table_id`) USING BTREE,
  INDEX `idx_gen_table_table_name`(`table_name`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `gen_table_column`;
CREATE TABLE `gen_table_column` (
  `column_id` bigint NOT NULL AUTO_INCREMENT,
  `column_comment` varchar(255) NULL DEFAULT NULL,
  `column_name` varchar(255) NULL DEFAULT NULL,
  `column_type` varchar(255) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `dict_type` varchar(255) NULL DEFAULT NULL,
  `html_type` varchar(255) NULL DEFAULT NULL,
  `is_edit` varchar(255) NULL DEFAULT NULL,
  `is_increment` varchar(255) NULL DEFAULT NULL,
  `is_insert` varchar(255) NULL DEFAULT NULL,
  `is_list` varchar(255) NULL DEFAULT NULL,
  `is_pk` varchar(255) NULL DEFAULT NULL,
  `is_query` varchar(255) NULL DEFAULT NULL,
  `is_required` varchar(255) NULL DEFAULT NULL,
  `java_field` varchar(255) NULL DEFAULT NULL,
  `java_type` varchar(255) NULL DEFAULT NULL,
  `query_type` varchar(255) NULL DEFAULT NULL,
  `sort` int NULL DEFAULT NULL,
  `table_id` bigint NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`column_id`) USING BTREE,
  INDEX `idx_gen_table_column_table_id`(`table_id`) USING BTREE,
  INDEX `idx_gen_table_column_sort`(`sort`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_config`;
CREATE TABLE `sys_config` (
  `config_id` bigint NOT NULL AUTO_INCREMENT,
  `config_key` varchar(255) NULL DEFAULT NULL,
  `config_name` varchar(255) NULL DEFAULT NULL,
  `config_type` varchar(255) NULL DEFAULT NULL,
  `config_value` varchar(255) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `remark` text NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`config_id`) USING BTREE,
  INDEX `idx_sys_config_config_key`(`config_key`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_dept`;
CREATE TABLE `sys_dept` (
  `dept_id` bigint NOT NULL AUTO_INCREMENT,
  `ancestors` varchar(255) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `del_flag` varchar(255) NULL DEFAULT NULL,
  `dept_name` varchar(255) NULL DEFAULT NULL,
  `email` varchar(255) NULL DEFAULT NULL,
  `leader` varchar(255) NULL DEFAULT NULL,
  `order_num` int NULL DEFAULT NULL,
  `parent_id` bigint NULL DEFAULT NULL,
  `parent_name` varchar(255) NULL DEFAULT NULL,
  `phone` varchar(255) NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`dept_id`) USING BTREE,
  INDEX `idx_sys_dept_parent_id`(`parent_id`) USING BTREE,
  INDEX `idx_sys_dept_del_flag`(`del_flag`) USING BTREE,
  INDEX `idx_sys_dept_dept_name`(`dept_name`) USING BTREE,
  INDEX `idx_sys_dept_status`(`status`) USING BTREE,
  INDEX `idx_sys_dept_order_num`(`order_num`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_dict_data`;
CREATE TABLE `sys_dict_data` (
  `dict_code` bigint NOT NULL AUTO_INCREMENT,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `css_class` varchar(255) NULL DEFAULT NULL,
  `dict_label` varchar(255) NULL DEFAULT NULL,
  `dict_sort` bigint NULL DEFAULT NULL,
  `dict_type` varchar(255) NULL DEFAULT NULL,
  `dict_value` varchar(255) NULL DEFAULT NULL,
  `is_default` varchar(255) NULL DEFAULT NULL,
  `list_class` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`dict_code`) USING BTREE,
  INDEX `idx_sys_dict_data_dict_type`(`dict_type`) USING BTREE,
  INDEX `idx_sys_dict_data_dict_sort`(`dict_sort`) USING BTREE,
  INDEX `idx_sys_dict_data_status`(`status`) USING BTREE,
  INDEX `idx_sys_dict_data_dict_value`(`dict_value`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_dict_type`;
CREATE TABLE `sys_dict_type` (
  `dict_id` bigint NOT NULL AUTO_INCREMENT,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `dict_name` varchar(255) NULL DEFAULT NULL,
  `dict_type` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`dict_id`) USING BTREE,
  INDEX `idx_sys_dict_type_dict_type`(`dict_type`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_job`;
CREATE TABLE `sys_job` (
  `job_id` bigint NOT NULL AUTO_INCREMENT,
  `concurrent` varchar(255) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `cron_expression` varchar(255) NULL DEFAULT NULL,
  `invoke_target` varchar(255) NULL DEFAULT NULL,
  `job_group` varchar(255) NULL DEFAULT NULL,
  `job_name` varchar(255) NULL DEFAULT NULL,
  `misfire_policy` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`job_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_job_log`;
CREATE TABLE `sys_job_log` (
  `job_log_id` bigint NOT NULL AUTO_INCREMENT,
  `create_time` datetime NULL DEFAULT NULL,
  `end_time` datetime NULL DEFAULT NULL,
  `exception_info` varchar(255) NULL DEFAULT NULL,
  `invoke_target` varchar(255) NULL DEFAULT NULL,
  `job_group` varchar(255) NULL DEFAULT NULL,
  `job_message` text NULL,
  `job_name` varchar(255) NULL DEFAULT NULL,
  `start_time` datetime NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`job_log_id`) USING BTREE,
  INDEX `idx_sys_job_log_create_time`(`create_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_logininfor`;
CREATE TABLE `sys_logininfor` (
  `info_id` bigint NOT NULL AUTO_INCREMENT,
  `browser` varchar(255) NULL DEFAULT NULL,
  `ipaddr` varchar(255) NULL DEFAULT NULL,
  `login_location` varchar(255) NULL DEFAULT NULL,
  `login_time` datetime NULL DEFAULT NULL,
  `msg` varchar(255) NULL DEFAULT NULL,
  `os` varchar(255) NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `user_name` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`info_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_menu`;
CREATE TABLE `sys_menu` (
  `menu_id` bigint NOT NULL AUTO_INCREMENT,
  `component` varchar(255) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `icon` varchar(500) NULL DEFAULT NULL,
  `is_cache` varchar(255) NULL DEFAULT NULL,
  `is_frame` varchar(255) NULL DEFAULT NULL,
  `menu_name` varchar(255) NULL DEFAULT NULL,
  `menu_type` varchar(255) NULL DEFAULT NULL,
  `order_num` int NULL DEFAULT NULL,
  `parent_id` bigint NULL DEFAULT NULL,
  `parent_name` varchar(255) NULL DEFAULT NULL,
  `path` varchar(500) NULL DEFAULT NULL,
  `perms` varchar(255) NULL DEFAULT NULL,
  `query` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `route_name` varchar(255) NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `visible` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`menu_id`) USING BTREE,
  INDEX `idx_sys_menu_parent_id`(`parent_id`) USING BTREE,
  INDEX `idx_sys_menu_status`(`status`) USING BTREE,
  INDEX `idx_sys_menu_order_num`(`order_num`) USING BTREE,
  INDEX `idx_sys_menu_menu_type`(`menu_type`) USING BTREE,
  INDEX `idx_sys_menu_menu_name`(`menu_name`) USING BTREE,
  INDEX `idx_sys_menu_path`(`path`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_notice`;
CREATE TABLE `sys_notice` (
  `notice_id` bigint NOT NULL AUTO_INCREMENT,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `notice_content` text NULL,
  `notice_title` varchar(255) NULL DEFAULT NULL,
  `notice_type` varchar(255) NULL DEFAULT NULL,
  `remark` text NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`notice_id`) USING BTREE,
  INDEX `idx_sys_notice_status`(`status`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_oper_log`;
CREATE TABLE `sys_oper_log` (
  `oper_id` bigint NOT NULL AUTO_INCREMENT,
  `business_type` int NULL DEFAULT NULL,
  `cost_time` bigint NULL DEFAULT NULL,
  `dept_name` varchar(255) NULL DEFAULT NULL,
  `error_msg` varchar(255) NULL DEFAULT NULL,
  `json_result` text NULL,
  `method` varchar(255) NULL DEFAULT NULL,
  `oper_ip` varchar(255) NULL DEFAULT NULL,
  `oper_location` varchar(255) NULL DEFAULT NULL,
  `oper_name` varchar(255) NULL DEFAULT NULL,
  `oper_param` varchar(255) NULL DEFAULT NULL,
  `oper_time` datetime NULL DEFAULT NULL,
  `oper_url` varchar(500) NULL DEFAULT NULL,
  `operator_type` int NULL DEFAULT NULL,
  `request_method` varchar(255) NULL DEFAULT NULL,
  `status` int NULL DEFAULT NULL,
  `title` varchar(255) NULL DEFAULT NULL,
  PRIMARY KEY (`oper_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_post`;
CREATE TABLE `sys_post` (
  `post_id` bigint NOT NULL AUTO_INCREMENT,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `post_code` varchar(255) NULL DEFAULT NULL,
  `post_name` varchar(255) NULL DEFAULT NULL,
  `post_sort` int NULL DEFAULT NULL,
  `remark` text NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`post_id`) USING BTREE,
  INDEX `idx_sys_post_post_name`(`post_name`) USING BTREE,
  INDEX `idx_sys_post_post_code`(`post_code`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_role`;
CREATE TABLE `sys_role` (
  `role_id` bigint NOT NULL AUTO_INCREMENT,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `data_scope` varchar(255) NULL DEFAULT NULL,
  `del_flag` varchar(255) NULL DEFAULT NULL,
  `dept_check_strictly` tinyint(1) NULL DEFAULT NULL,
  `menu_check_strictly` tinyint(1) NULL DEFAULT NULL,
  `remark` text NULL,
  `role_key` varchar(255) NULL DEFAULT NULL,
  `role_name` varchar(255) NULL DEFAULT NULL,
  `role_sort` int NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`role_id`) USING BTREE,
  INDEX `idx_sys_role_del_flag`(`del_flag`) USING BTREE,
  INDEX `idx_sys_role_role_name`(`role_name`) USING BTREE,
  INDEX `idx_sys_role_role_key`(`role_key`) USING BTREE,
  INDEX `idx_sys_role_status`(`status`) USING BTREE,
  INDEX `idx_sys_role_role_sort`(`role_sort`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_role_dept`;
CREATE TABLE `sys_role_dept` (
  `role_id` bigint NOT NULL,
  `dept_id` bigint NOT NULL,
  PRIMARY KEY (`role_id`, `dept_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_role_menu`;
CREATE TABLE `sys_role_menu` (
  `role_id` bigint NOT NULL,
  `menu_id` bigint NOT NULL,
  PRIMARY KEY (`role_id`, `menu_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `user_id` bigint NOT NULL AUTO_INCREMENT,
  `avatar` varchar(500) NULL DEFAULT NULL,
  `create_by` varchar(255) NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `del_flag` varchar(255) NULL DEFAULT NULL,
  `dept_id` bigint NULL DEFAULT NULL,
  `email` varchar(255) NULL DEFAULT NULL,
  `login_date` datetime NULL DEFAULT NULL,
  `login_ip` varchar(255) NULL DEFAULT NULL,
  `nick_name` varchar(255) NULL DEFAULT NULL,
  `password` varchar(100) NULL DEFAULT NULL,
  `phonenumber` varchar(255) NULL DEFAULT NULL,
  `pwd_update_date` datetime NULL DEFAULT NULL,
  `remark` text NULL,
  `sex` varchar(255) NULL DEFAULT NULL,
  `status` varchar(255) NULL DEFAULT NULL,
  `update_by` varchar(255) NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `user_name` varchar(30) NOT NULL,
  PRIMARY KEY (`user_id`) USING BTREE,
  INDEX `idx_sys_user_del_flag`(`del_flag`) USING BTREE,
  INDEX `idx_sys_user_user_name`(`user_name`) USING BTREE,
  INDEX `idx_sys_user_phonenumber`(`phonenumber`) USING BTREE,
  INDEX `idx_sys_user_dept_id`(`dept_id`) USING BTREE,
  INDEX `idx_sys_user_status`(`status`) USING BTREE,
  INDEX `idx_sys_user_email`(`email`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_user_post`;
CREATE TABLE `sys_user_post` (
  `user_id` bigint NOT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`user_id`, `post_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `sys_user_role`;
CREATE TABLE `sys_user_role` (
  `user_id` bigint NOT NULL,
  `role_id` bigint NOT NULL,
  PRIMARY KEY (`user_id`, `role_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;