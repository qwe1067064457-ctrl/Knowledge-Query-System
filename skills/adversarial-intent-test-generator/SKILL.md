---
name: adversarial-intent-test-generator
description: Generate hard and adversarial evaluation datasets for intent-recognition systems that route by rules or hybrid rule-plus-model logic. Use when Codex needs to create, expand, or revise intent test data that should pressure the four-layer path from input to evidence to resolved intent to control, especially for follow-up, challenge, ambiguous, mixed-intent, or complex-task cases.
---

# Adversarial Intent Test Generator

Generate test data as a rule-pressure workflow, not as a generic prompt-writing task.

This skill is a half-automatic adversarial dataset draft generator. It should produce high-quality structured drafts, not unquestioned ground truth.

## Quick Start

1. Identify the target layer:
   - `input`: pressure phrasing variety, ambiguity, or context dependence.
   - `evidence`: pressure required signals, required rules, unsupported flags, or dependency flags.
   - `resolved`: pressure `main_intent`, modifiers, `task.complexity`, `task.shape`, or `context_dependency`.
   - `control`: pressure route and mode so expensive requests do not fall into cheap flows.
2. Identify the target batch:
   - `standard_qa`
   - `fuzzy_qa`
   - `follow_up`
   - `meta`
   - `mixed_intent`
   - `adversarial`
   - `long_case_complex`
3. Identify the target rules or failure modes.
4. Generate a balanced set:
   - positive examples
   - clear negatives
   - near-miss negatives
   - mixed-intent or conflict cases when relevant
5. Emit data in the repo's four-layer schema. Read [four-layer-schema.md](references/four-layer-schema.md) before writing samples.

## Workflow

### Step 1: Define the core business target manually

Start from the minimum business decision that must be correct:

- `gold.resolved.main_intent`
- modifiers
- `gold.resolved.task.complexity`
- `gold.resolved.task.shape`
- `gold.control.route`
- `gold.control.mode`

Treat these fields as the manual source of truth for v1. Do not begin from fully enumerated rule hits.

### Step 2: Auto-fill the draft around that target

After the resolved intent and control are decided, prefill the draft:

- propose `input.user_query`
- construct `input.history`
- backfill minimal `gold.evidence`
- prefill `rule_expectations` only for rules under review

Use [history-templates.md](references/history-templates.md) whenever the sample depends on conversational context.

### Step 3: Run a mandatory consistency review

Every generated sample must pass these checks before it is accepted into the dataset:

1. Input support check:
   The `input` must genuinely support the chosen `gold.resolved`. If the query is too weak or too vague, revise the query or downgrade the label.
2. Minimum evidence check:
   `gold.evidence` must be the minimum sufficient evidence for the conclusion, not a padded list of every possible rule hit.
3. Routing cost check:
   `gold.control` must reflect the intended business cost. Avoid pushing a cheap request into an expensive flow or letting a high-risk request fall into a cheap flow.

Use [generation-modes.md](references/generation-modes.md) for the exact attack patterns and [batch-playbook.md](references/batch-playbook.md) for batch-specific pressure points.

## Attack Surface

Use one of these modes:

- Rule-centered:
  Start from one rule such as `challenge.disagree` or `source.ask_basis`, then generate positives, negatives, and near misses around it.
- Batch-centered:
  Start from one batch such as `follow_up` or `long_case_complex`, then pressure the whole route.
- Cost-centered:
  Start from a routing risk such as "complex request should not fall into simple rag" or "system capability query should not be treated as qa".

Prefer hard samples over clean samples. Spend most effort on:

- near-miss negatives
- ambiguous context
- mixed modifiers
- long factual inputs
- samples that change route if classified incorrectly

Do not spend the batch on easy, canonical phrasing unless you are intentionally building a regression set.

## Evidence Policy

Do not try to fully enumerate every possible rule hit. Only label:

- `required_signals`
- `required_rule_ids`
- `rule_expectations` for rules you want strict stats on
- `dependency_signals`
- `unsupported_signals`

