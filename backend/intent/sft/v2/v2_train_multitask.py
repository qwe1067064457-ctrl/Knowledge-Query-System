from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[3]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from intent.sft.v2.v2_data import V2Example, load_v2_bundle, summarize_v2_bundle
from intent.sft.v2.v2_eval import (
    apply_multilabel_thresholds,
    choose_multilabel_thresholds,
    compute_multiclass_metrics,
    compute_multilabel_metrics,
)
from intent.sft.v2.v2_label_spaces import MULTICLASS_HEADS, MULTILABEL_HEADS


@dataclass(frozen=True)
class HeadPredictions:
    multiclass_logits: dict[str, list[list[float]]]
    multilabel_probabilities: dict[str, list[list[float]]]
    gold_multiclass: dict[str, list[int]]
    gold_multilabel: dict[str, list[list[int]]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a physically isolated V2 multitask intent SFT baseline.")
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
    parser.add_argument("--threshold-source", choices=("dev", "fixed"), default="dev")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def write_report_bundle(
    output_dir: Path,
    *,
    config: dict[str, Any],
    dataset_summary: dict[str, Any],
    thresholds: dict[str, dict[str, float]] | None,
    metrics_by_split: dict[str, Any] | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "dataset_summary.json").write_text(json.dumps(dataset_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if thresholds is not None:
        (output_dir / "thresholds.json").write_text(json.dumps(thresholds, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if metrics_by_split is not None:
        (output_dir / "metrics.json").write_text(json.dumps(metrics_by_split, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
    thresholds: dict[str, dict[str, float]] | None,
    metrics_by_split: dict[str, Any] | None,
) -> str:
    lines = [
        "# Intent SFT V2 Multitask Run",
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
        lines.extend(["## Thresholds", "", "```json", json.dumps(thresholds, ensure_ascii=False, indent=2), "```", ""])
    if metrics_by_split is not None:
        lines.extend(["## Metrics", "", "```json", json.dumps(metrics_by_split, ensure_ascii=False, indent=2), "```", ""])
    else:
        lines.extend(
            [
                "## Status",
                "",
                "- Dry run only. No training or evaluation metrics were produced.",
                "- Current temporary policy: multilabel thresholds use `dev` because V2 calibration is not frozen yet.",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def run_training(bundle: dict[str, Any], args: argparse.Namespace) -> tuple[dict[str, dict[str, float]], dict[str, Any]]:
    deps = _import_training_dependencies()
    torch = deps["torch"]
    nn = deps["nn"]
    set_seed(args.seed, torch=torch)

    tokenizer = deps["AutoTokenizer"].from_pretrained(args.model_name)
    encoder = deps["AutoModel"].from_pretrained(args.model_name)
    model = V2MultiTaskModel(encoder=encoder, torch=torch, nn=nn)
    device = _select_device(torch)
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
    fixed_thresholds = {head: {label: 0.5 for label in labels} for head, labels in MULTILABEL_HEADS.items()}

    for epoch in range(args.epochs):
        train_loss = train_one_epoch(model=model, loader=train_loader, optimizer=optimizer, scheduler=scheduler, device=device, torch=torch)
        dev_predictions = predict_heads(model=model, loader=dev_loader, device=device, torch=torch)
        dev_metrics = evaluate_predictions(dev_predictions, thresholds=fixed_thresholds)
        score = compute_selection_score(dev_metrics)
        history.append({"epoch": epoch + 1, "train_loss": round(train_loss, 6), "dev_score@fixed": round(score, 6)})
        if score > best_score:
            best_score = score
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    predictions_by_split = {
        "train": predict_heads(model=model, loader=train_loader, device=device, torch=torch),
        "dev": predict_heads(model=model, loader=dev_loader, device=device, torch=torch),
        "heldout": predict_heads(model=model, loader=heldout_loader, device=device, torch=torch),
    }

    thresholds = fixed_thresholds
    if args.threshold_source == "dev":
        thresholds = {
            head: choose_multilabel_thresholds(
                probabilities=predictions_by_split["dev"].multilabel_probabilities[head],
                gold=predictions_by_split["dev"].gold_multilabel[head],
                label_names=list(MULTILABEL_HEADS[head]),
            )
            for head in MULTILABEL_HEADS
        }

    metrics_by_split: dict[str, Any] = {"history": history}
    for split, predictions in predictions_by_split.items():
        metrics_by_split[split] = evaluate_predictions(predictions, thresholds=thresholds)

    model_dir = args.output_dir / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    model.encoder.save_pretrained(model_dir)
    tokenizer.save_pretrained(model_dir)
    torch.save(model.state_dict(), model_dir / "multitask_heads.pt")
    return thresholds, metrics_by_split


class V2MultiTaskModel:
    def __init__(self, *, encoder: Any, torch: Any, nn: Any) -> None:
        self.encoder = encoder
        self.torch = torch
        self.nn = nn
        hidden_size = int(self.encoder.config.hidden_size)
        self.dropout = nn.Dropout(0.1)
        self.multiclass_heads = nn.ModuleDict(
            {head: nn.Linear(hidden_size, len(labels)) for head, labels in MULTICLASS_HEADS.items()}
        )
        self.multilabel_heads = nn.ModuleDict(
            {head: nn.Linear(hidden_size, len(labels)) for head, labels in MULTILABEL_HEADS.items()}
        )

    def parameters(self) -> Any:
        for item in self.encoder.parameters():
            yield item
        for item in self.dropout.parameters():
            yield item
        for item in self.multiclass_heads.parameters():
            yield item
        for item in self.multilabel_heads.parameters():
            yield item

    def state_dict(self) -> dict[str, Any]:
        state = {}
        state.update({f"encoder.{key}": value for key, value in self.encoder.state_dict().items()})
        state.update({f"dropout.{key}": value for key, value in self.dropout.state_dict().items()})
        state.update({f"multiclass_heads.{key}": value for key, value in self.multiclass_heads.state_dict().items()})
        state.update({f"multilabel_heads.{key}": value for key, value in self.multilabel_heads.state_dict().items()})
        return state

    def load_state_dict(self, state_dict: dict[str, Any]) -> None:
        encoder_state = {key.removeprefix("encoder."): value for key, value in state_dict.items() if key.startswith("encoder.")}
        dropout_state = {key.removeprefix("dropout."): value for key, value in state_dict.items() if key.startswith("dropout.")}
        multiclass_state = {
            key.removeprefix("multiclass_heads."): value
            for key, value in state_dict.items()
            if key.startswith("multiclass_heads.")
        }
        multilabel_state = {
            key.removeprefix("multilabel_heads."): value
            for key, value in state_dict.items()
            if key.startswith("multilabel_heads.")
        }
        self.encoder.load_state_dict(encoder_state)
        self.dropout.load_state_dict(dropout_state)
        self.multiclass_heads.load_state_dict(multiclass_state)
        self.multilabel_heads.load_state_dict(multilabel_state)

    def to(self, device: Any) -> None:
        self.encoder.to(device)
        self.dropout.to(device)
        self.multiclass_heads.to(device)
        self.multilabel_heads.to(device)

    def train(self) -> None:
        self.encoder.train()
        self.dropout.train()
        self.multiclass_heads.train()
        self.multilabel_heads.train()

    def eval(self) -> None:
        self.encoder.eval()
        self.dropout.eval()
        self.multiclass_heads.eval()
        self.multilabel_heads.eval()

    def __call__(self, *, input_ids: Any, attention_mask: Any) -> dict[str, dict[str, Any]]:
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled = outputs.pooler_output
        if pooled is None:
            pooled = outputs.last_hidden_state[:, 0]
        pooled = self.dropout(pooled)
        multiclass_logits = {head: layer(pooled) for head, layer in self.multiclass_heads.items()}
        multilabel_logits = {head: layer(pooled) for head, layer in self.multilabel_heads.items()}
        return {
            "multiclass": multiclass_logits,
            "multilabel": multilabel_logits,
        }


class TokenizedDataset:
    def __init__(
        self,
        *,
        examples: list[V2Example],
        tokenizer: Any,
        max_length: int,
        torch: Any,
        sample_weights: dict[str, float] | None = None,
    ) -> None:
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.torch = torch
        self.sample_weights = sample_weights or {"gold": 1.0, "silver": 1.0}

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
            "main_intent": self.torch.tensor(example.main_intent, dtype=self.torch.long),
            "task_complexity": self.torch.tensor(example.task_complexity, dtype=self.torch.long),
            "task_shape": self.torch.tensor(example.task_shape, dtype=self.torch.long),
            "task_topology": self.torch.tensor(example.task_topology, dtype=self.torch.long),
            "modifiers": self.torch.tensor(example.modifiers, dtype=self.torch.float32),
            "context": self.torch.tensor(example.context, dtype=self.torch.float32),
            "safety": self.torch.tensor(example.safety, dtype=self.torch.float32),
            "sample_weight": self.torch.tensor(
                float(self.sample_weights.get(example.label_tier, 1.0)),
                dtype=self.torch.float32,
            ),
        }


def build_dataloader(
    examples: list[V2Example],
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


def train_one_epoch(*, model: V2MultiTaskModel, loader: Any, optimizer: Any, scheduler: Any, device: Any, torch: Any) -> float:
    ce_loss = torch.nn.CrossEntropyLoss(reduction="none")
    bce_loss = torch.nn.BCEWithLogitsLoss(reduction="none")
    model.train()
    total_loss = 0.0
    total_batches = 0

    for batch in loader:
        optimizer.zero_grad()
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        sample_weight = batch["sample_weight"].to(device)

        losses: list[Any] = []
        for head in MULTICLASS_HEADS:
            logits = outputs["multiclass"][head]
            labels = batch[head].to(device)
            per_row = ce_loss(logits, labels)
            losses.append(per_row)
        for head in MULTILABEL_HEADS:
            logits = outputs["multilabel"][head]
            labels = batch[head].to(device)
            per_value = bce_loss(logits, labels)
            per_row = per_value.mean(dim=1)
            losses.append(per_row)

        stacked = torch.stack(losses, dim=1).mean(dim=1)
        loss = (stacked * sample_weight).mean()
        loss.backward()
        optimizer.step()
        scheduler.step()
        total_loss += float(loss.detach().cpu().item())
        total_batches += 1

    return total_loss / max(total_batches, 1)


def predict_heads(*, model: V2MultiTaskModel, loader: Any, device: Any, torch: Any) -> HeadPredictions:
    model.eval()
    softmax = torch.nn.functional.softmax
    sigmoid = torch.sigmoid
    multiclass_logits: dict[str, list[list[float]]] = {head: [] for head in MULTICLASS_HEADS}
    multilabel_probabilities: dict[str, list[list[float]]] = {head: [] for head in MULTILABEL_HEADS}
    gold_multiclass: dict[str, list[int]] = {head: [] for head in MULTICLASS_HEADS}
    gold_multilabel: dict[str, list[list[int]]] = {head: [] for head in MULTILABEL_HEADS}

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            for head in MULTICLASS_HEADS:
                logits = outputs["multiclass"][head]
                multiclass_logits[head].extend(logits.detach().cpu().tolist())
                gold_multiclass[head].extend(batch[head].tolist())
            for head in MULTILABEL_HEADS:
                probs = sigmoid(outputs["multilabel"][head])
                multilabel_probabilities[head].extend(probs.detach().cpu().tolist())
                gold_multilabel[head].extend(batch[head].int().tolist())
    return HeadPredictions(
        multiclass_logits=multiclass_logits,
        multilabel_probabilities=multilabel_probabilities,
        gold_multiclass=gold_multiclass,
        gold_multilabel=gold_multilabel,
    )


def evaluate_predictions(predictions: HeadPredictions, *, thresholds: dict[str, dict[str, float]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for head, labels in MULTICLASS_HEADS.items():
        pred_indices = [max(range(len(row)), key=lambda idx: row[idx]) for row in predictions.multiclass_logits[head]]
        result[head] = compute_multiclass_metrics(
            gold=predictions.gold_multiclass[head],
            pred=pred_indices,
            label_names=list(labels),
        )
    for head, labels in MULTILABEL_HEADS.items():
        threshold_list = [thresholds[head][label] for label in labels]
        pred_binary = apply_multilabel_thresholds(predictions.multilabel_probabilities[head], threshold_list)
        result[head] = compute_multilabel_metrics(
            gold=predictions.gold_multilabel[head],
            pred=pred_binary,
            label_names=list(labels),
        )
    result["selection_score"] = round(compute_selection_score(result), 6)
    return result


def compute_selection_score(metrics: dict[str, Any]) -> float:
    values: list[float] = []
    for head in MULTICLASS_HEADS:
        values.append(float(metrics[head]["macro_f1"]))
    for head in MULTILABEL_HEADS:
        active_scores = [
            signal_metrics["f1"]
            for signal_metrics in metrics[head]["per_signal"].values()
            if signal_metrics["support"]["positive"] > 0
        ]
        if active_scores:
            values.append(sum(active_scores) / len(active_scores))
    return sum(values) / len(values) if values else 0.0


def set_seed(seed: int, *, torch: Any | None = None) -> None:
    random.seed(seed)
    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)


def _select_device(torch: Any) -> Any:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _import_training_dependencies() -> dict[str, Any]:
    try:
        import torch
        import torch.nn as nn
        from torch.optim import AdamW
        from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Training dependencies are missing. Install `torch` and `transformers`.") from exc
    return {
        "torch": torch,
        "nn": nn,
        "AdamW": AdamW,
        "AutoModel": AutoModel,
        "AutoTokenizer": AutoTokenizer,
        "get_linear_schedule_with_warmup": get_linear_schedule_with_warmup,
    }


def main() -> int:
    args = parse_args()
    bundle = load_v2_bundle(args.bundle_dir)
    dataset_summary = summarize_v2_bundle(bundle)
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
        "threshold_source": args.threshold_source,
        "dry_run": args.dry_run,
        "include_history": bundle.get("include_history", False),
    }

    thresholds: dict[str, dict[str, float]] | None = None
    metrics_by_split: dict[str, Any] | None = None
    if not args.dry_run:
        thresholds, metrics_by_split = run_training(bundle, args)
    write_report_bundle(
        args.output_dir,
        config=config,
        dataset_summary=dataset_summary,
        thresholds=thresholds,
        metrics_by_split=metrics_by_split,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
