# Understanding 模式与模型接管说明 V1

## 模式

### rule_only

- 适用于：
  - baseline
  - hard gate
  - 冷启动
  - 回归锚点

### rule_plus_model

- 近期主路线
- rule 提供：
  - coarse classification
  - coarse recognition
  - safety / guardrail
- model 提供：
  - 中层语义收敛
  - ambiguity 判断
  - task 柔性收敛

### model_first_rule_guard

- 远期目标
- model 先理解
- rule 只保留：
  - unsupported / safety
  - coarse hard gate
  - regression guard

## 建议的模型接管点

- `clarify_candidate` 最终裁决
- `ask_source / challenge / soft_doubt` 的柔性收敛
- `response_structure_hint` 与 `staged` 的区分
- `task` 是否需要进一步拆分

## 不建议立即交给模型的

- `unsupported / safety`
- 高风险边界拦截
- 极高精度 hard gate
status: active-working
related_current_doc: notes/intent/architecture/intent_rule_lite_strategy.md
scope: rule model handoff modes
