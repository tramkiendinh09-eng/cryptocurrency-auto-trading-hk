package com.ruoyi.dca.controller.decision;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.dca.domain.decision.AgentMessage;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.service.decision.IDecisionAuditService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 决策审计控制器
 * 提供决策运行记录的保存和查询等RESTful API接口
 *
 * @author ruoyi-dca
 */
@RestController
@RequestMapping("/dca/decision")
public class DecisionAuditController extends BaseController {

    @Autowired
    private IDecisionAuditService decisionAuditService;

    /**
     * 保存决策运行记录
     *
     * @param decisionRun 决策运行数据
     * @return 操作结果
     */
    @Anonymous
    @PostMapping("/audit")
    public AjaxResult audit(@RequestBody DecisionRun decisionRun) {
        decisionAuditService.saveDecisionRun(decisionRun);
        return success();
    }

    /**
     * 查询决策运行列表
     *
     * @param executionStatus 执行状态
     * @param orderStatus 订单状态
     * @return 决策运行列表
     */
    @Anonymous
    @GetMapping("/runs")
    public TableDataInfo listRuns(@RequestParam(required = false) String executionStatus,
                                  @RequestParam(required = false) String orderStatus) {
        startPage();
        return getDataTable(decisionAuditService.listDecisionRuns(executionStatus, orderStatus));
    }

    @Anonymous
    @GetMapping("/supervisor-history")
    public AjaxResult listRecentSupervisorHistory(@RequestParam String symbol,
                                                  @RequestParam(required = false) String mode,
                                                  @RequestParam(required = false) String excludeTraceId,
                                                  @RequestParam(required = false) Integer limit) {
        List<AgentMessage> rows = decisionAuditService.listRecentSupervisorDecisions(symbol, mode, excludeTraceId, limit);
        return success(rows);
    }
}
