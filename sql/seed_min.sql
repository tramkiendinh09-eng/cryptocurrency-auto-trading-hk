-- Seed data for the reconstructed ai_trading schema.
-- Admin credentials are injected at deploy time (__ADMIN_PWD_HASH__).
SET NAMES utf8mb4;

-- ---------- org ----------
DELETE FROM sys_dept;
INSERT INTO sys_dept (dept_id,parent_id,ancestors,dept_name,order_num,leader,status,del_flag,create_by,create_time) VALUES (100,0,'0','量化交易',0,'admin','0','0','admin','2026-09-02 00:00:00');
DELETE FROM sys_post;
INSERT INTO sys_post (post_id,post_code,post_name,post_sort,status,create_by,create_time) VALUES (1,'ceo','运营负责人',1,'0','admin','2026-09-02 00:00:00');

-- ---------- roles ----------
DELETE FROM sys_role;
INSERT INTO sys_role (role_id,role_name,role_key,role_sort,data_scope,menu_check_strictly,dept_check_strictly,status,del_flag,create_by,create_time,remark) VALUES
  (1,'超级管理员','admin',1,'1',1,1,'0','0','admin','2026-09-02 00:00:00','拥有全部权限'),
  (2,'只读观察员','observer',2,'1',1,1,'0','0','admin','2026-09-02 00:00:00','仅可查看，不能下单或改配置');

-- ---------- admin user ----------
DELETE FROM sys_user;
INSERT INTO sys_user (user_id,dept_id,user_name,nick_name,email,phonenumber,sex,avatar,password,status,del_flag,login_ip,login_date,create_by,create_time,remark) VALUES
  (1,100,'admin','管理员','','','0','','__ADMIN_PWD_HASH__','0','0','',NULL,'admin','2026-09-02 00:00:00','初始管理员');
UPDATE sys_user SET pwd_update_date = '2026-09-02 00:00:00' WHERE user_id = 1;
DELETE FROM sys_user_role;
INSERT INTO sys_user_role (user_id,role_id) VALUES (1,1);

