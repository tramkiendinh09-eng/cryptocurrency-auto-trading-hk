package com.ruoyi.dca.mapper;

import com.ruoyi.dca.domain.PromptTemplate;
import java.util.List;

/**
 * 提示词模板Mapper接口
 */
public interface PromptTemplateMapper {

    PromptTemplate selectPromptTemplateById(Long id);

    List<PromptTemplate> selectPromptTemplateList(PromptTemplate promptTemplate);

    PromptTemplate selectPromptTemplateByCode(String code);

    List<PromptTemplate> selectPromptTemplatesByType(String type);

    int insertPromptTemplate(PromptTemplate promptTemplate);

    int updatePromptTemplate(PromptTemplate promptTemplate);

    int deletePromptTemplateById(Long id);

    int deletePromptTemplateByIds(Long[] ids);

    int incrementVersion(Long id);

    List<PromptTemplate> selectActiveTemplatesByCode(String code);
}
