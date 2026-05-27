# Challenge Boundary

## Challenge 和 Context Binding 的关系

`ContextBindingPower` 不负责 challenge adjudication。

它只负责：

- 产出 relevant set
- resolve / rewrite / clarification

`ChallengePower` 负责：

- 接收被质疑对象
- 先检查 existing evidence 是否足够
- 不够再 retrieve
- 再做 adjudication

## 当前边界状态

当前 `QA` 主链已经接入 `ContextBindingPower`。

但 `ChallengePower` 仍未完全统一进同一套 V2 contract，具体表现为：

- 仍保留旧式 target binding 路径
- 仍未完全消费同一 relevant set discipline

## 当前正式口径

对外正式说法应固定为：

- `Context Binding` 负责 relevant set 和 resolution
- `Challenge` 负责基于目标对象消费已有证据与补检索
