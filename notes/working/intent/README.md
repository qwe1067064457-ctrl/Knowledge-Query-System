# Working Intent Docs README

这个目录用于存放 `intent` 模块仍处于中间态的执行文档。

它和 `notes/intent/` 的区别是：

- `notes/intent/`
  - 记录当前已经相对稳定的结构、评估、规则调优与交付信息
- `notes/working/intent/`
  - 记录仍在冻结口径中的执行协议
  - 例如标签规范、切分规则、训练评估协议

当前放在这里的文档，默认都还可能继续调整：

- `sft_label_spec.md`
- `sft_split_policy.md`
- `sft_eval_protocol.md`

等这些协议经过一轮样本扩充和 baseline 训练验证后，再考虑提升到 `notes/intent/`。
