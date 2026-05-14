# Intent SFT Delivery

## 1. 文档定位

这份文档是当前 `intent` 小模型 SFT 准备阶段的完整交付文档。

它的目标不是解释某一个局部文件，而是让一个**新开对话的 AI 或新接手的开发者**，只读这一份文档就能快速知道：

- 当前 `intent` 模块为什么要做小模型
- 规则层已经推进到了什么程度
- 现有训练与评估数据资产分别是什么
- 哪些数据可以训练，哪些只能评估
- 第一版小模型应该预测什么，不应该接管什么
- 进入训练前还缺什么

如果只看一份文档来承接当前阶段，优先看这份。

---

## 2. 当前阶段结论

### 2.1 为什么现在开始准备 SFT

当前 `intent` 模块已经完成了规则层的第一阶段收口：

- `input -> evidence -> resolved -> control` 四层结构已经稳定
- `signal_buckets`、`ContextSignals`、`global stable rules`、`group_shared / domain bootstrap rules` 已有清晰边界
- 规则层已经能作为：
  - baseline
  - guardrail
  - weak-supervision teacher
  - 数据工厂

但规则层的能力边界也已经很明确：

- 对高确定性、结构化、强锚点表达较稳
- 对开放表达、元分析型问句、弱语气质疑、复杂边界语义天然有瓶颈
- 如果继续完全靠人工补规则，边际收益会快速下降

因此当前决策是：

- **规则层不再追求覆盖所有自然语言表达**
- **转向为小模型准备更干净的数据、标签和评估口径**

### 2.2 当前最重要的工程判断

当前 `intent` 系统的职责分配是：

- 规则层负责：
  - 高确定性识别
  - 护栏
  - 可解释性
  - 数据预标与弱监督
- 小模型负责：
  - 开放表达
  - 弱显式 QA
  - `generic`、`soft_doubt`、边界语义
  - 规则难以穷举的隐式语义理解

换句话说：

> 规则负责“稳”，小模型负责“活”。

---

## 3. 当前规则层状态

### 3.1 结构状态

当前 `intent` 采用四层链路：

1. `input`
2. `evidence`
3. `resolved`
4. `control`

其中：

- `evidence`：产出多值证据，允许冲突
- `resolved`：把多值证据收敛成单值决策
- `control`：把收敛结果映射成执行流开关

### 3.2 规则资产状态

当前规则资产分成两层：

- `global stable rules`
  - 跨知识域稳定
  - 适合长期固化
- `group_shared / domain bootstrap rules`
  - 当前知识组共享锚点
  - 适合冷启动
  - 不应被视为全局稳定语义

`domain bootstrap` 已经配置化外提，后续如果接动态调优 agent，应优先修改配置资产，而不是直接回改主分类逻辑。

### 3.3 当前规则层定位

当前规则层已经不再以“无限追分”为目标。

它现在的定位是：

- 稳定基线
- 规则护栏
- 评估辅助
- 训练数据工厂

---

## 4. 已完成的数据资产

### 4.1 项目级 query 输入源

#### query full set

- [intent_query_full_set.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/query_inputs/intent_query_full_set.md)

定位：

- 项目级 seed query 主版本
- 用于生成对抗样本、监督样本和后续增量数据
- 不再只是 skill 私有参考资料

#### 结构化 query 输入

- [seed_query_20260514.jsonl](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/query_inputs/seed_query_20260514.jsonl)
- [heldout_judgment_soft_doubt_20260514.jsonl](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/query_inputs/heldout_judgment_soft_doubt_20260514.jsonl)

定位：

- query 级输入源
- 适合作为脚本化派生输入

### 4.2 四层 gold 数据

#### 训练主 gold

- [seed_query_20260514_gold_v1](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/backend_test/intent/test_data/seed_query_20260514_gold_v1)

内容：

- `qa_generic_seed.json`
- `qa_judgment_seed.json`
- `soft_doubt_seed.json`

定位：

