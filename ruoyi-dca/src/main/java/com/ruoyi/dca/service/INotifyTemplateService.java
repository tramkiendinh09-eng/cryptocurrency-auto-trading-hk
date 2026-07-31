package com.ruoyi.dca.service;

import com.ruoyi.dca.domain.NotifyTemplate;

import java.util.List;

public interface INotifyTemplateService {
    NotifyTemplate selectNotifyTemplateById(Long id);

    List<NotifyTemplate> selectNotifyTemplateList(NotifyTemplate notifyTemplate);

    NotifyTemplate selectNotifyTemplateByCode(String code);

    int insertNotifyTemplate(NotifyTemplate notifyTemplate);

    int updateNotifyTemplate(NotifyTemplate notifyTemplate);

    int deleteNotifyTemplateByIds(Long[] ids);
}
