from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Example:
    id: str
    text: str
    label: int
    label_name: str
    source_dataset: str
    label_tier: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and evaluate the v1 MacBERT baseline for intent tasks.")
    parser.add_argument("task_dir", type=Path, help="Task directory such as exports/macbert_baseline_v1/soft_doubt")
    parser.add_argument("output_dir", type=Path, help="Directory to write reports and model artifacts")
    parser.add_argument("--model-name", default="hfl/chinese-macbert-base")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only validate the dataset bundle and emit summary reports without importing training dependencies.",
    )
    return parser.parse_args()


def load_task_bundle(task_dir: Path) -> dict[str, Any]:
    label_map_path = task_dir / "label_map.json"
    if not label_map_path.exists():
        raise FileNotFoundError(f"Missing label map: {label_map_path}")

    label_map = json.loads(label_map_path.read_text(encoding="utf-8"))
    splits: dict[str, list[Example]] = {}
    for split in ("train", "dev", "heldout"):
        split_path = task_dir / f"{split}.jsonl"
        if not split_path.exists():
            raise FileNotFoundError(f"Missing split file: {split_path}")
        splits[split] = load_examples(split_path)

    task_name = task_dir.name
    return {
        "task_name": task_name,
        "task_dir": task_dir,
        "label_map": label_map,
        "label_names": [label for label, _ in sorted(label_map.items(), key=lambda item: item[1])],
        "splits": splits,
    }


def load_examples(path: Path) -> list[Example]:
    examples: list[Example] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        examples.append(
            Example(
                id=row["id"],
                text=row["text"],
                label=int(row["label"]),
                label_name=row["label_name"],
                source_dataset=row.get("source_dataset", ""),
                label_tier=row.get("label_tier", ""),
            )
        )
    return examples


def summarize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    split_summary: dict[str, Any] = {}
    for split, rows in bundle["splits"].items():
        label_counter = Counter(row.label_name for row in rows)
        split_summary[split] = {
            "rows": len(rows),
            "labels": dict(sorted(label_counter.items())),
        }
    return {
        "task_name": bundle["task_name"],
        "task_dir": str(bundle["task_dir"]),
        "label_map": bundle["label_map"],
        "splits": split_summary,
    }


def compute_metrics(*, task_name: str, label_names: list[str], gold: list[int], pred: list[int]) -> dict[str, Any]:
    if len(gold) != len(pred):
        raise ValueError("gold and pred must have the same length")
    if _looks_like_binary_task(task_name=task_name, label_names=label_names):
        return compute_binary_metrics(gold=gold, pred=pred, positive_label=1, label_names=label_names)
    return compute_multiclass_metrics(gold=gold, pred=pred, label_names=label_names)


def compute_binary_metrics(*, gold: list[int], pred: list[int], positive_label: int, label_names: list[str]) -> dict[str, Any]:
    tp = sum(1 for g, p in zip(gold, pred) if g == positive_label and p == positive_label)
    fp = sum(1 for g, p in zip(gold, pred) if g != positive_label and p == positive_label)
    fn = sum(1 for g, p in zip(gold, pred) if g == positive_label and p != positive_label)
    tn = sum(1 for g, p in zip(gold, pred) if g != positive_label and p != positive_label)
    total = len(gold)
    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)
    f1 = safe_divide(2 * precision * recall, precision + recall)
    accuracy = safe_divide(tp + tn, total)
    return {
        "rows": total,
        "accuracy": round_metric(accuracy),
        "precision": round_metric(precision),
        "recall": round_metric(recall),
        "f1": round_metric(f1),
        "support": {
            "negative": sum(1 for g in gold if g != positive_label),
            "positive": sum(1 for g in gold if g == positive_label),
        },
        "confusion": {
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "tp": tp,
        },
        "labels": label_names,
    }


