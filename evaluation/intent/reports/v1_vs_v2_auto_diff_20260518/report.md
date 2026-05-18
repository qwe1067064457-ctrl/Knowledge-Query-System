# V1 vs V2 Auto Label Diff

## Overall

- rows: `1381`
- evidence_changed_rows: `110`
- label_changed_rows: `110`

### Field Changes

- `control.mode`: `34`
- `control.route`: `53`
- `resolved.context_dependency`: `17`
- `resolved.main_intent`: `31`
- `resolved.modifiers.ask_capability`: `11`
- `resolved.modifiers.ask_source`: `4`
- `resolved.modifiers.challenge`: `3`
- `resolved.modifiers.follow_up`: `7`
- `resolved.modifiers.needs_clarification`: `10`
- `resolved.modifiers.out_of_scope`: `8`
- `resolved.modifiers.soft_doubt`: `2`
- `resolved.task.complexity`: `36`
- `resolved.task.shape`: `45`
- `resolved.task.topology`: `35`

### Top Transitions

- `resolved.task.topology:single->staged`: `23`
- `resolved.task.shape:verify->single_question`: `17`
- `resolved.task.complexity:simple->compound`: `16`
- `resolved.task.complexity:simple->complex`: `16`
- `control.route:rag->agent`: `16`
- `control.mode:clarify->normal`: `12`
- `control.mode:capability->normal`: `11`
- `resolved.modifiers.ask_capability:True->False`: `11`
- `resolved.main_intent:qa->chat`: `10`
- `control.route:direct->chat`: `9`
- `resolved.main_intent:unsupported->chat`: `8`
- `control.route:reject->chat`: `8`
- `resolved.modifiers.out_of_scope:True->False`: `8`
- `resolved.modifiers.follow_up:False->True`: `7`
- `resolved.task.topology:single->parallel_queries`: `7`
- `control.route:direct->rag`: `7`
- `resolved.main_intent:system->chat`: `7`
- `resolved.context_dependency:none->ambiguous`: `6`
- `control.mode:normal->clarify`: `6`
- `resolved.modifiers.needs_clarification:False->True`: `6`

## Per Dataset

### frozen_heldout_v2

- rows: `9`
- evidence_changed_rows: `7`
- label_changed_rows: `9`

### intent_query_full_set_campaign_v1_silver_v1

- rows: `1137`
- evidence_changed_rows: `30`
- label_changed_rows: `25`

### query_list_campaign_v1_silver_v1

- rows: `16`
- evidence_changed_rows: `1`
- label_changed_rows: `1`

### seed_query_20260514_campaign_v1_silver_v1

- rows: `40`
- evidence_changed_rows: `0`
- label_changed_rows: `0`

### seed_query_20260514_gold_v1

- rows: `15`
- evidence_changed_rows: `10`
- label_changed_rows: `15`

### seed_query_20260515_campaign_v2_silver_v1

- rows: `56`
- evidence_changed_rows: `1`
- label_changed_rows: `1`

### seed_query_20260515_gold_v1

- rows: `14`
- evidence_changed_rows: `11`
- label_changed_rows: `10`

### seed_query_20260515_gold_v2

- rows: `28`
- evidence_changed_rows: `0`
- label_changed_rows: `0`

### seed_query_20260516_gold_v1

- rows: `48`
- evidence_changed_rows: `34`
- label_changed_rows: `39`

### seed_query_20260517_gold_v1

- rows: `18`
- evidence_changed_rows: `16`
- label_changed_rows: `10`

