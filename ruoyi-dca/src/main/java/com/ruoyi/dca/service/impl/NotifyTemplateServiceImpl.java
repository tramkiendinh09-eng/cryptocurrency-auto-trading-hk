package com.ruoyi.dca.service.impl;

import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.NotifyTemplate;
import com.ruoyi.dca.mapper.NotifyTemplateMapper;
import com.ruoyi.dca.service.INotifyTemplateService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class NotifyTemplateServiceImpl implements INotifyTemplateService {

    @Autowired
    private NotifyTemplateMapper notifyTemplateMapper;

    @Override
    public NotifyTemplate selectNotifyTemplateById(Long id) {
        return notifyTemplateMapper.selectNotifyTemplateById(id);
    }

    @Override
    public List<NotifyTemplate> selectNotifyTemplateList(NotifyTemplate notifyTemplate) {
        return notifyTemplateMapper.selectNotifyTemplateList(notifyTemplate);
    }

    @Override
    public NotifyTemplate selectNotifyTemplateByCode(String code) {
        if (code == null || code.isBlank()) {
            return null;
        }
        return notifyTemplateMapper.selectNotifyTemplateByCode(code.trim());
    }

    @Override
    public int insertNotifyTemplate(NotifyTemplate notifyTemplate) {
        normalizeAndValidate(notifyTemplate, false);
        return notifyTemplateMapper.insertNotifyTemplate(notifyTemplate);
    }

    @Override
    public int updateNotifyTemplate(NotifyTemplate notifyTemplate) {
        if (notifyTemplate == null || notifyTemplate.getId() == null) {
            throw new ServiceException("Notify template id is required");
        }
        if (notifyTemplateMapper.selectNotifyTemplateById(notifyTemplate.getId()) == null) {
            throw new ServiceException("Notify template does not exist");
        }
        normalizeAndValidate(notifyTemplate, true);
        return notifyTemplateMapper.updateNotifyTemplate(notifyTemplate);
    }

    @Override
    public int deleteNotifyTemplateByIds(Long[] ids) {
        if (ids == null || ids.length == 0) {
            return 0;
        }
        return notifyTemplateMapper.deleteNotifyTemplateByIds(ids);
    }

    private void normalizeAndValidate(NotifyTemplate notifyTemplate, boolean update) {
        if (notifyTemplate == null) {
            throw new ServiceException("Notify template payload is required");
        }
        notifyTemplate.setName(trim(notifyTemplate.getName()));
        notifyTemplate.setCode(trim(notifyTemplate.getCode()));
        notifyTemplate.setTitleTemplate(trim(notifyTemplate.getTitleTemplate()));
        notifyTemplate.setContentTemplate(trim(notifyTemplate.getContentTemplate()));
        notifyTemplate.setVariables(trim(notifyTemplate.getVariables()));
        notifyTemplate.setRemark(trim(notifyTemplate.getRemark()));
        if (notifyTemplate.getIsActive() == null) {
            notifyTemplate.setIsActive(1);
        }
        if (notifyTemplate.getIsDefault() == null) {
            notifyTemplate.setIsDefault(0);
        }

        if (notifyTemplate.getName().isEmpty()) {
            throw new ServiceException("Notify template name is required");
        }
        if (notifyTemplate.getCode().isEmpty()) {
            throw new ServiceException("Notify template code is required");
        }
        if (notifyTemplate.getTitleTemplate().isEmpty()) {
            throw new ServiceException("Notify template title is required");
        }
        if (notifyTemplate.getContentTemplate().isEmpty()) {
            throw new ServiceException("Notify template content is required");
        }

        NotifyTemplate existing = notifyTemplateMapper.selectNotifyTemplateByCode(notifyTemplate.getCode());
        if (existing != null && (!update || !existing.getId().equals(notifyTemplate.getId()))) {
            throw new ServiceException("Notify template code already exists");
        }
    }

    private String trim(String value) {
        return value == null ? "" : value.trim();
    }
}
