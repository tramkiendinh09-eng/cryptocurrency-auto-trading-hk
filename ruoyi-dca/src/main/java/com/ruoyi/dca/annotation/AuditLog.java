package com.ruoyi.dca.annotation;

import java.lang.annotation.Documented;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 审计日志注解
 * 用于标注需要记录审计日志的方法
 *
 * @author ruoyi
 */
@Target({ java.lang.annotation.ElementType.METHOD })
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface AuditLog
{
    /**
     * 操作模块
     */
    String module() default "";

    /**
     * 操作类型
     */
    String operation() default "";

    /**
     * 操作描述
     */
    String description() default "";

    /**
     * 是否排除敏感参数（如password、token等）
     */
    boolean excludeParams() default true;

    /**
     * 是否保存返回结果
     */
    boolean saveResponseData() default false;
}
