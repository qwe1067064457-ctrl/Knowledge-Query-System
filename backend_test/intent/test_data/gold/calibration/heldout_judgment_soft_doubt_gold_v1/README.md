# heldout_judgment_soft_doubt_gold_v1

This dataset is a held-out four-layer gold draft for judgment and soft_doubt generalization checks.

Scope:
- `intent.qa.judgment`
- `challenge.soft_doubt`

Purpose:
- verify whether the current rules still hold on unseen paraphrases
- keep these samples outside the current tuning loop until validation time
- provide a cleaner held-out check than the raw query-list scaffold

Files:
- `qa_judgment_heldout.json`
- `soft_doubt_heldout.json`