-- ---------- menus ----------
DELETE FROM sys_menu;
INSERT INTO sys_menu (menu_id,menu_name,parent_id,order_num,path,component,perms,menu_type,visible,icon,status,is_frame,create_by,create_time) VALUES
  (2000,'交易控制台',0,1,'trade',NULL,NULL,'M','0','monitor','0','0','admin','2026-09-02 00:00:00'),
  (2001,'实盘驾驶舱',2000,1,'monitor','dca/trade/monitor/index','dca:tradeRuntime:query','C','0','dashboard','0','0','admin','2026-09-02 00:00:00'),
  (2002,'运行时监控',2000,2,'runtime','dca/trade/runtime/index','dca:tradeRuntime:query','C','0','monitor','0','0','admin','2026-09-02 00:00:00'),
  (2003,'策略管理',2000,3,'strategy','dca/trade/strategy/index','dca:tradeStrategy:list','C','0','tree','0','0','admin','2026-09-02 00:00:00'),
  (2004,'决策审计',2000,4,'decision','dca/trade/decision/index','dca:audit:list','C','0','form','0','0','admin','2026-09-02 00:00:00'),
  (2005,'订单管理',2000,5,'orders','dca/trade/orders/index','dca:tradeRuntime:query','C','0','list','0','0','admin','2026-09-02 00:00:00'),
  (2006,'成交明细',2000,6,'fills','dca/trade/fills/index','dca:tradeRuntime:query','C','0','documentation','0','0','admin','2026-09-02 00:00:00'),
  (2007,'持仓管理',2000,7,'positions','dca/trade/positions/index','dca:tradeRuntime:query','C','0','chart','0','0','admin','2026-09-02 00:00:00'),
  (2008,'持仓守护',2000,8,'position-guard','dca/trade/positionGuard/index','dca:tradePositionGuard:list','C','0','shield','0','0','admin','2026-09-02 00:00:00'),
  (2009,'风控命中',2000,9,'risk-hits','dca/trade/riskHits/index','dca:tradeRuntime:query','C','0','validCode','0','0','admin','2026-09-02 00:00:00'),
  (2010,'决策回放',2000,10,'replay','dca/trade/replay/index','dca:tradeRuntime:query','C','0','redo','0','0','admin','2026-09-02 00:00:00'),
  (2011,'链路审计',2000,11,'trace-audit','dca/trade/traceAudit/index','dca:audit:list','C','0','log','0','0','admin','2026-09-02 00:00:00'),
  (2012,'交易账户',2000,12,'account','dca/trade/account/index','dca:tradeAccount:list','C','0','money','0','0','admin','2026-09-02 00:00:00'),
  (2013,'Agent 档案',2000,13,'agent-profile','dca/trade/agentProfile/index','dca:tradeAgentProfile:list','C','0','peoples','0','0','admin','2026-09-02 00:00:00'),
  (2014,'Prompt 绑定',2000,14,'prompt-binding','dca/trade/promptBinding/index','dca:tradePromptBinding:list','C','0','edit','0','0','admin','2026-09-02 00:00:00'),
  (2015,'通知策略',2000,15,'notify-policy','dca/trade/notifyPolicy/index','dca:tradeNotifyPolicy:list','C','0','message','0','0','admin','2026-09-02 00:00:00'),
  (2016,'通知模板',2000,16,'notify-template','dca/trade/notifyTemplate/index','dca:notifyTemplate:list','C','0','email','0','0','admin','2026-09-02 00:00:00'),
  (2100,'数据与模型',0,2,'data',NULL,NULL,'M','0','chart','0','0','admin','2026-09-02 00:00:00'),
  (2101,'行情数据',2100,1,'market','dca/market/index','dca:market:query','C','0','international','0','0','admin','2026-09-02 00:00:00'),
  (2102,'AI 模型',2100,2,'ai-model','dca/ai/index','dca:aiModel:list','C','0','component','0','0','admin','2026-09-02 00:00:00'),
  (2103,'提示词模板',2100,3,'template','dca/template/index','dca:template:list','C','0','documentation','0','0','admin','2026-09-02 00:00:00'),
  (2104,'风控配置',2100,4,'risk','dca/risk/index','dca:tradeRuntime:query','C','0','lock','0','0','admin','2026-09-02 00:00:00'),
  (2200,'审计与授权',0,3,'ops',NULL,NULL,'M','0','log','0','0','admin','2026-09-02 00:00:00'),
  (2201,'综合审计',2200,1,'audit','dca/audit/index','dca:audit:list','C','0','form','0','0','admin','2026-09-02 00:00:00'),
  (2202,'卡密管理',2200,2,'card','dca/card/index','dca:card:list','C','0','key','0','0','admin','2026-09-02 00:00:00'),
  (2203,'通知渠道',2200,3,'notify','dca/notify/index','dca:notify:list','C','0','email','0','0','admin','2026-09-02 00:00:00'),
  (2204,'通知记录',2200,4,'notify-record','dca/notify/record','dca:notify:query','C','0','list','0','0','admin','2026-09-02 00:00:00'),
  (1,'系统管理',0,8,'system',NULL,NULL,'M','0','system','0','0','admin','2026-09-02 00:00:00'),
  (2,'系统监控',0,9,'monitor',NULL,NULL,'M','0','monitor','0','0','admin','2026-09-02 00:00:00'),
  (3,'系统工具',0,10,'tool',NULL,NULL,'M','0','tool','0','0','admin','2026-09-02 00:00:00'),
  (100,'用户管理',1,1,'user','system/user/index','system:user:list','C','0','user','0','0','admin','2026-09-02 00:00:00'),
  (101,'角色管理',1,2,'role','system/role/index','system:role:list','C','0','peoples','0','0','admin','2026-09-02 00:00:00'),
  (102,'菜单管理',1,3,'menu','system/menu/index','system:menu:list','C','0','tree-table','0','0','admin','2026-09-02 00:00:00'),
  (103,'部门管理',1,4,'dept','system/dept/index','system:dept:list','C','0','tree','0','0','admin','2026-09-02 00:00:00'),
  (104,'岗位管理',1,5,'post','system/post/index','system:post:list','C','0','post','0','0','admin','2026-09-02 00:00:00'),
  (105,'字典管理',1,6,'dict','system/dict/index','system:dict:list','C','0','dict','0','0','admin','2026-09-02 00:00:00'),
  (106,'参数设置',1,7,'config','system/config/index','system:config:list','C','0','edit','0','0','admin','2026-09-02 00:00:00'),
  (107,'通知公告',1,8,'notice','system/notice/index','system:notice:list','C','0','message','0','0','admin','2026-09-02 00:00:00'),
  (109,'在线用户',2,1,'online','monitor/online/index','monitor:online:list','C','0','online','0','0','admin','2026-09-02 00:00:00'),
  (110,'定时任务',2,2,'job','monitor/job/index','monitor:job:list','C','0','job','0','0','admin','2026-09-02 00:00:00'),
  (111,'数据监控',2,3,'druid','monitor/druid/index','monitor:druid:list','C','0','druid','0','0','admin','2026-09-02 00:00:00'),
  (112,'服务监控',2,4,'server','monitor/server/index','monitor:server:list','C','0','server','0','0','admin','2026-09-02 00:00:00'),
  (113,'缓存监控',2,5,'cache','monitor/cache/index','monitor:cache:list','C','0','redis','0','0','admin','2026-09-02 00:00:00'),
  (500,'操作日志',2,6,'operlog','monitor/operlog/index','monitor:operlog:list','C','0','form','0','0','admin','2026-09-02 00:00:00'),
  (501,'登录日志',2,7,'logininfor','monitor/logininfor/index','monitor:logininfor:list','C','0','logininfor','0','0','admin','2026-09-02 00:00:00'),
  (115,'表单构建',3,1,'build','tool/build/index','tool:build:list','C','0','build','0','0','admin','2026-09-02 00:00:00'),
  (116,'代码生成',3,2,'gen','tool/gen/index','tool:gen:list','C','0','code','0','0','admin','2026-09-02 00:00:00'),
  (117,'系统接口',3,3,'swagger','tool/swagger/index','tool:swagger:list','C','0','swagger','0','0','admin','2026-09-02 00:00:00'),
  (2501,'edit',2001,1,'',NULL,'dca:tradeRuntime:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2502,'add',2002,1,'',NULL,'dca:tradeStrategy:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2503,'edit',2002,2,'',NULL,'dca:tradeStrategy:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2504,'remove',2002,3,'',NULL,'dca:tradeStrategy:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2505,'query',2002,4,'',NULL,'dca:tradeStrategy:query','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2506,'query',2003,1,'',NULL,'dca:audit:query','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2507,'export',2003,2,'',NULL,'dca:audit:export','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2508,'remove',2003,3,'',NULL,'dca:audit:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2509,'clean',2003,4,'',NULL,'dca:audit:clean','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2510,'add',2007,1,'',NULL,'dca:tradePositionGuard:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2511,'edit',2007,2,'',NULL,'dca:tradePositionGuard:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2512,'remove',2007,3,'',NULL,'dca:tradePositionGuard:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2513,'push',2009,1,'',NULL,'dca:taskqueue:push','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2514,'add',2011,1,'',NULL,'dca:tradeAccount:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2515,'edit',2011,2,'',NULL,'dca:tradeAccount:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2516,'remove',2011,3,'',NULL,'dca:tradeAccount:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2517,'add',2012,1,'',NULL,'dca:tradeAgentProfile:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2518,'edit',2012,2,'',NULL,'dca:tradeAgentProfile:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2519,'remove',2012,3,'',NULL,'dca:tradeAgentProfile:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2520,'add',2013,1,'',NULL,'dca:tradePromptBinding:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2521,'edit',2013,2,'',NULL,'dca:tradePromptBinding:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2522,'remove',2013,3,'',NULL,'dca:tradePromptBinding:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2523,'add',2014,1,'',NULL,'dca:tradeNotifyPolicy:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2524,'edit',2014,2,'',NULL,'dca:tradeNotifyPolicy:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2525,'remove',2014,3,'',NULL,'dca:tradeNotifyPolicy:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2526,'add',2015,1,'',NULL,'dca:notifyTemplate:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2527,'edit',2015,2,'',NULL,'dca:notifyTemplate:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2528,'remove',2015,3,'',NULL,'dca:notifyTemplate:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2529,'query',2015,4,'',NULL,'dca:notifyTemplate:query','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2530,'add',2101,1,'',NULL,'dca:market:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2531,'edit',2101,2,'',NULL,'dca:market:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2532,'remove',2101,3,'',NULL,'dca:market:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2533,'export',2101,4,'',NULL,'dca:market:export','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2534,'collect',2101,5,'',NULL,'dca:market:collect','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2535,'log',2101,6,'',NULL,'dca:market:log','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2536,'api',2101,7,'',NULL,'dca:market:api','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2537,'add',2101,8,'',NULL,'dca:market:api:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2538,'edit',2101,9,'',NULL,'dca:market:api:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2539,'remove',2101,10,'',NULL,'dca:market:api:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2540,'test',2101,11,'',NULL,'dca:market:api:test','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2541,'task',2101,12,'',NULL,'dca:market:task','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2542,'add',2101,13,'',NULL,'dca:market:task:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2543,'edit',2101,14,'',NULL,'dca:market:task:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2544,'remove',2101,15,'',NULL,'dca:market:task:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2545,'list',2101,16,'',NULL,'dca:tradeSourceBinding:list','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2546,'add',2101,17,'',NULL,'dca:tradeSourceBinding:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2547,'edit',2101,18,'',NULL,'dca:tradeSourceBinding:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2548,'remove',2101,19,'',NULL,'dca:tradeSourceBinding:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2549,'add',2102,1,'',NULL,'dca:aiModel:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2550,'edit',2102,2,'',NULL,'dca:aiModel:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2551,'remove',2102,3,'',NULL,'dca:aiModel:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2552,'export',2102,4,'',NULL,'dca:aiModel:export','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2553,'query',2102,5,'',NULL,'dca:aiModel:query','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2554,'use',2102,6,'',NULL,'dca:aiModel:use','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2555,'add',2103,1,'',NULL,'dca:template:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2556,'edit',2103,2,'',NULL,'dca:template:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2557,'remove',2103,3,'',NULL,'dca:template:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2558,'query',2103,4,'',NULL,'dca:template:query','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2559,'add',2202,1,'',NULL,'dca:card:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2560,'edit',2202,2,'',NULL,'dca:card:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2561,'remove',2202,3,'',NULL,'dca:card:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2562,'export',2202,4,'',NULL,'dca:card:export','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2563,'generate',2202,5,'',NULL,'dca:card:generate','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2564,'query',2202,6,'',NULL,'dca:card:query','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2565,'add',2203,1,'',NULL,'dca:notify:add','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2566,'edit',2203,2,'',NULL,'dca:notify:edit','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2567,'remove',2203,3,'',NULL,'dca:notify:remove','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2568,'export',2203,4,'',NULL,'dca:notify:export','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2569,'send',2203,5,'',NULL,'dca:notify:send','F','0','#','0','0','admin','2026-09-02 00:00:00'),
  (2570,'list',2204,1,'',NULL,'dca:dashboard:list','F','0','#','0','0','admin','2026-09-02 00:00:00');