def compute_multiclass_metrics(*, gold: list[int], pred: list[int], label_names: list[str]) -> dict[str, Any]:
    total = len(gold)
    correct = sum(1 for g, p in zip(gold, pred) if g == p)
    per_class: dict[str, Any] = {}
    f1_values: list[float] = []
    confusion = [[0 for _ in label_names] for _ in label_names]

    for g, p in zip(gold, pred):
        confusion[g][p] += 1

    for label_id, label_name in enumerate(label_names):
        tp = sum(1 for g, p in zip(gold, pred) if g == label_id and p == label_id)
        fp = sum(1 for g, p in zip(gold, pred) if g != label_id and p == label_id)
        fn = sum(1 for g, p in zip(gold, pred) if g == label_id and p != label_id)
        precision = safe_divide(tp, tp + fp)
        recall = safe_divide(tp, tp + fn)
        f1 = safe_divide(2 * precision * recall, precision + recall)
        f1_values.append(f1)
        per_class[label_name] = {
            "precision": round_metric(precision),
            "recall": round_metric(recall),
            "f1": round_metric(f1),
            "support": sum(1 for g in gold if g == label_id),
        }

    return {
        "rows": total,
        "accuracy": round_metric(safe_divide(correct, total)),
        "macro_f1": round_metric(sum(f1_values) / len(label_names) if label_names else 0.0),
        "per_class": per_class,
        "confusion_matrix": {
            "labels": label_names,
            "matrix": confusion,
        },
    }


