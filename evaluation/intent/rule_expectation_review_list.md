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
- `建议理由`: 通用问答谓语明显，属于普通 QA，不依赖明确领域名词正则。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 2. `generic_002`

- `batch`: `chat_meta_boundary`
- `query`: `最近感觉事情越来越复杂。`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 表达情绪或感受，不是问答型请求。
- `review`: [1 ] 同意 [ ] 不同意
- `你的结论`: 属于普通chat?
- `你的理由`:

#### 3. `generic_003`

- `batch`: `standard_qa`
- `query`: `医保报销比例如何计算？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: 带有明确的求解问法“如何计算”，属于通用问答请求。
- `review`: [ ] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 4. `generic_004`

- `batch`: `standard_qa`
- `query`: `赔偿金额通常如何确定？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: 虽然带领域词，但更关键的是“如何确定”的通用问答谓语，应允许 generic QA 覆盖。
- `review`: [ ] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 5. `generic_005`

- `batch`: `meta`
- `query`: `有依据吗？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 这是 ask_source / meta 追问，不应计入 generic QA。
- `review`: [ ] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

---

### B. `intent.qa.judgment`

#### 3. `judgment_001`

- `batch`: `fuzzy_qa`
- `query`: `这样算医疗事故吗？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: 典型判断型 QA，询问事实是否构成某类责任或定性。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`: 这个query应该有上文!
- `你的理由`:

#### 4. `judgment_002`

- `batch`: `meta`
- `query`: `你刚才为什么这么说？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 这是追问依据/来源，不是判断型 QA。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:这个query应该有上文!, 我发现follow_up和challenge是不是有语义重叠
- `你的理由`:

#### 5. `judgment_003`

- `batch`: `fuzzy_qa`
- `query`: `医院这么做合理吗？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: `合理吗` 是典型判断型 QA 表达，询问行为是否成立或适当。
- `review`: [ ] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 6. `judgment_004`

- `batch`: `fuzzy_qa`
- `query`: `这样会被拘留吗？`
- `history`: `[]`
- `建议 expected`: `true`
- `建议理由`: 询问某种事实是否会触发法律后果，属于判断型 QA。
- `review`: [ ] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 7. `judgment_005`

- `batch`: `standard_qa`
- `query`: `医疗过失责任的构成要件是什么？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 这是定义 / 要件型 QA，不是判断型 QA。
- `review`: [ ] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

---

### C. `challenge.soft_doubt`

#### 5. `soft_doubt_001`

- `batch`: `challenge`
- `query`: `这个说法是不是太绝对了？`
- `history`:
  - `assistant`: `这种情况一定要赔偿。`
- `建议 expected`: `true`
- `建议理由`: 轻质疑、求证式反驳，有上一轮回答支撑，应标为 `soft_doubt`。
- `review`: [ 1] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 6. `soft_doubt_002`

- `batch`: `standard_qa`
- `query`: `这种规则是不是全国都适用？`
- `history`: `[]`
- `建议 expected`: `false`
- `建议理由`: 这是普通 QA 求知，不应因为“是不是”结构就标为 `soft_doubt`。
- `review`: [ ] 同意 [1 ] 不同意
- `你的结论`:作为普通 QA 也带有soft_doubt?
- `你的理由`:

#### 7. `soft_doubt_003`

- `batch`: `challenge`
- `query`: `你确定没有例外情况吗？`
- `history`:
  - `assistant`: `这个规则在所有情况下都适用。`
- `建议 expected`: `true`
- `建议理由`: 有上一轮回答支撑，当前句子是在保留和求证，而不是直接硬否定。
- `review`: [ ] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 8. `soft_doubt_004`

- `batch`: `challenge`
- `query`: `你是不是搞错了？`
- `history`:
  - `assistant`: `这种情况一定不构成责任。`
- `建议 expected`: `false`
- `建议理由`: 这更接近硬质疑 / 直接反驳，应落到 hard challenge，而不是 soft_doubt。
- `review`: [ ] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

#### 9. `soft_doubt_005`

- `batch`: `meta`
- `query`: `这个规则我有点没看懂，你是说在任何情况下都适用吗？`
- `history`:
  - `assistant`: `这种规则在任何情况下都适用。`
- `建议 expected`: `true`
- `建议理由`: 虽然语气温和，但明显是在对上一轮绝对化说法做保留式求证，应计入 `soft_doubt`。
- `review`: [ ] 同意 [ ] 不同意
- `你的结论`:
- `你的理由`:

---

## 3. 最小 review 输出格式

如果你想直接把结果发我，最简单可以按下面格式：

```text
generic_001: 同意
generic_002: 同意
judgment_001: 同意
judgment_002: 同意
soft_doubt_001: 不同意 -> false
理由：……
soft_doubt_002: 同意
```

这样我就能继续把结果回填进 JSONL 和后续评估数据里。
