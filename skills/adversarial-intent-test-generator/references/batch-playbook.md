# Batch Playbook

Use this file when choosing where to add pressure.

## standard_qa

Use when you want a clean single-question baseline.

Good pressure points:

- domain coverage gaps
- short legal or medical questions with weak domain keywords

## fuzzy_qa

Use when the user asks a domain question but with insufficient facts.

Good pressure points:

- legal judgment without factual detail
- medical judgment without symptoms, timeline, or treatment specifics

Expected pattern:

- `main_intent=qa`
- `needs_clarification=true`
- `route=direct`
- `mode=clarify`

## follow_up

Use when the user depends on previous turns.

Good pressure points:

- same query with and without history
- history exists but the last topic was unrelated
- short referential phrasing like "what about this case then"

Recommended history templates:

- `supportive`
- `weak`
- `conflicting`

## challenge

Use when the user disputes, questions, or attacks a previous answer.

Good pressure points:

- explicit contradiction
- indirect skepticism
- rhetorical attacks
- challenge mixed with ask_source

Recommended history templates:

- `supportive`
- `weak`

## meta

Use when the user challenges, asks for evidence, or asks about system capability.

Good pressure points:

- `challenge` versus `ask_source`
- capability questions that mention domain words
- evidence requests without usable history

## mixed_intent

Use when multiple signals coexist.

Good pressure points:

- `challenge + ask_source`
- `follow_up + multi_question`
- `qa + compare`

## adversarial

Use when the user attacks the certainty, consistency, or legitimacy of prior reasoning.

Good pressure points:

- challenge phrasing that is indirect
- rhetorical questions
- emotionally charged criticism

## long_case_complex

Use when the user provides a long factual narrative and expects legal or medical analysis.

Good pressure points:

- causal chains
- multiple actors
- negligence versus unavoidable risk
- platform liability or employment disputes with several factual pivots

Expected pattern:

- usually `main_intent=qa`
- often `task.complexity=complex`
- often `route=agent`