-- ---------- role 1 gets every menu ----------
DELETE FROM sys_role_menu;
INSERT INTO sys_role_menu (role_id,menu_id) SELECT 1, menu_id FROM sys_menu;
-- observer role: directories and list pages only, no buttons
INSERT INTO sys_role_menu (role_id,menu_id) SELECT 2, menu_id FROM sys_menu WHERE menu_type <> 'F';

-- ---------- framework params ----------
DELETE FROM sys_config;
INSERT INTO sys_config (config_id,config_name,config_key,config_value,config_type,create_by,create_time,remark) VALUES
  (1,'用户管理-账号初始密码','sys.user.initPassword','__INIT_PWD__','Y','admin','2026-09-02 00:00:00','新建用户的初始口令'),
  (2,'账号自助-验证码开关','sys.account.captchaEnabled','true','Y','admin','2026-09-02 00:00:00','登录是否启用验证码'),
  (3,'账号自助-是否开启用户注册','sys.account.registerUser','false','Y','admin','2026-09-02 00:00:00','关闭公开注册'),
  (4,'用户登录-黑名单列表','sys.login.blackIPList','','Y','admin','2026-09-02 00:00:00','登录 IP 黑名单'),
  (5,'用户管理-初始密码修改','sys.account.initPasswordModify','1','Y','admin','2026-09-02 00:00:00','1=提示修改初始口令'),
  (6,'用户管理-密码有效期','sys.account.passwordValidateDays','0','Y','admin','2026-09-02 00:00:00','0=不限制');

