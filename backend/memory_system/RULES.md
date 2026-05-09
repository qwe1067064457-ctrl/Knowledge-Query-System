# Memory System Rules

本目录承载记忆系统模块，以及当前第一版的记忆写入规则说明。

## 三类记忆

- `core`
  - 长期、稳定、值得跨会话保留的偏好与规则
  - 作用域为 `user_global` 或 `user_group`
- `daily_log`
  - 阶段性结果、会话摘要、近期推进记录
  - 作用域为 `user_group`
- `domain_case`
  - 组共享的案例、判例、病例、可复用结论
  - 作用域为 `group_shared`

## 写入时机

- `daily_log`
  - checkpoint 或 compaction flush 时默认写入
  - 是否启用由 `memory_policy.daily_log.checkpoint_enabled` 控制

- `core`
  - 只从用户消息中提取“显式长期信号”
  - 触发词来自 `memory_policy.core.explicit_markers`
  - `user_global / user_group` 由 `memory_policy.core.group_scope_keywords` 判断

- `domain_case`
  - 只在 checkpoint 时尝试提取
  - 必须同时满足：
    - 完成态标记：`memory_policy.domain_case.completion_markers`
    - 结构化标记：`memory_policy.domain_case.structural_markers` 或 `case_markers`

## 作用域语义

- `user_global`
  - 同一用户跨所有组都成立的长期记忆
- `user_group`
  - 同一用户仅在当前组成立的长期记忆
- `group_shared`
  - 当前组内共享的案例、经验、规范

## 规则来源

两层来源，后者覆盖前者：

1. 默认规则
   - `backend/memory_system/policy.default.json`
2. 组元数据
   - `backend/storage/groups/{group_id}/meta.json`
   - 使用其中的 `memory_policy` 字段

group 元数据不存在时，完全回退到默认规则。
group 元数据缺字段时，按默认规则补齐。

## group 元数据字段

```json
{
  "memory_policy": {
    "enabled_memory_types": ["core", "daily_log", "domain_case"],
    "core": {
      "explicit_markers": ["以后", "默认"],
      "group_scope_keywords": ["法律", "法条"],
      "min_candidate_length": 6,
      "max_candidate_length": 120
    },
    "daily_log": {
      "checkpoint_enabled": true
    },
    "domain_case": {
      "completion_markers": ["已完成", "结论"],
      "structural_markers": ["问题", "分析", "结论"],
      "case_markers": ["案例", "判例", "病例"]
    }
  }
}
```

## 当前第一版限制

- 不支持 user 级规则覆盖
- 不提供管理 UI
- 测试补充延后
- 规则判断仍然是启发式，不是 LLM 分类器
