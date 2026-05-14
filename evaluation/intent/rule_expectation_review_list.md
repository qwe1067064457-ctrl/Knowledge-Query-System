# Rule Expectation Review List

## 1. 使用方式

这份清单是给人工快速 review 用的。

你只需要逐条判断：

- `expected` 是否同意
- 如不同意，改成正确的 `true / false`
- 如有必要，补一句更准确的理由

对应的结构化模板文件在：

- [rule_expectation_annotation_template.jsonl](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/rule_expectation_annotation_template.jsonl)

规则口径说明在：

- [rule_supervision.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/rule_supervision.md)

---

## 2. Review 清单

### A. `intent.qa.generic`

#### 1. `generic_001`

- `batch`: `standard_qa`
- `query`: `如果公司拖欠工资，我可以怎么处理？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: 通用问答谓语明显，属于普通QA，不依赖明确领域名词正则。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 2. `generic_002`

- `batch`: `chat_meta_boundary`
- `query`: `最近感觉事情越来越复杂。`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 表达情绪或感受，属于普通 chat，不是问答型请求。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:
- `备注`: 用户补充：属于普通 chat。

#### 3. `generic_003`

- `batch`: `standard_qa`
- `query`: `医保报销比例如何计算？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: 带有明确的求解问法“如何计算”，属于通用问答请求。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 4. `generic_004`

- `batch`: `standard_qa`
- `query`: `赔偿金额通常如何确定？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: 关键触发点是“如何确定”的通用问答谓语，应允许 generic QA 覆盖。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 5. `generic_005`

- `batch`: `meta`
- `query`: `有依据吗？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 这是 ask_source / meta 追问，不应计入 generic QA。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 6. `generic_006`

- `batch`: `standard_qa`
- `query`: `工伤认定一般怎么申请？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: “怎么申请”是典型通用问答谓语，应作为 generic QA 正例。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: “怎么申请”是明确的通用求解谓语，属于 generic QA 正例。

#### 7. `generic_007`

- `batch`: `standard_qa`
- `query`: `离职后社保怎么处理？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: “怎么处理”是 generic QA 核心问法，且不依赖特定领域硬编码。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: “怎么处理”是 generic QA 的核心触发表达，且 query 是自包含的普通问答。

#### 8. `generic_008`

- `batch`: `chat_meta_boundary`
- `query`: `最近总觉得事情不太顺。`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 是情绪表达，不是问答请求。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=false`
- `你的理由`: 这是情绪/状态表达，没有求知、求解或判断请求。

#### 9. `generic_009`

- `batch`: `standard_qa`
- `query`: `这种情况通常会有什么后果？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: “会有什么后果”属于 generic QA 高价值通用问法。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: “会有什么后果”是高价值通用问答模式，应计入 generic QA。

#### 10. `generic_010`

- `batch`: `meta`
- `query`: `你能处理哪些问题？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 这是 capability / system 范畴，不应算 generic QA。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=false`
- `你的理由`: 这是系统能力/范围询问，应归入 capability/system，不是 generic QA。

#### 11. `generic_011`

- `batch`: `standard_qa`
- `query`: `如果合同里没写违约金怎么办？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: “怎么办”是 generic QA 核心触发模式。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: “怎么办”是 generic QA 的稳定触发模式，且问题有明确对象。

#### 12. `generic_012`

- `batch`: `chat_meta_boundary`
- `query`: `我想先听你安慰我一下。`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 表达陪伴/安慰需求，不是问答意图。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=false`
- `你的理由`: 这是安慰/陪伴需求，不是问答型请求。

---

### B. `intent.qa.judgment`

#### 1. `judgment_001`

