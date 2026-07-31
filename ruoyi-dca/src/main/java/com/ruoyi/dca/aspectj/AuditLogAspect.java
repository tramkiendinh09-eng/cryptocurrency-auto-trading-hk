package com.ruoyi.dca.aspectj;

import java.lang.reflect.Method;
import java.util.Date;
import java.util.Map;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.AfterReturning;
import org.aspectj.lang.annotation.AfterThrowing;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.core.domain.model.LoginUser;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.common.utils.ServletUtils;
import com.ruoyi.common.utils.StringUtils;
import com.ruoyi.common.utils.ip.IpUtils;
import jakarta.servlet.http.HttpServletRequest;
import com.ruoyi.dca.service.IAuditOperationLogService;

/**
 * 审计日志切面
 * 自动记录关键操作的审计日志
 *
 * @author ruoyi
 */
@Aspect
@Component
public class AuditLogAspect
{
    private static final Logger log = LoggerFactory.getLogger(AuditLogAspect.class);

    @Autowired
    private IAuditOperationLogService auditOperationLogService;

    private ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 配置织入点
     */
    @Pointcut("@annotation(com.ruoyi.dca.annotation.AuditLog)")
    public void auditLogPointCut()
    {
    }

    /**
     * 前置通知：用于记录操作开始时间
     */
    // @Before("auditLogPointCut()")
    // public void doBefore(JoinPoint joinPoint)
    // {
    //     // 可以在这里记录开始时间
    // }

    /**
     * 操作成功返回结果
     */
    @AfterReturning(pointcut = "auditLogPointCut()", returning = "jsonResult")
    public void doAfterReturning(JoinPoint joinPoint, Object jsonResult)
    {
        handleLog(joinPoint, null, jsonResult);
    }

    /**
     * 操作抛出异常
     */
    @AfterThrowing(pointcut = "auditLogPointCut()", throwing = "e")
    public void doAfterThrowing(JoinPoint joinPoint, Exception e)
    {
        handleLog(joinPoint, e, null);
    }

    /**
     * 处理审计日志
     */
    private void handleLog(JoinPoint joinPoint, Exception e, Object jsonResult)
    {
        try
        {
            // 获取注解
            com.ruoyi.dca.annotation.AuditLog auditLog = getAnnotationLog(joinPoint);
            if (auditLog == null)
            {
                return;
            }

            // 获取当前用户
            Long userId = null;
            String username = "";
            try
            {
                LoginUser loginUser = SecurityUtils.getLoginUser();
                if (loginUser != null)
                {
                    userId = loginUser.getUserId();
                    username = loginUser.getUsername();
                }
            }
            catch (Exception ex)
            {
                // 未登录或获取用户信息失败，使用默认值
                log.warn("获取当前用户信息失败: {}", ex.getMessage());
            }

            // 获取请求信息
            HttpServletRequest request = ((ServletRequestAttributes) RequestContextHolder.getRequestAttributes()).getRequest();
            String requestMethod = request.getMethod();
            String requestUrl = request.getRequestURI();
            String requestIp = IpUtils.getIpAddr(request);

            // 获取请求参数
            String requestParams = getRequestParams(joinPoint, auditLog);

            // 获取操作描述
            String description = auditLog.description();
            if (StringUtils.isEmpty(description))
            {
                description = getControllerMethodDescription(joinPoint);
            }

            // 获取模块和操作类型
            String module = auditLog.module();
            String operation = auditLog.operation();

            // 记录操作时间
            long executionTime = 0L;
            // TODO: 可以通过ThreadLocal记录开始时间，计算执行时间

            // 记录返回结果（如果配置了需要记录）
            String responseData = null;
            if (auditLog.saveResponseData())
            {
                responseData = toJson(jsonResult);
            }

            // 判断操作状态
            Integer status = 1; // 默认成功
            String errorMsg = null;

            if (e != null)
            {
                status = 0; // 失败
                errorMsg = StringUtils.substring(e.getMessage(), 0, 2000);
            }

            // 记录审计日志
            auditOperationLogService.recordOperation(
                    userId, username, module, operation, description,
                    requestMethod, requestUrl, requestIp, requestParams,
                    responseData, status, errorMsg, executionTime);
        }
        catch (Exception exp)
        {
            // 记录日志失败不应影响业务流程
            log.error("==前置通知异常==", exp);
        }
    }

