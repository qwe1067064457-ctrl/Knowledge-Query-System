# Challenge And Review

## 当前定位

`challenge` 当前不是独立 route。

它属于：

- `qa route` 内部的争议点复审分支

打开条件通常是：

- `handling_mode = challenge`
- `enabled_powers` 中包含 `challenge_power`

## 边界

当前边界固定为：

- `ChallengePower = orchestration`
- `ReviewWorker = coarse adjudication`

这意味着：

### ChallengePower 负责

- 消费 `context binding` 结果
- 识别 challenge target
- 先检查 existing evidence
- coverage 不足时触发 targeted follow-up retrieval
- 汇总 `review status / review findings / answer constraints`

### ReviewWorker 负责

- `retrieval_quality_check(...)`
- `evidence_check(...)`
- `re_evaluate(...)`

也就是：

- 检索层粗质量检查
- coarse evidence sufficiency adjudication
- review 输出投影

## Challenge 正式主链

当前 challenge 主链可以压成：

`consume binding result -> identify targets -> existing evidence check -> follow-up retrieval(if needed) -> review re-evaluate -> answer constraints / review summary`

## 当前消费的 binding signals

challenge 当前优先消费：

- `binding_result.bound_targets`
- `binding_result.resolved_target_ids`
- `binding_result.relevant_set`

如果没有稳定 target：

- 不继续做 challenge adjudication
- 直接返回 `needs_clarification`

## 当前 adjudication 粒度

当前 `ReviewWorker` 仍保持 coarse-grained adjudication。

它主要区分：

- `supported`
- `related_only`
- `missing`

对应问题是：

- 当前 evidence 是否 grounded 到 target
- 只是相关，还是足够支撑
- 是否仍需更多 evidence

当前不做：

- claim decomposition
- support / contradiction / exception 细粒度模型裁判
- retrieval repair 全过程诊断回灌到 challenge

## Existing Evidence Reuse

当前 challenge enhancement 的高收益点在：

- evidence coverage
- existing evidence reuse quality

当前口径是：

- grounded overlap 或稳定文本对齐才视为可直接支撑
- `related_only` 不能直接视为 sufficient
- 如果只是相关，会继续走：
  - `related_only -> targeted retrieval`

## Follow-up Retrieval

当前 follow-up retrieval 是受控补检索，不是整轮重跑大检索。

核心规则：

- 只围绕 `needs_more_evidence_targets` 发生
- multi-target challenge 时按缺口 target 分开构 support query units
- 不把已覆盖 target 一起重新搜

## 当前稳定输出

当前 challenge / review 稳定投影到下游的信号包括：

- `binding_contract_used`
- `binding_fallback_type`
- `binding_reason`
- `used_existing_evidence`
- `retrieve_if_needed_needed`
- `retrieve_if_needed_reason`
- `matched_target_count`
- `review status`
- `answer_constraints`

## 后续增强优先级

如果后续继续增强，优先级固定为：

1. evidence coverage
2. existing evidence reuse quality
3. fine-grained claim adjudication