-- ---------- dictionaries used by the console ----------
DELETE FROM sys_dict_type;
INSERT INTO sys_dict_type (dict_id,dict_name,dict_type,status,create_by,create_time) VALUES
  (1,'任务分组','sys_job_group','0','admin','2026-09-02 00:00:00'),
  (2,'操作类型','sys_oper_type','0','admin','2026-09-02 00:00:00');
DELETE FROM sys_dict_data;
INSERT INTO sys_dict_data (dict_code,dict_sort,dict_label,dict_value,dict_type,status,create_by,create_time) VALUES
  (1,1,'默认','DEFAULT','sys_job_group','0','admin','2026-09-02 00:00:00'),
  (2,2,'系统','SYSTEM','sys_job_group','0','admin','2026-09-02 00:00:00'),
  (3,0,'其他','0','sys_oper_type','0','admin','2026-09-02 00:00:00'),
  (4,1,'新增','1','sys_oper_type','0','admin','2026-09-02 00:00:00'),
  (5,2,'修改','2','sys_oper_type','0','admin','2026-09-02 00:00:00'),
  (6,3,'删除','3','sys_oper_type','0','admin','2026-09-02 00:00:00'),
  (7,4,'授权','4','sys_oper_type','0','admin','2026-09-02 00:00:00'),
  (8,5,'导出','5','sys_oper_type','0','admin','2026-09-02 00:00:00'),
  (9,6,'导入','6','sys_oper_type','0','admin','2026-09-02 00:00:00'),
  (10,7,'强退','7','sys_oper_type','0','admin','2026-09-02 00:00:00'),
  (11,8,'生成代码','8','sys_oper_type','0','admin','2026-09-02 00:00:00'),
  (12,9,'清空数据','9','sys_oper_type','0','admin','2026-09-02 00:00:00');

