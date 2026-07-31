package com.ruoyi.dca.service.impl;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import com.ruoyi.dca.domain.PromptTemplate;
import com.ruoyi.dca.mapper.PromptTemplateMapper;
import com.ruoyi.dca.service.IPromptTemplateService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 提示词模板服务实现
 */
@Service
public class PromptTemplateServiceImpl implements IPromptTemplateService {

    private static final Logger log = LoggerFactory.getLogger(PromptTemplateServiceImpl.class);

    private static final Pattern VARIABLE_PATTERN = Pattern.compile("\\{([^}]+)\\}");

    @Autowired
    private PromptTemplateMapper promptTemplateMapper;

    @Override
    public PromptTemplate selectPromptTemplateById(Long id) {
        return promptTemplateMapper.selectPromptTemplateById(id);
    }

    @Override
    public List<PromptTemplate> selectPromptTemplateList(PromptTemplate promptTemplate) {
        return promptTemplateMapper.selectPromptTemplateList(promptTemplate);
    }

    @Override
    public int insertPromptTemplate(PromptTemplate promptTemplate) {
        return promptTemplateMapper.insertPromptTemplate(promptTemplate);
    }

    @Override
    public int updatePromptTemplate(PromptTemplate promptTemplate) {
        return promptTemplateMapper.updatePromptTemplate(promptTemplate);
    }

    @Override
    public int deletePromptTemplateByIds(Long[] ids) {
        return promptTemplateMapper.deletePromptTemplateByIds(ids);
    }

    @Override
    public PromptTemplate selectTemplateByCode(String code) {
        return promptTemplateMapper.selectPromptTemplateByCode(code);
    }

    @Override
    public String renderTemplate(String templateCode, Map<String, Object> variables) {
        PromptTemplate template = selectTemplateByCode(templateCode);
        if (template == null) {
            log.warn("Template not found: {}", templateCode);
            return "";
        }

        String content = template.getContent();
        if (content == null) {
            return "";
        }

        Map<String, Object> safeVariables = variables != null ? variables : Collections.emptyMap();

        try {
            Matcher matcher = VARIABLE_PATTERN.matcher(content);
            StringBuffer result = new StringBuffer();

            while (matcher.find()) {
                String varName = matcher.group(1);
                Object value = safeVariables.get(varName);
                String replacement = value != null ? value.toString() : "";
                matcher.appendReplacement(result, Matcher.quoteReplacement(replacement));
            }
            matcher.appendTail(result);

            return result.toString();
        } catch (Exception e) {
            log.error("Failed to render template: {}", templateCode, e);
            return "";
        }
    }

    @Override
    public int createNewVersion(Long id) {
        PromptTemplate oldTemplate = selectPromptTemplateById(id);
        if (oldTemplate == null) {
            return 0;
        }

        PromptTemplate newTemplate = new PromptTemplate();
        newTemplate.setName(oldTemplate.getName());
        newTemplate.setCode(oldTemplate.getCode());
        newTemplate.setContent(oldTemplate.getContent());
        newTemplate.setVariables(oldTemplate.getVariables());
        newTemplate.setVersion(oldTemplate.getVersion() + 1);
        newTemplate.setIsActive(0);

        return insertPromptTemplate(newTemplate);
    }

    @Override
    public List<PromptTemplate> selectTemplateVersions(String code) {
        return promptTemplateMapper.selectActiveTemplatesByCode(code);
    }

    @Override
    public int updateTemplateStatus(Long id, Integer isActive) {
        PromptTemplate template = selectPromptTemplateById(id);
        if (template != null) {
            template.setIsActive(isActive);
            return updatePromptTemplate(template);
        }
        return 0;
    }
}
