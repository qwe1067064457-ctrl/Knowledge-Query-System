# MacBERT Baseline Dataset v1

这份目录是从 `evaluation/intent/exports/intent_training_v7.jsonl` 进一步整理出来的 `macbert-base` baseline 输入层。

当前拆成两个任务：

- `soft_doubt/`
  - 二分类
  - 每条记录包含：`id / text / label / label_name / source_dataset / label_tier`
- `task_shape/`
  - 小集合多分类
  - 标签集合：`single_question / verify / compare / summarize / multi_question`

目录说明：

- `train.jsonl`
  - 训练集
- `dev.jsonl`
  - 开发验证集
- `heldout.jsonl`
  - 冻结 benchmark
- `label_map.json`
  - 当前任务标签到整数 id 的映射

当前已知缺口：

- `soft_doubt/dev` 暂时没有正例
- baseline 已经可跑，但下一步仍应优先补一批 `soft_doubt=true` 的 `dev` 样本