-- ---------- trade runtime ----------
-- runtime_flags_json stays '{}': the backend deep-merges buildDefaultRuntimeFlags()
-- over whatever is stored, so an empty object yields the full EVENT_GATED policy.
DELETE FROM trade_runtime_config;
INSERT INTO trade_runtime_config (id,singleton_key,default_mode,live_enabled,max_position_ratio,max_daily_loss,max_consecutive_failures,allowed_symbols_json,allowed_exchanges_json,require_account_binding,live_order_requires_healthy_account,runtime_flags_json,notify_defaults_json,event_retention_days,replay_retention_days,deliberation_enabled,deliberation_max_rounds,deliberation_fail_open,route_max_concurrency,route_scheduler_mode) VALUES
  (1,1,'PAPER',0,0.40,-500.00,3,'["BTCUSDT","ETHUSDT","SOLUSDT"]','["binance","okx"]',1,1,'{}','{}',30,30,0,0,1,1,'SERIAL');

-- ---------- LLM model ----------
-- DeepSeek is the default: OpenAI and Anthropic both geo-block Hong Kong egress
-- (api.openai.com answers unsupported_country_region_territory from this host).
DELETE FROM ai_model_config;
INSERT INTO ai_model_config (id,model_name,model_code,model_key,provider,api_endpoint,api_key_encrypted,is_enabled,is_default,priority,timeout_seconds,retry_times,max_tokens,temperature,top_p,daily_limit,description,create_by,create_time) VALUES
  (6,'deepseek-reasoner','deepseek-reasoner','deepseek-reasoner','deepseek','https://api.deepseek.com/v1','__DEEPSEEK_API_KEY__',1,1,1,60,2,4096,0.3,0.9,500,'香港出口可直连；OpenAI/Anthropic 从本机返回 403','admin','2026-09-02 00:00:00');

-- ---------- agent profiles ----------
DELETE FROM trade_agent_profile;
INSERT INTO trade_agent_profile (id,agent_code,agent_name,agent_type,enabled,llm_enabled,default_model_id,speak_order,max_retries,timeout_seconds,dialogue_enabled,max_dialogue_rounds,runtime_options_json,tool_policy_json,created_at,updated_at) VALUES
  (1,'market_agent','行情 Agent','market',1,1,6,1,2,60,0,0,'{}','{}','2026-09-02 00:00:00','2026-09-02 00:00:00'),
  (2,'news_agent','新闻 Agent','news',1,1,6,2,2,60,0,0,'{}','{}','2026-09-02 00:00:00','2026-09-02 00:00:00'),
  (3,'onchain_agent','链上 Agent','onchain',1,1,6,3,2,60,0,0,'{}','{}','2026-09-02 00:00:00','2026-09-02 00:00:00'),
  (4,'social_agent','社交 Agent','social',1,1,6,4,2,60,0,0,'{}','{}','2026-09-02 00:00:00','2026-09-02 00:00:00'),
  (5,'supervisor_agent','主管 Agent','supervisor',1,1,6,9,2,60,0,0,'{}','{}','2026-09-02 00:00:00','2026-09-02 00:00:00');

