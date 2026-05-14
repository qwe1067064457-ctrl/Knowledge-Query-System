# Generation Modes

Use these modes intentionally.

## positive

Generate a clean example that should clearly support the target rule or route.

Use for:

- regression coverage
- sanity checks
- proving a route is still reachable

## negative

Generate an example that should clearly not support the target rule or route.

Use for:

- precision checks
- unsupported-vs-qa boundaries
- system-vs-chat boundaries

## near_miss

Generate an example that looks similar to the target class but should resolve differently.

Use for:

- challenge versus clarification
- follow-up versus ambiguous
- ask_source versus challenge
- qa versus system

This is the highest-value mode for rule pressure.

Preferred twin boundaries:

- challenge versus clarify
- follow_up versus ambiguous
- qa versus system

## mixed

Generate an example that legitimately contains multiple signals and must be resolved correctly.

Use for:

- `challenge + ask_source`
- `follow_up + multi_question`
- `qa + complex`
- long factual inputs that should route to `agent`

## cost_focused

Generate examples where the main value is the routing cost of a mistake.

Examples:

- a complex case should not fall into simple `rag`
- a direct capability question should not trigger qa retrieval
- a follow-up without history should not be answered as if context exists
- a long query that still only asks for one definition should not be escalated to `agent`

Expected labeling behavior:

- add a note that explains why the sample is easy to route incorrectly
- add `CONTROL_ROUTE_COST_RISK` when the route is intentionally the fragile part
- prefer these samples in `mixed_intent`, `long_case_complex`, and fuzzy single-question inputs

## from_query_list

This is not a separate label mode. It is a campaign construction mode.

Use it when you already have raw business queries and want the skill to derive:

- supportive history variants
- weak or conflicting history variants
- near-miss rewrites
- mixed or cost-focused variants when requested

The intended output is a structured dataset draft, not final gold truth.

## twins_campaign_v2

This is a maintained benchmark campaign profile.

Use it when you want a stable adversarial set that keeps wording close while flipping the intended route.

Current twin families:

- challenge versus clarify
- follow_up versus ambiguous
- qa versus system
