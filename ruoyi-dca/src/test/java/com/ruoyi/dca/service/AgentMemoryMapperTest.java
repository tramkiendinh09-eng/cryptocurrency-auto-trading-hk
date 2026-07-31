package com.ruoyi.dca.service;

import com.ruoyi.dca.domain.memory.AgentMemory;
import com.ruoyi.dca.mapper.memory.AgentMemoryMapper;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.annotation.MapperScan;
import org.mybatis.spring.boot.test.autoconfigure.MybatisTest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.jdbc.Sql;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@MybatisTest
@ContextConfiguration(classes = AgentMemoryMapperTest.TestApplication.class)
@TestPropertySource(properties = "mybatis.mapper-locations=classpath*:mapper/dca/memory/*.xml")
@Sql(statements = {
    "drop table if exists agent_memory_usage",
    "drop table if exists agent_memory",
    "create table agent_memory (" +
        "id bigint auto_increment primary key," +
        "memory_key varchar(128)," +
        "agent_code varchar(64)," +
        "symbol varchar(32)," +
        "memory_type varchar(32)," +
        "market_regime varchar(64)," +
        "event_tags_json varchar(1024)," +
        "direction varchar(16)," +
        "action varchar(32)," +
        "lesson_text varchar(1024)," +
        "evidence_json varchar(1024)," +
        "outcome_json varchar(1024)," +
        "quality_score decimal(8,4)," +
        "confidence decimal(8,4)," +
        "usage_count integer default 0," +
        "win_count integer default 0," +
        "loss_count integer default 0," +
        "last_used_at timestamp null," +
        "source_trace_id varchar(64)," +
        "enabled integer," +
        "created_at timestamp default current_timestamp," +
        "updated_at timestamp default current_timestamp" +
    ")",
    "create table agent_memory_usage (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "symbol varchar(32)," +
        "memory_id bigint," +
        "agent_code varchar(64)," +
        "usage_context_json varchar(1024)," +
        "outcome_json varchar(1024)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "insert into agent_memory (memory_key, agent_code, symbol, memory_type, event_tags_json, lesson_text, quality_score, confidence, enabled) values " +
        "('m-1', 'news_agent', 'BTCUSDT', 'lesson', '[\"strong_news\",\"breakout\"]', 'match both', 0.9, 0.8, 1)," +
        "('m-2', 'news_agent', 'BTCUSDT', 'lesson', '[\"macro\"]', 'different tag', 0.8, 0.7, 1)," +
        "('m-3', 'onchain_agent', 'BTCUSDT', 'lesson', '[\"strong_news\"]', 'other agent', 0.7, 0.6, 1)"
})
class AgentMemoryMapperTest {

    @SpringBootApplication
    @MapperScan("com.ruoyi.dca.mapper.memory")
    static class TestApplication {
    }

    @Autowired
    private AgentMemoryMapper agentMemoryMapper;

    @Test
    void selectCandidateMemoriesRanksRequestedTagMatchesBeforeFallbackMemories() {
        List<AgentMemory> rows = agentMemoryMapper.selectCandidateMemories(
            "news_agent",
            "BTCUSDT",
            List.of("strong_news", "volume_spike"),
            10
        );

        assertThat(rows).hasSize(2);
        assertThat(rows.get(0).getMemoryKey()).isEqualTo("m-1");
        assertThat(rows.get(1).getMemoryKey()).isEqualTo("m-2");
    }
}