- `batch`: `fuzzy_qa`
- `query`: `这样算医疗事故吗？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: 典型判断型 QA，询问事实是否构成某类责任或定性。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:
- `备注`: 用户备注：这类 query 在真实对话中常常应有上文；但对当前规则监督目标而言，judgment 仍应命中。

#### 2. `judgment_002`

- `batch`: `meta`
- `query`: `你刚才为什么这么说？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 这是追问依据/来源，不是判断型 QA。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:
- `备注`: 用户备注：这类 query 在真实对话中通常应有上文；同时 follow_up 与 challenge 在表面语义上存在重叠，后续需单独澄清。

#### 3. `judgment_003`

- `batch`: `fuzzy_qa`
- `query`: `医院这么做合理吗？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: “合理吗”是典型判断型 QA 表达，询问行为是否成立或适当。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 4. `judgment_004`

- `batch`: `fuzzy_qa`
- `query`: `这样会被拘留吗？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: 询问某种事实是否会触发法律后果，属于判断型 QA。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 5. `judgment_005`

- `batch`: `standard_qa`
- `query`: `医疗过失责任的构成要件是什么？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 这是定义/要件型 QA，不是判断型 QA。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 6. `judgment_006`

- `batch`: `fuzzy_qa`
- `query`: `公司这样扣工资合法吗？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: “合法吗”是判断型 QA 的强模式。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: “合法吗”是在判断行为是否合法，属于 judgment QA 强模式。

#### 7. `judgment_007`

- `batch`: `fuzzy_qa`
- `query`: `这种情况会被认定为工伤吗？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: “会被认定为…吗”属于典型定性判断问法。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: “会被认定为工伤吗”是在判断某事实是否构成特定定性，属于 judgment QA。

#### 8. `judgment_008`

- `batch`: `standard_qa`
- `query`: `工伤认定的条件是什么？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 询问条件/定义，不是对具体事实作判断。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=false`
- `你的理由`: 这是条件/定义型问答，不是在判断具体事实是否成立。

#### 9. `judgment_009`

- `batch`: `fuzzy_qa`
- `query`: `物业这么做合理吗？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: “合理吗”依旧是判断型 QA，即使领域换成物业。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: “合理吗”是判断型 QA 表达，领域换成物业不改变规则语义。

#### 10. `judgment_010`

- `batch`: `standard_qa`
- `query`: `医疗事故的定义是什么？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 定义型 QA，不属于 judgment。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=false`
- `你的理由`: “定义是什么”是定义型 QA，不属于 judgment。

#### 11. `judgment_011`

- `batch`: `fuzzy_qa`
- `query`: `这种免责条款还有效吗？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: “还有效吗”是在判断法律效果是否成立。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: “还有效吗”是在判断法律效果是否仍然成立，属于 judgment QA。

#### 12. `judgment_012`

- `batch`: `meta`
- `query`: `你为什么这么判断？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 追问理由/依据，不是 judgment QA 本身。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=false`
- `你的理由`: 这是追问理由/依据，更接近 ask_source，不是判断型 QA。

---

### C. `challenge.soft_doubt`

#### 1. `soft_doubt_001`

- `batch`: `challenge`
- `query`: `这个说法是不是太绝对了？`
- `history`:
  - `assistant`: `这种情况一定要赔偿。`
- `建议 expected`: `true`
- `建议理由`: 轻质疑、求证式反驳，有上一轮回答支撑，应标为 soft_doubt。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 2. `soft_doubt_002`

- `batch`: `standard_qa`
- `query`: `这种规则是不是全国都适用？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 这是普通 QA 求知，不应因为“是不是”结构就标为 soft_doubt。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:
- `备注`: 用户提出疑问：普通 QA 也可能带 soft_doubt 语气。当前监督口径仍按 false 处理，避免把一般求知句误吸入 challenge 语义。

#### 3. `soft_doubt_003`

- `batch`: `challenge`
- `query`: `你确定没有例外情况吗？`
- `history`:
  - `assistant`: `这个规则在所有情况下都适用。`
- `建议 expected`: `true`
- `建议理由`: 有上一轮回答支撑，当前句子是在保留和求证，而不是直接硬否定。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 4. `soft_doubt_004`

