# Challenge Review Runtime Skill

## 作用

把 challenge 轮收敛成目标选择、证据复核与回答约束。

## 何时使用

- 用户质疑上一轮结论
- 用户要求给出依据、纠错或复核

## 何时不要使用

- 普通检索问答
- 仅仅是闲聊追问

## 流程

1. challenge target selection
2. evidence check
3. follow-up retrieval planning
4. challenge re-evaluate
5. `answer_constraint`

## 输出契约

返回 `ChallengeSkillResult`。

## 失败兜底

- target not found -> `needs_clarification`
- evidence weak -> `insufficient_evidence`
