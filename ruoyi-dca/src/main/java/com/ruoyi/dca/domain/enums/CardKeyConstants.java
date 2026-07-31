package com.ruoyi.dca.domain.enums;

/**
 * 卡密相关常量
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class CardKeyConstants {
    /**
     * 卡密状态
     */
    public static final class Status {
        public static final String UNUSED = "unused";       // 未使用
        public static final String ACTIVATED = "activated"; // 已激活
        public static final String EXPIRED = "expired";     // 已过期
        public static final String DISABLED = "disabled";   // 已禁用
    }

    /**
     * 卡密类型
     */
    public static final class Type {
        public static final String TIME = "time";           // 时间版
        public static final String PERMANENT = "permanent"; // 永久版
        public static final String COUNT = "count";         // 次数版
        public static final String TRIAL = "trial";         // 试用版
    }

    /**
     * 卡密等级
     */
    public static final class Level {
        public static final String BASIC = "basic";         // 基础版
        public static final String PRO = "pro";             // 专业版
        public static final String PREMIUM = "premium";     // 旗舰版
    }

    /**
     * 功能开关
     */
    public static final class Feature {
        // AI 功能
        public static final String AI_ENABLED = "ai_enabled";
        public static final String AI_MODEL_GPT4 = "ai_model_gpt4";
        public static final String AI_MODEL_GPT35 = "ai_model_gpt35";
        public static final String AI_MODEL_CLAUDE = "ai_model_claude";

        // 交易功能
        public static final String MULTI_CURRENCY = "multi_currency";       // 多币种
        public static final String AUTO_TRADING = "auto_trading";           // 自动交易
        public static final String ADVANCED_CHART = "advanced_chart";       // 高级图表
        public static final String TECHNICAL_INDICATORS = "technical_indicators"; // 技术指标

        // 通知功能
        public static final String TELEGRAM_NOTIFY = "telegram_notify";     // Telegram通知
        public static final String EMAIL_NOTIFY = "email_notify";           // 邮件通知
        public static final String SMS_NOTIFY = "sms_notify";               // 短信通知
        public static final String WEBHOOK_NOTIFY = "webhook_notify";       // Webhook通知

        // 高级功能
        public static final String BACKTESTING = "backtesting";             // 回测功能
        public static final String STRATEGY_MARKET = "strategy_market";     // 策略市场
        public static final String API_ACCESS = "api_access";               // API访问
        public static final String PRIORITY_SUPPORT = "priority_support";   // 优先支持

        // 数据功能
        public static final String REALTIME_DATA = "realtime_data";         // 实时数据
        public static final String HISTORICAL_DATA = "historical_data";     // 历史数据
        public static final String CUSTOM_TIMEFRAME = "custom_timeframe";   // 自定义时间周期
    }

    /**
     * 默认功能开关配置
     */
    public static final class DefaultFeatures {
        // 基础版默认功能
        public static final String BASIC = "{"
                + "\"ai_enabled\":true,"
                + "\"ai_model_gpt35\":true,"
                + "\"multi_currency\":false,"
                + "\"telegram_notify\":true,"
                + "\"email_notify\":false,"
                + "\"realtime_data\":true"
                + "}";

        // 专业版默认功能
        public static final String PRO = "{"
                + "\"ai_enabled\":true,"
                + "\"ai_model_gpt4\":true,"
                + "\"ai_model_gpt35\":true,"
                + "\"multi_currency\":true,"
                + "\"auto_trading\":true,"
                + "\"telegram_notify\":true,"
                + "\"email_notify\":true,"
                + "\"realtime_data\":true,"
                + "\"historical_data\":true,"
                + "\"technical_indicators\":true"
                + "}";

        // 旗舰版默认功能
        public static final String PREMIUM = "{"
                + "\"ai_enabled\":true,"
                + "\"ai_model_gpt4\":true,"
                + "\"ai_model_gpt35\":true,"
                + "\"ai_model_claude\":true,"
                + "\"multi_currency\":true,"
                + "\"auto_trading\":true,"
                + "\"advanced_chart\":true,"
                + "\"telegram_notify\":true,"
                + "\"email_notify\":true,"
                + "\"sms_notify\":true,"
                + "\"webhook_notify\":true,"
                + "\"backtesting\":true,"
                + "\"strategy_market\":true,"
                + "\"api_access\":true,"
                + "\"priority_support\":true,"
                + "\"realtime_data\":true,"
                + "\"historical_data\":true,"
                + "\"custom_timeframe\":true"
                + "}";
    }
}