- `batch`: `challenge`
- `query`: `你是不是搞错了？`
- `history`:
  - `assistant`: `这种情况一定不构成责任。`
- `建议 expected`: `false`
- `建议理由`: 这更接近硬质疑/直接反驳，应落到 hard challenge，而不是 soft_doubt。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 5. `soft_doubt_005`

- `batch`: `meta`
- `query`: `这个规则我有点没看懂，你是说在任何情况下都适用吗？`
- `history`:
  - `assistant`: `这种规则在任何情况下都适用。`
- `建议 expected`: `true`
- `建议理由`: 语气温和，但明显在对上一轮绝对化说法做保留式求证，应计入 soft_doubt。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 6. `soft_doubt_006`

- `batch`: `challenge`
- `query`: `真的是所有情况都这样吗？`
- `history`:
  - `assistant`: `所有情况下都只能这样处理。`
- `建议 expected`: `true`
- `建议理由`: 对绝对化结论进行保留式求证，属于 soft_doubt。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: 有上一轮绝对化结论，“真的是所有情况都这样吗”是在保留式求证，属于 soft_doubt。

#### 7. `soft_doubt_007`

- `batch`: `challenge`
- `query`: `会不会还有别的理解？`
- `history`:
  - `assistant`: `这个结论只有一种解释。`
- `建议 expected`: `true`
- `建议理由`: 是在弱化、试探上一轮唯一化表述，不是强否定。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: “会不会还有别的理解”是在弱化上一轮唯一化结论，属于软质疑。

#### 8. `soft_doubt_008`

- `batch`: `challenge`
- `query`: `你这明显说错了吧？`
- `history`:
  - `assistant`: `这种情况一定合法。`
- `建议 expected`: `false`
- `建议理由`: “明显说错了”是强否定，更接近 hard challenge。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=false`
- `你的理由`: “明显说错了”是直接否定，更适合作为 hard challenge。

#### 9. `soft_doubt_009`

- `batch`: `standard_qa`
- `query`: `这种规定是不是一般都这样？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 没有上文支撑时，这是普通求知，不应标 soft_doubt。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=false`
- `你的理由`: 无 history 时，这是普通适用规律求知，不应仅因“是不是”判为 soft_doubt。

#### 10. `soft_doubt_010`

- `batch`: `challenge`
- `query`: `你是不是把条件漏掉了？`
- `history`:
  - `assistant`: `完全不需要其他条件。`
- `建议 expected`: `true`
- `建议理由`: 对上一轮绝对化说法提出保留和补充条件，仍属于软质疑。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: 有上一轮“完全不需要其他条件”的绝对化回答，当前是在质疑是否遗漏条件，属于 soft_doubt。

#### 11. `soft_doubt_011`

- `batch`: `meta`
- `query`: `这个依据是哪来的？`
- `history`:
  - `assistant`: `这个结论就是这样。`
- `建议 expected`: `false`
- `建议理由`: 这是 ask_source 追问，不应记为 soft_doubt。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=false`
- `你的理由`: 主轴是依据来源追问，应归入 ask_source，不计入 soft_doubt。

#### 12. `soft_doubt_012`

- `batch`: `challenge`
- `query`: `难道就没有别的例外吗？`
- `history`:
  - `assistant`: `这里没有任何例外。`
- `建议 expected`: `true`
- `建议理由`: 带有怀疑和求证色彩，但未形成直接硬否定，属于 soft_doubt。
- `review`: [1] 同意 [ ] 不同意
- `你的结论`: `expected=true`
- `你的理由`: “难道就没有别的例外吗”是在保留式质疑上一轮无例外结论，属于 soft_doubt。

---

## 3. 最小 review 输出格式

如果你想直接把结果发我，最简单可以按下面格式：

```text
generic_006: 同意
generic_007: 不同意 -> false
理由：……
judgment_006: 同意
soft_doubt_006: 同意
```

这样我就能继续把结果回填进 JSONL 和后续评估数据里。
