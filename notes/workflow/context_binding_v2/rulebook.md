# Context Binding Rulebook

## 规则的职责

规则只做两件事：

1. 候选缩小
2. fallback 分流

规则不做：

1. 最终 truth-like target 判定
2. 深语义等价判断

## query style 触发词

### challenge

- `不对`
- `有问题`
- `依据`
- `为什么`
- `漏了`
- `不成立`
- `错了`

### follow_up

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

## 规则直出

规则只在两类场景直出：

- 显式序号 / 多目标模式直接命中
- relevant set 只剩 1 个高置信候选

其余都交给主大模型。