def build_error_rows(examples: list[Example], pred: list[int], label_names: list[str]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for example, predicted_label in zip(examples, pred):
        if example.label == predicted_label:
            continue
        errors.append(
            {
                "id": example.id,
                "text": example.text,
                "gold_label": example.label_name,
                "pred_label": label_names[predicted_label],
                "source_dataset": example.source_dataset,
                "label_tier": example.label_tier,
            }
        )
    return errors


def write_report_bundle(
    output_dir: Path,
    *,
    config: dict[str, Any],
    dataset_summary: dict[str, Any],
    metrics_by_split: dict[str, Any] | None,
    errors: list[dict[str, Any]] | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "dataset_summary.json").write_text(
        json.dumps(dataset_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if metrics_by_split is not None:
        (output_dir / "metrics.json").write_text(
            json.dumps(metrics_by_split, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if errors is not None:
        (output_dir / "heldout_errors.jsonl").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in errors) + ("\n" if errors else ""),
            encoding="utf-8",
        )
    (output_dir / "README.md").write_text(
        build_report_readme(
            config=config,
            dataset_summary=dataset_summary,
            metrics_by_split=metrics_by_split,
            error_count=len(errors or []),
        ),
        encoding="utf-8",
    )


def build_report_readme(
    *,
    config: dict[str, Any],
    dataset_summary: dict[str, Any],
    metrics_by_split: dict[str, Any] | None,
    error_count: int,
) -> str:
    lines = [
        f"# MacBERT Baseline Run: {dataset_summary['task_name']}",
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
        json.dumps(dataset_summary["splits"], ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    if metrics_by_split is not None:
        lines.extend(
            [
                "## Metrics",
                "",
                "```json",
                json.dumps(metrics_by_split, ensure_ascii=False, indent=2),
                "```",
                "",
                f"## Heldout Errors",
                "",
                f"- rows: `{error_count}`",
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


def run_training(bundle: dict[str, Any], args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    transformers = _import_training_dependencies()
    torch = transformers["torch"]
    set_seed(args.seed, torch=torch)

    tokenizer = transformers["AutoTokenizer"].from_pretrained(args.model_name)
    model = transformers["AutoModelForSequenceClassification"].from_pretrained(
        args.model_name,
        num_labels=len(bundle["label_names"]),
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    train_loader = build_dataloader(
        examples=bundle["splits"]["train"],
        tokenizer=tokenizer,
        batch_size=args.batch_size,
        max_length=args.max_length,
        shuffle=True,
        torch=torch,
    )
    dev_loader = build_dataloader(
        examples=bundle["splits"]["dev"],
        tokenizer=tokenizer,
        batch_size=args.batch_size,
        max_length=args.max_length,
        shuffle=False,
        torch=torch,
    )
    heldout_loader = build_dataloader(
        examples=bundle["splits"]["heldout"],
        tokenizer=tokenizer,
        batch_size=args.batch_size,
        max_length=args.max_length,
        shuffle=False,
        torch=torch,
    )

    optimizer = transformers["AdamW"](model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    total_steps = max(1, len(train_loader) * args.epochs)
    warmup_steps = int(total_steps * args.warmup_ratio)
    scheduler = transformers["get_linear_schedule_with_warmup"](
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    best_state: dict[str, Any] | None = None
    best_score = -math.inf
    history: list[dict[str, Any]] = []

    for epoch in range(args.epochs):
        train_loss = train_one_epoch(model=model, loader=train_loader, optimizer=optimizer, scheduler=scheduler, device=device, torch=torch)
        dev_pred, dev_gold = predict(model=model, loader=dev_loader, device=device, torch=torch)
        dev_metrics = compute_metrics(
            task_name=bundle["task_name"],
            label_names=bundle["label_names"],
            gold=dev_gold,
            pred=dev_pred,
        )
        score = dev_metrics["f1"] if bundle["task_name"] == "soft_doubt" else dev_metrics["macro_f1"]
        history.append({"epoch": epoch + 1, "train_loss": round_metric(train_loss), "dev_metrics": dev_metrics})
        if score > best_score:
            best_score = score
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    metrics_by_split: dict[str, Any] = {"history": history}
    heldout_errors: list[dict[str, Any]] = []
    for split, loader in (("train", train_loader), ("dev", dev_loader), ("heldout", heldout_loader)):
        pred, gold = predict(model=model, loader=loader, device=device, torch=torch)
        split_metrics = compute_metrics(
            task_name=bundle["task_name"],
            label_names=bundle["label_names"],
            gold=gold,
            pred=pred,
        )
        metrics_by_split[split] = split_metrics
        if split == "heldout":
            heldout_errors = build_error_rows(bundle["splits"]["heldout"], pred, bundle["label_names"])

    model_output_dir = args.output_dir / "model"
    model_output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(model_output_dir)
    tokenizer.save_pretrained(model_output_dir)

    return metrics_by_split, heldout_errors


def build_dataloader(
    *,
    examples: list[Example],
    tokenizer: Any,
    batch_size: int,
    max_length: int,
    shuffle: bool,
    torch: Any,
) -> Any:
    dataset = TokenizedDataset(examples=examples, tokenizer=tokenizer, max_length=max_length, torch=torch)
    return torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


class TokenizedDataset:
    def __init__(self, *, examples: list[Example], tokenizer: Any, max_length: int, torch: Any) -> None:
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.torch = torch

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
            "labels": self.torch.tensor(example.label, dtype=self.torch.long),
        }


def train_one_epoch(*, model: Any, loader: Any, optimizer: Any, scheduler: Any, device: Any, torch: Any) -> float:
    model.train()
    total_loss = 0.0
    total_batches = 0
    for batch in loader:
        optimizer.zero_grad()
        moved = {key: value.to(device) for key, value in batch.items()}
        output = model(**moved)
        loss = output.loss
        loss.backward()
        optimizer.step()
        scheduler.step()
        total_loss += float(loss.detach().cpu().item())
        total_batches += 1
    return total_loss / total_batches if total_batches else 0.0


def predict(*, model: Any, loader: Any, device: Any, torch: Any) -> tuple[list[int], list[int]]:
    model.eval()
    pred: list[int] = []
    gold: list[int] = []
    with torch.no_grad():
        for batch in loader:
            labels = batch["labels"]
            moved = {key: value.to(device) for key, value in batch.items()}
            output = model(**moved)
            logits = output.logits
            pred.extend(int(value) for value in logits.argmax(dim=-1).detach().cpu().tolist())
            gold.extend(int(value) for value in labels.tolist())
    return pred, gold


def set_seed(seed: int, *, torch: Any | None = None) -> None:
    random.seed(seed)
    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)


def _import_training_dependencies() -> dict[str, Any]:
    try:
        import torch
        from transformers import AdamW, AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
    except ImportError as exc:
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


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def round_metric(value: float) -> float:
    return round(value, 6)


def _looks_like_binary_task(*, task_name: str, label_names: list[str]) -> bool:
    return task_name == "soft_doubt" or (len(label_names) == 2 and set(label_names) == {"false", "true"})


def main() -> int:
    args = parse_args()
    bundle = load_task_bundle(args.task_dir)
    dataset_summary = summarize_bundle(bundle)
    config = {
        "task_name": bundle["task_name"],
        "task_dir": str(args.task_dir),
        "output_dir": str(args.output_dir),
        "model_name": args.model_name,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "max_length": args.max_length,
        "weight_decay": args.weight_decay,
        "warmup_ratio": args.warmup_ratio,
        "seed": args.seed,
        "dry_run": args.dry_run,
    }

    metrics_by_split: dict[str, Any] | None = None
    heldout_errors: list[dict[str, Any]] | None = None
    if not args.dry_run:
        metrics_by_split, heldout_errors = run_training(bundle, args)

    write_report_bundle(
        args.output_dir,
        config=config,
        dataset_summary=dataset_summary,
        metrics_by_split=metrics_by_split,
        errors=heldout_errors,
    )
    print(
        json.dumps(
            {
                "task_name": bundle["task_name"],
                "output_dir": str(args.output_dir),
                "dry_run": args.dry_run,
                "dataset_summary": dataset_summary["splits"],
                "metrics": metrics_by_split,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
