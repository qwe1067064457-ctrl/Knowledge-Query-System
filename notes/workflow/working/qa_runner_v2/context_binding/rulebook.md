# Context Binding Rulebook

## 规则的职责

规则只做两件事：

1. 候选缩小
2. fallback 分流

规则不做：

1. 最终 truth-like target 判定
2. 深语义等价判断

## query style

### challenge

命中词：

- `不对`
- `有问题`
- `依据`
- `为什么`
- `漏了`
- `不成立`
- `错了`

### follow_up

命中词：

- `这个`
- `那个`
- `上面`
- `刚才`
- `前面`
- `另一个`
- `第一点`
- `第二点`
- `第三点`
- `第一个`
- `第二个`
- `第三个`

### multi_target

命中词：

- `前两个`
- `两个`
- `两条`
- `分别`
- `都`
- `以及`
- `和`

## relevant set filter

### 1. recent/type/status

- 只看 active 候选
- 先按 query style 过滤 entry type

### 2. explicit patterns

- `第一点/第二点/第三点`
  - 优先按 `unit_index` 直接缩候选
- `前两个/分别`
  - 直接截取前 2 个高相关候选
- `这个说法/那个结论`
  - 优先保留 `answer_unit + user_assertion`

### 3. score ranking

排序因素：

- entry type bonus
- confidence bonus
- query-content keyword overlap
- challenge bonus

## fallback routing

### `retrieve_on_raw_query`

- relevant set 为空
- query 自包含

### `needs_clarification`

- relevant set 为空但 query 明显依赖上下文
- 或 relevant set 多个强候选无法稳定区分

### `rewrite_without_target`

- target 不明确
- 但 topic 可恢复

### `answer_from_context_only`

- 当前问题本身不需要 retrieval
- 且 answer side 可以直接消费上下文
