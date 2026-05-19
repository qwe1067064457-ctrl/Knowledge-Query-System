# Intent Rule-Lite Strategy

## 1. 为什么要继续 rule-lite

当前最重要的判断不是“规则还能不能继续变复杂”，而是：

- 继续把 rule 层做重，会越来越吃力不讨好

原因很明确：

1. rule 擅长高精度模式
2. rule 不擅长开放语义理解
3. rule 不擅长柔性澄清判断
4. rule 不擅长区分“回答结构”与“执行步骤”

所以当前方向不是：

- `rule -> 0`

而是：

- `rule-lite + model-centric understanding`

## 2. rule-lite 的核心原则

### 原则 1：做不到就不要死扛

如果某类理解：

- 依赖开放表达
- 强依赖上下文
- 经常边界模糊
- 难以稳定写出高精度规则

那 rule 就不该继续死扛终判。

### 原则 2：能做粗识别，就不做强裁决

例如：

- 可以识别 `challenge`
- 但不必 rule 直接强判“必须 clarify”

### 原则 3：能做候选态，就不做执行承诺

例如：

- `clarify_candidate`
- `possibly_ambiguous`
- `needs_context_check`

这些都比“直接澄清”更适合放在 rule 层。

## 3. 哪些继续留在 rule

### 3.1 guardrail

- `unsupported / safety`
- 明显越权
- 高风险操作

### 3.2 粗分类

- `qa`
- `chat`
- `system`
- `unsupported`

### 3.3 粗识别

- `follow_up`
- `ask_source`
- `challenge`
- `soft_doubt`
- `scope_question`

### 3.4 资产角色

- baseline
- teacher
- regression anchor

## 4. 哪些不再让 rule 死扛

### 4.1 强 clarify 裁决

rule 只应提示：

- `clarify_candidate`
- `possibly_ambiguous`
- `needs_context_check`

不应最终拍板：

- 一定要澄清

### 4.2 细粒度 task 终判

例如：

- 一定是 `complex`
- 一定该 `orchestrated`
- 一定该 `staged`

这些都应更保守。

### 4.3 回答结构 vs 执行步骤终判

像：

- `先说是否成立，再说依据，再说风险`

rule 不该直接判成 staged execution。

### 4.4 柔性 decomposition

是否真的要：

- query decomposition
- task decomposition

rule 更适合给粗提示，而不是终判。

### 4.5 过细 workflow 决策

rule 不该过早替 workflow 做太多细决定。

## 5. 和模型的职责分工

### rule 做什么

- 粗分类
- 粗识别
- safety / guardrail
- baseline / teacher

### SFT 小模型做什么

- 中层语义理解
- 更柔性的 task / context 收敛
- `clarify_candidate` 的进一步判断
- `ask_source / challenge / soft_doubt` 的细化理解

### 主回答模型 / workflow 做什么

- 最终 clarify 判断
- 最终回答结构组织
- 复杂执行前理解补足
- 小模型仍不稳的开放式理解

## 6. 三种模式

### `rule_only`

适合：

- baseline
- 冷启动
- hard gate
- 回归基线

### `rule_plus_model`

这是当前最现实的主路线。

适合：

- rule 做 coarse understanding
- model 做中层收敛增强
- control / workflow 再承接

### `model_first_rule_guard`

这是长期目标态。

适合：

- model 先理解
- rule 只做 safety / guard

当前还没有完全产品化落地，但方向已经明确。

## 7. 为什么这不意味着“项目不新颖了”

相反，这更成熟。

真正有价值的新颖点，不是：

- 用规则提前决定越来越多的事

而是：

- `rule-lite + model-centric understanding`
- `structured resolved output`
- `workflow-aware but not workflow-deciding understanding`
- `V1 / V2` 双轨数据治理

这套东西更有长期工程价值，也更适合项目讲解。

## 8. 一句话总结

`rule-lite` 的核心不是“规则变弱”，而是：

> 把 rule 层收缩到它真正擅长的部分，把开放、柔性、上下文强依赖的理解逐步让给模型和后续主回答层。
