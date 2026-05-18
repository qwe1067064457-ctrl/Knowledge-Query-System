# Working Intent Docs

`notes/working/intent/` 是 working 层，不是稳定层。

这里保留的是：

- 过程稿
- 迁移稿
- 试验稿
- 还没有完全冻结的协议和结论

和 `notes/intent/` 的区别是：

- `notes/intent/`
  - 当前稳定口径
  - 适合对齐架构、讲项目、快速建立全局理解
- `notes/working/intent/`
  - 仍在演化
  - 适合追过程、看取舍、查过渡阶段决策

## 状态说明

后续 working 文档统一建议带这类头部信息：

```md
status: draft | active-working | promoted-partially | legacy-reference
related_current_doc: notes/intent/xxx.md
scope: ...
```

推荐含义：

- `draft`
  - 还在探索，不能当当前方案引用
- `active-working`
  - 当前还在推进、仍影响后续实现
- `promoted-partially`
  - 一部分稳定结论已经提升到 `notes/intent/`
- `legacy-reference`
  - 旧过程稿，保留参考，但不再代表现行口径

## 当前文件建议状态

### 仍然 active-working

- `evidence_resolver_refactor_lessons.md`
- `model_handoff_modes_v1.md`
- `rule_lite_shrink_checklist_v1.md`
- `sft_eval_protocol.md`
- `sft_label_spec.md`
- `sft_split_policy.md`

### promoted-partially

- `rule_lessons.md`
- `rule_supervision.md`
- `rule_tuning.md`
- `intent_sft_delivery.md`

### legacy-reference

- `auto_uplift_silver.md`
- `sft_preparation.md`
- `sft_gold_expansion_20260515_v2.md`
- `sft_gold_expansion_20260516.md`
- `sft_gold_expansion_20260517.md`

### 单独保留观察

- `intent_execution_flow_preparation.md`
  - 这是执行流准备稿
  - 仍然有价值
  - 但当前不应当作 understanding 稳定口径引用

## 当前 working 层的作用

你现在读 working 层，主要是为了：

1. 看某个设计是怎么演进出来的
2. 看哪些问题还没彻底定型
3. 看 V2 迁移过程中的临时协议
4. 看小模型、执行流、SFT 这些还在推进中的支线

## 当前一句话总结

如果 `notes/intent/` 是稳定知识层，那么 `notes/working/intent/` 就是：

> 记录迁移过程、保留设计取舍和承载未冻结细节的过渡层。