    /**
     * 获取注解
     */
    private com.ruoyi.dca.annotation.AuditLog getAnnotationLog(JoinPoint joinPoint)
    {
        try
        {
            Method method = getMethod(joinPoint);
            if (method == null)
            {
                return null;
            }
            return method.getAnnotation(com.ruoyi.dca.annotation.AuditLog.class);
        }
        catch (Exception e)
        {
            log.error("获取注解失败", e);
            return null;
        }
    }

    /**
     * 获取方法
     */
    private Method getMethod(JoinPoint joinPoint)
    {
        try
        {
            String methodName = joinPoint.getSignature().getName();
            Class<?> targetClass = joinPoint.getTarget().getClass();

            // 处理代理类，获取实际的目标类
            if (targetClass.getName().contains("$$EnhancerBySpringCGLIB$$")) {
                targetClass = targetClass.getSuperclass();
            }

            // 获取方法参数类型
            Class<?>[] parameterTypes = new Class[joinPoint.getArgs().length];
            Object[] args = joinPoint.getArgs();
            for (int i = 0; i < args.length; i++)
            {
                if (args[i] != null)
                {
                    parameterTypes[i] = args[i].getClass();
                }
                else
                {
                    // 参数为null时，使用Object类型
                    parameterTypes[i] = Object.class;
                }
            }

            // 尝试直接获取方法
            try {
                return targetClass.getMethod(methodName, parameterTypes);
            } catch (NoSuchMethodException e) {
                // 如果直接获取失败，尝试遍历所有方法进行匹配
                Method[] methods = targetClass.getMethods();
                for (Method method : methods) {
                    if (method.getName().equals(methodName)) {
                        Class<?>[] methodParams = method.getParameterTypes();
                        if (methodParams.length == parameterTypes.length) {
                            boolean match = true;
                            for (int i = 0; i < methodParams.length; i++) {
                                if (parameterTypes[i] != Object.class && !methodParams[i].isAssignableFrom(parameterTypes[i])) {
                                    match = false;
                                    break;
                                }
                            }
                            if (match) {
                                return method;
                            }
                        }
                    }
                }
                throw e;
            }
        }
        catch (Exception e)
        {
            log.error("获取方法失败", e);
            return null;
        }
    }

    /**
     * 获取请求参数
     */
    private String getRequestParams(JoinPoint joinPoint, com.ruoyi.dca.annotation.AuditLog auditLog)
    {
        try
        {
            if (auditLog.excludeParams())
            {
                // 排除敏感参数
                Map<String, String[]> params = ServletUtils.getRequest().getParameterMap();
                return objectMapper.writeValueAsString(filterParams(params));
            }
            else
            {
                // 记录所有参数
                return objectMapper.writeValueAsString(joinPoint.getArgs());
            }
        }
        catch (Exception e)
        {
            log.error("获取请求参数失败", e);
            return null;
        }
    }

    /**
     * 过滤敏感参数
     */
    private Map<String, String[]> filterParams(Map<String, String[]> params)
    {
        Map<String, String[]> filteredParams = new java.util.HashMap<>();
        String[] sensitiveFields = {"password", "secret", "token", "key"};

        for (Map.Entry<String, String[]> entry : params.entrySet())
        {
            String key = entry.getKey().toLowerCase();
            boolean isSensitive = false;
            for (String field : sensitiveFields)
            {
                if (key.contains(field))
                {
                    isSensitive = true;
                    break;
                }
            }

            if (isSensitive)
            {
                filteredParams.put(entry.getKey(), new String[]{"******"});
            }
            else
            {
                filteredParams.put(entry.getKey(), entry.getValue());
            }
        }

        return filteredParams;
    }

    /**
     * 转换为JSON
     */
    private String toJson(Object obj)
    {
        try
        {
            if (obj == null)
            {
                return null;
            }
            return objectMapper.writeValueAsString(obj);
        }
        catch (Exception e)
        {
            log.error("转换为JSON失败", e);
            return null;
        }
    }

    /**
     * 获取控制器方法描述
     */
    private String getControllerMethodDescription(JoinPoint joinPoint)
    {
        try
        {
            Method method = getMethod(joinPoint);
            if (method == null)
            {
                return "";
            }
            // 可以从方法注释或其他注解中获取描述
            return method.getName();
        }
        catch (Exception e)
        {
            log.error("获取方法描述失败", e);
            return "";
        }
    }
}
