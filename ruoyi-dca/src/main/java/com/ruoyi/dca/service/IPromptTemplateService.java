package com.ruoyi.dca.service;

import com.ruoyi.dca.domain.PromptTemplate;
import java.util.List;
import java.util.Map;

/**
 * 提示词模板服务接口
 */
public interface IPromptTemplateService {

    PromptTemplate selectPromptTemplateById(Long id);

    List<PromptTemplate> selectPromptTemplateList(PromptTemplate promptTemplate);

    int insertPromptTemplate(PromptTemplate promptTemplate);

    int updatePromptTemplate(PromptTemplate promptTemplate);

    int deletePromptTemplateByIds(Long[] ids);

    PromptTemplate selectTemplateByCode(String code);

    String renderTemplate(String templateCode, Map<String, Object> variables);

    int createNewVersion(Long id);

    List<PromptTemplate> selectTemplateVersions(String code);

    int updateTemplateStatus(Long id, Integer isActive);
}
