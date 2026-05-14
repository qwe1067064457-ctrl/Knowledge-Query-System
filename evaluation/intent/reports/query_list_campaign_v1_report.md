# Intent 评估统计表

## Overall

- samples: `16`

| metric | value |
| --- | --- |
| evidence_mode_correct | 10 |
| evidence_required_signals_correct | 7 |
| evidence_required_rules_correct | 15 |
| evidence_dependency_correct | 7 |
| evidence_unsupported_correct | 16 |
| resolved_main_intent_correct | 8 |
| resolved_complexity_correct | 14 |
| resolved_shape_correct | 8 |
| resolved_context_correct | 8 |
| control_route_correct | 5 |
| control_mode_correct | 7 |
| evidence_mode_accuracy | 0.625 |
| evidence_required_signals_accuracy | 0.4375 |
| evidence_required_rules_accuracy | 0.9375 |
| evidence_dependency_accuracy | 0.4375 |
| evidence_unsupported_accuracy | 1.0 |
| resolved_main_intent_accuracy | 0.5 |
| resolved_complexity_accuracy | 0.875 |
| resolved_shape_accuracy | 0.5 |
| resolved_context_accuracy | 0.5 |
| control_route_accuracy | 0.3125 |
| control_mode_accuracy | 0.4375 |

## Per Batch

| batch | samples | resolved_main_intent_accuracy | resolved_complexity_accuracy | resolved_shape_accuracy | control_route_accuracy | control_mode_accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| challenge | 4 | 0.75 | 1.0 | 0.75 | 0.5 | 0.5 |
| follow_up | 5 | 0.4 | 0.8 | 0.4 | 0.4 | 0.8 |
| fuzzy_qa | 2 | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| meta | 3 | 1.0 | 1.0 | 1.0 | 0.3333 | 0.3333 |
| mixed_intent | 2 | 0.0 | 0.5 | 0.0 | 0.0 | 0.0 |

## Rule Stats

| rule_id | hits | labeled_samples | tp | fp | fn | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| challenge.disagree | 3 | 10 | 2 | 1 | 0 | 0.6667 | 1.0 | 0.8 |
| context.follow_up.missing_history | 5 | 2 | 1 | 1 | 0 | 0.5 | 1.0 | 0.6667 |
| context.follow_up.reference | 3 | 5 | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| intent.qa.domain | 0 | 4 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| source.ask_basis | 3 | 7 | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| task.complex.request | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| task.enumerated_questions | 0 | 1 | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
