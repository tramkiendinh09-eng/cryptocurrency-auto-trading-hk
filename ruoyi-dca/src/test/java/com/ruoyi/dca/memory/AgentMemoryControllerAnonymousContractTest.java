package com.ruoyi.dca.memory;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.dca.controller.memory.AgentMemoryController;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * worker↔后端是免鉴权的内网协议（TRADE_RUNTIME_BEARER_TOKEN 不是 RuoYi 的 JWT，
 * 实测带上仍然 401）。本控制器的三个方法全部由 worker 调用，少标一个就整条路径失效。
 *
 * 实际发生过：add 是唯一没标 @Anonymous 的，于是长期记忆的写入从部署起从未成功，
 * agent_memory 表一行都没有。失败被 RuoYi「401 装在 HTTP 200 里」掩盖，worker 的
 * raise_for_status() 不抛，只留下一句笼统的 memory_store_create_failed。
 */
class AgentMemoryControllerAnonymousContractTest {

    @Test
    void everyWorkerFacingEndpointIsAnonymous() {
        for (String name : new String[] {"list", "recordUsage", "add"}) {
            Method method = findMethod(name);
            assertThat(method.getAnnotation(Anonymous.class))
                .as("%s 必须标 @Anonymous，否则 worker 调用会被拒而且只报 memory_store_create_failed", name)
                .isNotNull();
        }
    }

    /** disable 只在控制台用，不该对外免鉴权。 */
    @Test
    void consoleOnlyEndpointStaysAuthenticated() {
        assertThat(findMethod("disable").getAnnotation(Anonymous.class)).isNull();
    }

    private Method findMethod(String name) {
        for (Method method : AgentMemoryController.class.getDeclaredMethods()) {
            if (method.getName().equals(name)) {
                return method;
            }
        }
        throw new AssertionError("找不到方法 " + name);
    }
}
