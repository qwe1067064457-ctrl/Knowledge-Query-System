# Intent 评估统计表

## Overall

- samples: `70`

| metric | value |
| --- | --- |
| evidence_mode_correct | 43 |
| evidence_required_signals_correct | 28 |
| evidence_required_rules_correct | 56 |
| evidence_dependency_correct | 50 |
| evidence_unsupported_correct | 70 |
| resolved_main_intent_correct | 36 |
| resolved_complexity_correct | 61 |
| resolved_shape_correct | 30 |
| resolved_context_correct | 51 |
| control_route_correct | 36 |
| control_mode_correct | 51 |
| evidence_mode_accuracy | 0.6143 |
| evidence_required_signals_accuracy | 0.4 |
| evidence_required_rules_accuracy | 0.8 |
| evidence_dependency_accuracy | 0.7143 |
| evidence_unsupported_accuracy | 1.0 |
| resolved_main_intent_accuracy | 0.5143 |
| resolved_complexity_accuracy | 0.8714 |
| resolved_shape_accuracy | 0.4286 |
| resolved_context_accuracy | 0.7286 |
| control_route_accuracy | 0.5143 |
| control_mode_accuracy | 0.7286 |

## Per Batch

| batch | samples | resolved_main_intent_accuracy | resolved_complexity_accuracy | resolved_shape_accuracy | control_route_accuracy | control_mode_accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| adversarial | 5 | 0.4 | 1.0 | 0.0 | 0.4 | 0.0 |
| chat | 10 | 0.9 | 1.0 | 1.0 | 0.9 | 0.9 |
| follow_up | 10 | 0.2 | 1.0 | 0.2 | 0.2 | 1.0 |
| fuzzy_qa | 10 | 0.2 | 1.0 | 0.2 | 0.6 | 0.6 |
| long_case_complex | 5 | 0.6 | 0.0 | 0.0 | 0.0 | 0.6 |
| meta | 10 | 0.7 | 1.0 | 0.8 | 0.7 | 0.7 |
| mixed_intent | 10 | 0.6 | 0.6 | 0.3 | 0.5 | 0.6 |
| standard_qa | 10 | 0.5 | 1.0 | 0.5 | 0.5 | 1.0 |

## Rule Stats

| rule_id | hits | labeled_samples | tp | fp | fn | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| challenge.disagree | 4 | 35 | 4 | 0 | 8 | 1.0 | 0.3333 | 0.5 |
| context.follow_up.missing_history | 10 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| context.follow_up.reference | 16 | 12 | 12 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| intent.chat.greeting | 0 | 11 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| intent.qa.domain | 21 | 39 | 9 | 3 | 3 | 0.75 | 0.75 | 0.75 |
| source.ask_basis | 6 | 9 | 5 | 0 | 2 | 1.0 | 0.7143 | 0.8333 |
| system.capability.ask | 1 | 5 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 |
| task.complex.request | 0 | 8 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| task.enumerated_questions | 4 | 7 | 2 | 0 | 1 | 1.0 | 0.6667 | 0.8 |
