# Intent 评估统计表

## Overall

- samples: `50`

| metric | value |
| --- | --- |
| evidence_mode_correct | 37 |
| evidence_required_signals_correct | 22 |
| evidence_required_rules_correct | 37 |
| evidence_dependency_correct | 25 |
| evidence_unsupported_correct | 50 |
| resolved_main_intent_correct | 30 |
| resolved_complexity_correct | 50 |
| resolved_shape_correct | 25 |
| resolved_context_correct | 33 |
| control_route_correct | 20 |
| control_mode_correct | 23 |
| evidence_mode_accuracy | 0.74 |
| evidence_required_signals_accuracy | 0.44 |
| evidence_required_rules_accuracy | 0.74 |
| evidence_dependency_accuracy | 0.5 |
| evidence_unsupported_accuracy | 1.0 |
| resolved_main_intent_accuracy | 0.6 |
| resolved_complexity_accuracy | 1.0 |
| resolved_shape_accuracy | 0.5 |
| resolved_context_accuracy | 0.66 |
| control_route_accuracy | 0.4 |
| control_mode_accuracy | 0.46 |

## Per Batch

| batch | samples | resolved_main_intent_accuracy | resolved_complexity_accuracy | resolved_shape_accuracy | control_route_accuracy | control_mode_accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| challenge | 25 | 0.76 | 1.0 | 0.56 | 0.44 | 0.24 |
| follow_up | 25 | 0.44 | 1.0 | 0.44 | 0.36 | 0.68 |

## Rule Stats

| rule_id | hits | labeled_samples | tp | fp | fn | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| challenge.disagree | 6 | 42 | 6 | 0 | 11 | 1.0 | 0.3529 | 0.5217 |
| context.follow_up.missing_history | 7 | 8 | 7 | 0 | 1 | 1.0 | 0.875 | 0.9333 |
| context.follow_up.reference | 26 | 25 | 17 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| intent.qa.domain | 2 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| source.ask_basis | 8 | 25 | 6 | 0 | 1 | 1.0 | 0.8571 | 0.9231 |
| task.enumerated_questions | 2 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
