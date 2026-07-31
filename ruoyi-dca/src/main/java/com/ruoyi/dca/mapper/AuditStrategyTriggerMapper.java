package com.ruoyi.dca.mapper;

import com.ruoyi.dca.domain.AuditStrategyTrigger;

import java.util.List;

/**
 * 旧 DCA 触发审计只读兼容 Mapper。
 *
 * <p>runtime 重构后仅保留历史查询与兼容清理入口，不再承担任何运行时写入职责。</p>
 *
 * @author ruoyi
 */
public interface AuditStrategyTriggerMapper {

    AuditStrategyTrigger selectAuditStrategyTriggerById(Long id);

    List<AuditStrategyTrigger> selectAuditStrategyTriggerList(AuditStrategyTrigger auditStrategyTrigger);

    int cleanExpiredLogs(Integer days);
}