## Failure Modes

If the goal is to improve the classifier, generate samples that expose concrete failure:

- `follow_up` without enough history
- challenge-like language that is actually a request for clarification
- `qa` versus `system`
- `compound` versus `complex`
- long case descriptions that should route to `agent`

Read [batch-playbook.md](references/batch-playbook.md) when the target batch is unclear.

## Output Contract

Emit samples in the same shape used by the repo's intent evaluation assets:

```json
{
  "id": "sample_id",
  "batch": "follow_up",
  "input": {
    "user_query": "Then what if the company is the counterparty?",
    "history": []
  },
  "gold": {
    "evidence": {
      "classifier_mode": "rule_plus_model",
      "required_signals": ["follow_up"],
      "required_rule_ids": ["context.follow_up.reference"],
      "rule_expectations": {
        "context.follow_up.reference": true,
        "challenge.disagree": false
      },
      "unsupported_signals": {
        "file_write_request": false,
        "file_delete_request": false,
        "kb_admin_request": false,
        "privileged_operation": false,
        "unknown_external_action": false
      },
      "dependency_signals": {
        "none": false,
        "history_reference": true,
        "previous_answer": false,
        "previous_retrieval": false,
        "ambiguous": false
      }
    },
    "resolved": {
      "main_intent": "qa",
      "modifiers": {
        "follow_up": true,
        "challenge": false,
        "ask_source": false,
        "ask_capability": false,
        "needs_clarification": false,
        "out_of_scope": false
      },
      "task": {
        "complexity": "simple",
        "shape": "single_question"
      },
      "context_dependency": "history_reference"
    },
    "control": {
      "route": "rag",
      "mode": "normal"
    }
  },
  "notes": "Follow-up with explicit history dependence."
}
```

## Repo Integration

When working in this repo:

- Put generated datasets under `backend_test/intent/test_data/`.
- Use a dedicated subdirectory for each campaign, such as `user_batch_v1` or `challenge_near_miss_v2`.
- Reuse or adapt repo scripts under `evaluation/intent/` when they already fit.
- Keep generated data reviewable. Prefer batch files over one giant blob.

Use `scripts/scaffold_intent_dataset.py` in one of two ways:

- empty scaffold:
  Generate empty batch files to fill manually.
- prefilled campaign:
  Generate a first-pass campaign with prefilled `gold` drafts and review hints.
- twin-boundary campaign:
  Use `--profile twins_campaign_v2` to generate fixed challenge-versus-clarify, follow_up-versus-ambiguous, and qa-versus-system benchmark pairs.
- query list campaign:
  Use `--profile from_query_list --input-file ...` to turn raw queries into supportive, weak, conflicting, near-miss, mixed, or cost-focused variants.

Supported input file formats:

- `.txt`: one query per line
- `.json`: list of strings or objects
- `.jsonl`: one object per line

Preferred object shape:

```json
{
  "id": "q_001",
  "query": "What about this case?",
  "hints": {
    "preferred_batch": "follow_up"
  }
}
```

## Guardrails

- Do not optimize for high scores.
- Do not mirror current rules too literally.
- Do not generate only canonical phrasing.
- Do not let `mixed` become a default escape hatch. Use it only when the shape cannot be expressed cleanly.
- Do not label unsupported or capability requests as qa just because they mention legal or medical words.

## Validation

After generating or revising a dataset:

1. Run the repo evaluation script on the new dataset.
2. Review `overall`, `per_batch`, and `rule_stats`.
3. Check whether the new data actually lowers over-optimistic metrics or exposes real conflicts.
4. Keep the dataset if it reveals something meaningful. Revise it if it only repeats easy cases.
5. Read `review_hints.risk_flags` first when triaging samples that need manual review.

For the first closed-loop campaign, focus on:

- `follow_up`
- `challenge`

Prefer:

- `near_miss`
- `mixed`

The intended success criterion is not a high metric. The intended success criterion is that previously inflated rule scores begin to drop on realistic adversarial drafts.