- 当前第一批人工确认的四层 gold
- 适合作为 `train/dev` 的主要高质量来源

#### 历史 held-out gold

- [heldout_judgment_soft_doubt_gold_v1](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/backend_test/intent/test_data/heldout_judgment_soft_doubt_gold_v1)

定位：

- 曾用于真实泛化验证
- 后续已经参与过最后一轮规则收口
- 不能再视为完全冻结的最终 held-out
- 现在更接近 calibration / dev 辅助资产

### 4.3 冻结 held-out

- [frozen_heldout_v2](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/backend_test/intent/test_data/frozen_heldout_v2)

内容：

- `qa_generic_frozen.json`
- `qa_judgment_frozen.json`
- `soft_doubt_frozen.json`

定位：

- 当前第一版**真正冻结**的 held-out
- 不得参与规则调优
- 不得回填训练集
- 用于后续统一验证规则冻结后的状态和小模型效果

### 4.4 规则级监督资产

- [rule_supervision_approved_v1.jsonl](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/rule_supervision_approved_v1.jsonl)

定位：

- 当前已批准的严格规则监督
- 已覆盖：
  - `intent.qa.generic`
  - `intent.qa.judgment`
  - `challenge.soft_doubt`

配套文件：

- [rule_expectation_annotation_template.jsonl](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/rule_expectation_annotation_template.jsonl)
- [rule_expectation_review_list.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/rule_expectation_review_list.md)

### 4.5 训练导出资产

- [intent_training_v1.jsonl](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/exports/intent_training_v1.jsonl)

导出脚本：

- [export_intent_training_set.py](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/export_intent_training_set.py)

定位：

- 第一版 SFT-ready JSONL 导出
- 当前是数据导出基线，不等于最终训练全集

---

## 5. 数据谱系

当前数据关系建议按下面理解：

### 5.1 上游 seed 层

- `evaluation/intent/query_inputs/intent_query_full_set.md`
- `evaluation/intent/query_inputs/*.jsonl`

作用：

- 提供原始 query 源头
- 提供脚本化派生输入

### 5.2 派生 campaign 层

- `backend_test/intent/test_data/seed_query_20260514_campaign_v1`
- `backend_test/intent/test_data/heldout_judgment_soft_doubt_v1`

作用：

- 对抗样本草案
- 规则压测
- 继续扩 badcase / near-miss

### 5.3 gold 层

- `seed_query_20260514_gold_v1`
- `heldout_judgment_soft_doubt_gold_v1`
- `frozen_heldout_v2`

作用：

- 四层人工/高质量确认样本
- 用于训练、验证、冻结评估

### 5.4 supervision 层

- `rule_supervision_approved_v1.jsonl`

作用：

- 严格规则监督
- 支撑 `rule_stats`

### 5.5 export 层

- `intent_training_v1.jsonl`

作用：

- 为小模型训练准备统一输入格式

---

## 6. 当前可用标签定义

### 6.1 第一版模型建议预测的目标

当前建议第一版小模型预测：

- `main_intent`
- `follow_up`
- `ask_source`
- `challenge`
- `soft_doubt`
- `needs_clarification`
- 关键 `task.shape`

建议第一版 `task.shape` 只保留高价值主标签：

- `single_question`
- `verify`
- `compare`
- `summarize`
- `multi_question`

### 6.2 当前不建议第一版直接接管的目标

不建议第一版直接预测：

- `control.route`
- `control.mode`

原因：

- 这两个字段更偏策略映射
- 当前更适合继续由规则从 `resolved` 映射出来

### 6.3 当前还缺什么

虽然方向已明确，但严格的 label spec 还未独立沉淀成单独文档。

后续应新增：

- `sft_label_spec.md`

至少补齐：

- `main_intent` 枚举全集
- modifiers 的最终标签集合
- `task.shape` 的最终枚举
- 多头分类还是多标签分类
- 标签冲突处理规则

---

## 7. 数据分层口径

当前建议使用三层：

### gold

