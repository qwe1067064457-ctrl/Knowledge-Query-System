# Intent 评估统计表

## Overall

- samples: `24`

| metric | value |
| --- | --- |
| evidence_mode_correct | 14 |
| evidence_required_signals_correct | 14 |
| evidence_required_rules_correct | 21 |
| evidence_dependency_correct | 17 |
| evidence_unsupported_correct | 24 |
| resolved_main_intent_correct | 16 |
| resolved_complexity_correct | 24 |
| resolved_shape_correct | 17 |
| resolved_context_correct | 17 |
| control_route_correct | 12 |
| control_mode_correct | 17 |
| evidence_mode_accuracy | 0.5833 |
| evidence_required_signals_accuracy | 0.5833 |
| evidence_required_rules_accuracy | 0.875 |
| evidence_dependency_accuracy | 0.7083 |
| evidence_unsupported_accuracy | 1.0 |
| resolved_main_intent_accuracy | 0.6667 |
| resolved_complexity_accuracy | 1.0 |
| resolved_shape_accuracy | 0.7083 |
| resolved_context_accuracy | 0.7083 |
| control_route_accuracy | 0.5 |
| control_mode_accuracy | 0.7083 |

## Per Batch

| batch | samples | resolved_main_intent_accuracy | resolved_complexity_accuracy | resolved_shape_accuracy | control_route_accuracy | control_mode_accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| challenge | 8 | 0.75 | 1.0 | 0.75 | 0.25 | 0.25 |
| follow_up | 8 | 0.75 | 1.0 | 0.75 | 0.75 | 1.0 |
| meta | 4 | 0.75 | 1.0 | 1.0 | 0.75 | 0.75 |
| standard_qa | 4 | 0.25 | 1.0 | 0.25 | 0.25 | 1.0 |

## Rule Stats

| rule_id | hits | labeled_samples | tp | fp | fn | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| challenge.disagree | 2 | 12 | 2 | 0 | 2 | 1.0 | 0.5 | 0.6667 |
| context.follow_up.missing_history | 4 | 4 | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| context.follow_up.reference | 4 | 8 | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| intent.qa.domain | 3 | 8 | 1 | 1 | 3 | 0.5 | 0.25 | 0.3333 |
| source.ask_basis | 1 | 8 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| system.capability.ask | 3 | 8 | 3 | 0 | 1 | 1.0 | 0.75 | 0.8571 |