-- ---------- auxiliary feed sources ----------
-- IDs 102/103/104 are the news/onchain/social endpoints that
-- deploy/prod/README.md tells you to point at the feed-adapter.
DELETE FROM market_api_config;
INSERT INTO market_api_config (id,config_name,data_category,api_name,api_url,http_method,transport_type,vendor_code,market_scope,enabled,priority,timeout,retry_count,retry_interval,version_no,use_proxy,create_by,create_time,remark) VALUES
  (102,'新闻资讯','news','新闻资讯','http://127.0.0.1:18080/runtime/news','GET','http','feed-adapter','futures',1,2,10,2,5,1,0,'admin','2026-09-02 00:00:00','feed-adapter 聚合源'),
  (103,'链上资金','onchain','链上资金','http://127.0.0.1:18080/runtime/onchain','GET','http','feed-adapter','futures',1,3,10,2,5,1,0,'admin','2026-09-02 00:00:00','feed-adapter 聚合源'),
  (104,'社交舆情','social','社交舆情','http://127.0.0.1:18080/runtime/social','GET','http','feed-adapter','futures',1,4,10,2,5,1,0,'admin','2026-09-02 00:00:00','feed-adapter 聚合源');

-- ---------- price source (Binance USD-M futures websocket) ----------
-- selectFirstEnabledApi("PRICE") drives bootstrap.marketApiConfig; without a
-- PRICE row the worker reports market_source_abnormal and market_data stays empty.
-- The ws_* values match BinanceWebSocketProfile's built-in defaults.
INSERT INTO market_api_config (id,config_name,data_category,data_sub_type,api_name,api_url,http_method,transport_type,vendor_code,market_scope,ws_base_url,ws_path,ws_stream_name_template,ws_combined_enabled,ws_symbol_lowercase,ws_ping_interval_seconds,ws_pong_timeout_seconds,ws_connection_ttl_hours,ws_max_streams_per_connection,ws_control_messages_per_second,doc_reference_url,enabled,priority,timeout,retry_count,retry_interval,version_no,use_proxy,apply_symbols,create_by,create_time,remark) VALUES
  (101,'Binance 合约行情','PRICE','ticker','binance-futures-ticker','https://fapi.binance.com/fapi/v1/ticker/24hr','GET','ws','binance','futures','wss://fstream.binance.com','/ws','{symbol_lower}@ticker',0,1,20,60,24,1024,5,'https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams',1,1,10,2,5,1,0,'["BTCUSDT","ETHUSDT","SOLUSDT"]','admin','2026-09-02 00:00:00','香港出口实测可直连 fapi/fstream');

-- ---------- collection config ----------
DELETE FROM market_data_config;
INSERT INTO market_data_config (id,config_name,symbol,data_sources,collect_interval,collect_kline,kline_periods,collect_fear_greed,collect_onchain,enabled,create_by,create_time,remark) VALUES
  (1,'BTCUSDT 行情采集','BTCUSDT','["binance"]',60,1,'["15m","1h","4h"]',0,0,1,'admin','2026-09-02 00:00:00',NULL),
  (2,'ETHUSDT 行情采集','ETHUSDT','["binance"]',60,1,'["15m","1h","4h"]',0,0,1,'admin','2026-09-02 00:00:00',NULL),
  (3,'SOLUSDT 行情采集','SOLUSDT','["binance"]',60,1,'["15m","1h","4h"]',0,0,1,'admin','2026-09-02 00:00:00',NULL);

-- ---------- notification plumbing ----------
DELETE FROM notify_channel;
INSERT INTO notify_channel (id,user_id,channel_type,channel_name,is_enabled,create_by,create_time,remark) VALUES (1,1,'email','通用渠道',0,'admin','2026-09-02 00:00:00','填入 SMTP 后再启用');
DELETE FROM notify_template;
INSERT INTO notify_template (id,name,code,title_template,content_template,variables,is_active,is_default,create_by,create_time) VALUES
  (1,'运行时风险通知','notify.runtime.risk.v1','[{severity}] {event_type} {symbol}','trace={trace_id} {summary}','["severity","event_type","symbol","trace_id","summary"]',1,1,'admin','2026-09-02 00:00:00');
DELETE FROM trade_notify_policy;
INSERT INTO trade_notify_policy (id,policy_name,policy_scope,strategy_id,event_scope_json,severity_scope_json,mode_scope_json,throttle_seconds,template_code,enabled,created_at,updated_at) VALUES
  (1,'runtime-critical-events','GLOBAL',NULL,'["risk_guard_hit","source_health","execution_failed"]','["WARN","ERROR"]','["shadow","live"]',60,'notify.runtime.risk.v1',1,'2026-09-02 00:00:00','2026-09-02 00:00:00');
DELETE FROM trade_notify_policy_channel;
INSERT INTO trade_notify_policy_channel (id,policy_id,channel_id,channel_order,enabled) VALUES (1,1,1,1,1);