- 人工确认
- 或四层 gold 明确确认
- 可直接进入 `train/dev/heldout`

### silver

- 规则或 skill 预标
- 需要抽样复核
- 可用于扩大训练规模
- 不应和 `gold` 混成同权重

### weak

- 仅规则推断
- 适合作为蒸馏或辅助训练来源
- 不适合作为第一版最高权重监督

---

## 8. 当前 split 建议

### 8.1 现阶段原则

- `train`
  - 以当前 `gold` 为主
- `dev`
  - 从非冻结 `gold` 中切出一小部分
- `heldout`
  - 固定使用 `frozen_heldout_v2`

### 8.2 当前未完全落地的部分

目前还没有形成一份独立、最终冻结的 split policy 文档。

后续需要补：

- `sft_split_policy.md`

至少明确：

- 哪些文件进入 `train`
- 哪些文件进入 `dev`
- 去重策略
- 同 seed 派生样本是否允许跨 split
- `heldout` 的冻结规则

---

## 9. 当前导出格式

当前 `intent_training_v1.jsonl` 每条导出包含：

- `id`
- `batch`
- `split`
- `input`
- `evidence`
- `resolved`
- `control`
- `metadata`

其中 `metadata` 当前包含：

- `source_dataset`
- `source_query_id`
- `label_tier`
- `label_source`
- `review_status`
- `difficulty`
- `is_heldout`
- `is_strict_rule_supervision`

这已经足够作为第一版训练格式基线，但还不是最终训练协议。

---

## 10. 当前模型建议

如果目标是：

- 意图识别不太重
- 延迟较低
- 精度明显高于纯规则

第一版优先建议：

- `BERT` / `RoBERTa` 类 encoder classifier

不建议第一版就直接上大生成模型做主路由，原因是：

- 推理成本高
- 结构化输出约束更难
- 当前标签更适合分类头

---

## 11. 当前评估口径

### 11.1 规则评估

当前已有：

- `overall`
- `per_batch`
- `rule_stats`

说明：

- `overall / per_batch` 更偏端到端评估
- `rule_stats` 是规则级严格监督评估

### 11.2 当前还缺的模型评估协议

如果进入 SFT，需要补一份：

- `sft_eval_protocol.md`

至少明确：

- 主指标
  - accuracy
  - macro F1
  - per-label recall
- 是否按 `batch` 拆开看
- 是否保留 confusion matrix
- `heldout` 过线标准

---

## 12. 当前仍未完成的事项

### 已完成

- 规则层已完成第一阶段收口
- `generic / judgment / soft_doubt` 已完成一轮严格监督
- 训练导出脚本已存在
- `frozen_heldout_v2` 已建立
- query full set 已提升为项目级输入资产

### 未完成

1. `train/dev` 真实切分仍未最终冻结
2. 第一版 label spec 仍未独立文档化
3. `silver / weak` 扩充策略仍未固化
4. 第一版训练脚本尚未开始
5. 第一版模型评估协议尚未独立文档化

---

## 13. 新对话接手建议

如果是新开一个对话，建议按下面顺序进入：

1. 先读本文件
2. 再读 [sft_preparation.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/sft_preparation.md)
3. 再读 [intent_project_info.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/intent_project_info.md)
4. 再读 [intent_testing_and_evaluation.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/intent_testing_and_evaluation.md)
5. 最后根据任务类型进入：
   - 规则细节：看 [rule_tuning.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/rule_tuning.md)
   - 监督口径：看 [rule_supervision.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/rule_supervision.md)
   - 数据输入源：看 [intent_query_full_set.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/query_inputs/intent_query_full_set.md)

---

## 14. 一句话总结

当前 `intent` 小模型 SFT 阶段的真实状态是：

> 规则层已经完成第一轮工程收口，当前最重要的不是继续堆规则，而是把 query 输入源、gold、strict supervision、frozen held-out、导出格式、label spec 和 split policy 整理成一套真正可训练、可验证、可交接的数据与文档系统。
