from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from intent.sft.data import MultiLabelExample, load_multilabel_bundle, summarize_bundle
from intent.sft.metrics import apply_thresholds, choose_thresholds, compute_multilabel_metrics


@dataclass(frozen=True)
class SplitPredictions:
    probabilities: list[list[float]]
    gold: list[list[int]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a multi-signal evidence baseline with a BERT encoder.")
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--model-name", default="hfl/chinese-macbert-base")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gold-weight", type=float, default=1.0)
    parser.add_argument("--silver-weight", type=float, default=0.4)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def write_report_bundle(
    output_dir: Path,
    *,
    config: dict[str, Any],
    dataset_summary: dict[str, Any],
    thresholds: dict[str, float] | None,
    metrics_by_split: dict[str, Any] | None,
    error_rows: dict[str, list[dict[str, Any]]] | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "dataset_summary.json").write_text(json.dumps(dataset_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if thresholds is not None:
        (output_dir / "thresholds.json").write_text(json.dumps(thresholds, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if metrics_by_split is not None:
        (output_dir / "metrics.json").write_text(json.dumps(metrics_by_split, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if error_rows is not None:
        for split, rows in error_rows.items():
            (output_dir / f"{split}_errors.jsonl").write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
                encoding="utf-8",
            )
    (output_dir / "README.md").write_text(
        build_report_readme(
            config=config,
            dataset_summary=dataset_summary,
            thresholds=thresholds,
            metrics_by_split=metrics_by_split,
        ),
        encoding="utf-8",
    )


def build_report_readme(
    *,
    config: dict[str, Any],
    dataset_summary: dict[str, Any],
    thresholds: dict[str, float] | None,
    metrics_by_split: dict[str, Any] | None,
) -> str:
    lines = [
        "# Multi-Signal SFT Baseline Run",
        "",
        "## Config",
        "",
        "```json",
        json.dumps(config, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Dataset Summary",
        "",
        "```json",
        json.dumps(dataset_summary, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    if thresholds is not None:
        lines.extend(
            [
                "## Thresholds",
                "",
                "```json",
                json.dumps(thresholds, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    if metrics_by_split is not None:
        lines.extend(
            [
                "## Metrics",
                "",
                "```json",
                json.dumps(metrics_by_split, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## Status",
                "",
                "- Dry run only. No training or evaluation metrics were produced.",
                "",
            ]
        )
    return "\n".join(lines)


def run_training(bundle: dict[str, Any], args: argparse.Namespace) -> tuple[dict[str, float], dict[str, Any], dict[str, list[dict[str, Any]]]]:
    deps = _import_training_dependencies()
    torch = deps["torch"]
    set_seed(args.seed, torch=torch)

    tokenizer = deps["AutoTokenizer"].from_pretrained(args.model_name)
    model = deps["AutoModelForSequenceClassification"].from_pretrained(
        args.model_name,
        num_labels=len(bundle["label_names"]),
        problem_type="multi_label_classification",
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    train_loader = build_dataloader(
        bundle["splits"]["train"],
        tokenizer=tokenizer,
        batch_size=args.batch_size,
        max_length=args.max_length,
        shuffle=True,
        torch=torch,
        sample_weights={"gold": args.gold_weight, "silver": args.silver_weight},
    )
    dev_loader = build_dataloader(
        bundle["splits"]["dev"],
        tokenizer=tokenizer,
        batch_size=args.batch_size,
        max_length=args.max_length,
        shuffle=False,
        torch=torch,
    )
    calibration_loader = build_dataloader(
        bundle["splits"]["calibration"],
        tokenizer=tokenizer,
        batch_size=args.batch_size,
        max_length=args.max_length,
        shuffle=False,
        torch=torch,
    )
    heldout_loader = build_dataloader(
        bundle["splits"]["heldout"],
        tokenizer=tokenizer,
        batch_size=args.batch_size,
        max_length=args.max_length,
        shuffle=False,
        torch=torch,
    )

    optimizer = deps["AdamW"](model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    total_steps = max(1, len(train_loader) * args.epochs)
    scheduler = deps["get_linear_schedule_with_warmup"](
        optimizer,
        num_warmup_steps=int(total_steps * args.warmup_ratio),
        num_training_steps=total_steps,
    )

    best_state: dict[str, Any] | None = None
    best_score = -math.inf
    history: list[dict[str, Any]] = []
    half_thresholds = [0.5] * len(bundle["label_names"])

    for epoch in range(args.epochs):
        train_loss = train_one_epoch(model=model, loader=train_loader, optimizer=optimizer, scheduler=scheduler, device=device, torch=torch)
        dev_predictions = predict_probabilities(model=model, loader=dev_loader, device=device, torch=torch)
        dev_pred_binary = apply_thresholds(dev_predictions.probabilities, half_thresholds)
        dev_metrics = compute_multilabel_metrics(gold=dev_predictions.gold, pred=dev_pred_binary, label_names=bundle["label_names"])
        history.append({"epoch": epoch + 1, "train_loss": round(train_loss, 6), "dev_micro_f1@0.5": dev_metrics["micro"]["f1"]})
        score = dev_metrics["micro"]["f1"]
        if score > best_score:
            best_score = score
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    predictions_by_split = {
        "train": predict_probabilities(model=model, loader=train_loader, device=device, torch=torch),
        "dev": predict_probabilities(model=model, loader=dev_loader, device=device, torch=torch),
        "calibration": predict_probabilities(model=model, loader=calibration_loader, device=device, torch=torch),
        "heldout": predict_probabilities(model=model, loader=heldout_loader, device=device, torch=torch),
    }
    thresholds = choose_thresholds(
        probabilities=predictions_by_split["calibration"].probabilities,
        gold=predictions_by_split["calibration"].gold,
        label_names=bundle["label_names"],
    )
    threshold_list = [thresholds[label] for label in bundle["label_names"]]

    metrics_by_split: dict[str, Any] = {"history": history}
    error_rows: dict[str, list[dict[str, Any]]] = {}
    for split, predictions in predictions_by_split.items():
        pred_binary = apply_thresholds(predictions.probabilities, threshold_list)
        metrics_by_split[split] = compute_multilabel_metrics(gold=predictions.gold, pred=pred_binary, label_names=bundle["label_names"])
        error_rows[split] = build_error_rows(
            bundle["splits"][split],
            probabilities=predictions.probabilities,
            pred=pred_binary,
            label_names=bundle["label_names"],
        )

    model_dir = args.output_dir / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(model_dir)
    tokenizer.save_pretrained(model_dir)
    return thresholds, metrics_by_split, error_rows


def build_dataloader(
    examples: list[MultiLabelExample],
    *,
    tokenizer: Any,
    batch_size: int,
    max_length: int,
    shuffle: bool,
    torch: Any,
    sample_weights: dict[str, float] | None = None,
) -> Any:
    dataset = TokenizedDataset(
        examples=examples,
        tokenizer=tokenizer,
        max_length=max_length,
        torch=torch,
        sample_weights=sample_weights,
    )
    return torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


class TokenizedDataset:
    def __init__(
        self,
        *,
        examples: list[MultiLabelExample],
        tokenizer: Any,
        max_length: int,
        torch: Any,
        sample_weights: dict[str, float] | None = None,
    ) -> None:
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.torch = torch
        self.sample_weights = sample_weights or {}

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> dict[str, Any]:
        example = self.examples[index]
        encoded = self.tokenizer(
            example.text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        return {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "labels": self.torch.tensor(example.labels, dtype=self.torch.float32),
            "sample_weight": self.torch.tensor(
                float(self.sample_weights.get(example.label_tier, 1.0)),
                dtype=self.torch.float32,
            ),
        }


def train_one_epoch(*, model: Any, loader: Any, optimizer: Any, scheduler: Any, device: Any, torch: Any) -> float:
    model.train()
    total_loss = 0.0
    total_batches = 0
    loss_fn = torch.nn.BCEWithLogitsLoss(reduction="none")
    for batch in loader:
        optimizer.zero_grad()
        labels = batch["labels"].to(device)
        sample_weight = batch["sample_weight"].to(device)
        moved = {
            "input_ids": batch["input_ids"].to(device),
            "attention_mask": batch["attention_mask"].to(device),
        }
        output = model(**moved)
        unreduced_loss = loss_fn(output.logits, labels)
        weighted_loss = unreduced_loss.mean(dim=1) * sample_weight
        loss = weighted_loss.mean()
        loss.backward()
        optimizer.step()
        scheduler.step()
        total_loss += float(loss.detach().cpu().item())
        total_batches += 1
    return total_loss / total_batches if total_batches else 0.0


def predict_probabilities(*, model: Any, loader: Any, device: Any, torch: Any) -> SplitPredictions:
    model.eval()
    probabilities: list[list[float]] = []
    gold: list[list[int]] = []
    sigmoid = torch.nn.Sigmoid()
    with torch.no_grad():
        for batch in loader:
            labels = batch["labels"]
            moved = {
                "input_ids": batch["input_ids"].to(device),
                "attention_mask": batch["attention_mask"].to(device),
            }
            output = model(**moved)
            probs = sigmoid(output.logits).detach().cpu().tolist()
            probabilities.extend([[float(value) for value in row] for row in probs])
            gold.extend([[int(value) for value in row] for row in labels.tolist()])
    return SplitPredictions(probabilities=probabilities, gold=gold)


def build_error_rows(
    examples: list[MultiLabelExample],
    *,
    probabilities: list[list[float]],
    pred: list[list[int]],
    label_names: list[str],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for example, probs, pred_row in zip(examples, probabilities, pred):
        gold_labels = [label for label, active in zip(label_names, example.labels) if active]
        pred_labels = [label for label, active in zip(label_names, pred_row) if active]
        if gold_labels == pred_labels:
            continue
        errors.append(
            {
                "id": example.id,
                "text": example.text,
                "gold_labels": gold_labels,
                "pred_labels": pred_labels,
                "missing_labels": sorted(set(gold_labels) - set(pred_labels)),
                "extra_labels": sorted(set(pred_labels) - set(gold_labels)),
                "probabilities": {label: round(float(score), 6) for label, score in zip(label_names, probs)},
                "source_dataset": example.source_dataset,
                "label_tier": example.label_tier,
            }
        )
    return errors


def set_seed(seed: int, *, torch: Any | None = None) -> None:
    random.seed(seed)
    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)


def _import_training_dependencies() -> dict[str, Any]:
    try:
        import torch
        from torch.optim import AdamW
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
    except ImportError as exc:  # pragma: no cover - dependency gate
        raise RuntimeError(
            "Training dependencies are missing. Install `torch` and `transformers` before running without --dry-run."
        ) from exc
    return {
        "torch": torch,
        "AdamW": AdamW,
        "AutoModelForSequenceClassification": AutoModelForSequenceClassification,
        "AutoTokenizer": AutoTokenizer,
        "get_linear_schedule_with_warmup": get_linear_schedule_with_warmup,
    }


def main() -> int:
    args = parse_args()
    bundle = load_multilabel_bundle(args.bundle_dir)
    dataset_summary = summarize_bundle(bundle)
    config = {
        "task_name": bundle["task_name"],
        "bundle_dir": str(args.bundle_dir),
        "output_dir": str(args.output_dir),
        "model_name": args.model_name,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "max_length": args.max_length,
        "weight_decay": args.weight_decay,
        "warmup_ratio": args.warmup_ratio,
        "seed": args.seed,
        "gold_weight": args.gold_weight,
        "silver_weight": args.silver_weight,
        "dry_run": args.dry_run,
        "label_group": bundle.get("label_group", "boundary_signals_v1"),
        "include_history": bundle.get("include_history", False),
    }

    thresholds: dict[str, float] | None = None
    metrics_by_split: dict[str, Any] | None = None
    error_rows: dict[str, list[dict[str, Any]]] | None = None
    if not args.dry_run:
        thresholds, metrics_by_split, error_rows = run_training(bundle, args)

    write_report_bundle(
        args.output_dir,
        config=config,
        dataset_summary=dataset_summary,
        thresholds=thresholds,
        metrics_by_split=metrics_by_split,
        error_rows=error_rows,
    )
    print(
        json.dumps(
            {
                "task_name": bundle["task_name"],
                "output_dir": str(args.output_dir),
                "dry_run": args.dry_run,
                "dataset_summary": dataset_summary,
                "thresholds": thresholds,
                "metrics": metrics_by_split,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
