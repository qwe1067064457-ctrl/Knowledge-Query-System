# History Templates

Use explicit history templates whenever the sample depends on context.

## supportive

Use when the previous turns clearly support the current label.

Best for:

- valid `follow_up`
- standard `challenge`
- `ask_source` after an earlier answer

Goal:

- test baseline recall
- confirm the route is still reachable under good context

## weak

Use when some prior context exists but it is insufficient for a confident carry-over.

Best for:

- follow-up-like language with missing specifics
- challenge-like language that is really confusion
- evidence requests that lack a concrete earlier answer

Goal:

- force `needs_clarification`
- avoid hallucinated linkage

## conflicting

Use when history exists but the topic drifts or conflicts with the current query.

Best for:

- pressure-testing whether the classifier links on mere context presence
- exposing bad follow-up recall that is really false association

Goal:

- catch "history exists therefore it must be follow-up" failure modes

## Usage Rule

When generating contextual samples, label the history template in `review_hints` or `notes` so reviewers know what kind of context pressure was intended.
