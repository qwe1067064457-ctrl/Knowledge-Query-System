# ADR README

## Purpose

This directory is for Architecture Decision Records.

Use ADRs to record decisions that future maintainers, reviewers, and agent workflows should not have to rediscover or re-litigate repeatedly.

Good ADR candidates:

- choosing a seam that will shape many future changes
- deciding why one module should remain rule-based
- deciding why a retrieval path is Skill-first
- deciding why a specific persistence model is file-first
- rejecting a tempting refactor for a load-bearing reason

Avoid writing ADRs for:

- temporary sequencing decisions
- obvious local cleanups
- things that are still pure brainstorming

---

## Current Status

This project now has an ADR home, but does not yet have a complete ADR set.

Recommended first ADR candidates:

1. Skill-first plus Hybrid Retrieval fallback
2. File-first local state as a product constraint
3. Intent pipeline shape: `input -> evidence -> resolved -> control`
4. Rule guardrails plus future small-model routing

---

## Minimal Template

Create files like:

- `ADR-0001-short-title.md`
- `ADR-0002-short-title.md`

Suggested structure:

```md
# ADR-0001: Title

## Status

Accepted | Proposed | Superseded

## Context

What problem or recurring decision pressure exists?

## Decision

What did we choose?

## Consequences

What becomes easier, harder, or intentionally constrained?

## Revisit Signals

What evidence would justify reopening this decision?
```

---

## Guidance For Future Skill Use

Skills like `improve-codebase-architecture`, `triage`, and `to-prd` should read this directory before making durable recommendations.

If a future discussion reveals a load-bearing reason for keeping or rejecting an architecture direction, prefer writing an ADR instead of letting that reasoning live only in chat history.

