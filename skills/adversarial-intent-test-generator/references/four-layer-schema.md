# Four-Layer Schema

Use the repo's intent evaluation schema as four layers:

```text
input -> evidence -> resolved -> control
```

## input

Describe the actual user-facing query and the history needed for context.

- `input.user_query`
- `input.history`

Do not hand-author `context_state` in dataset rows. Let the code derive it from `history`.

## evidence

Label only the minimum evidence needed for strict evaluation:

- `classifier_mode`
- `required_signals`
- `required_rule_ids`
- `rule_expectations`
- `unsupported_signals`
- `dependency_signals`

`rule_expectations` is the strict rule-eval contract:

- `true`: the rule should fire on this sample
- `false`: the rule should not fire on this sample

## resolved

This is the primary gold label:

- `main_intent`
- modifiers
- `task.complexity`
- `task.shape`
- `context_dependency`

Label this first.

## control

This is the coarse route:

- `route`
- `mode`

The point is not to specify execution details. The point is to test that the request lands on the right flow.
