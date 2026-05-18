# Multi-Signal SFT Baseline Run

## Config

```json
{
  "task_name": "required_signals_multilabel",
  "bundle_dir": "/tmp/intent_sft_multisignal_bundle_v2",
  "output_dir": "/Users/genius/Developer/Ai_Project/Skill-First-Hybrid-RAG/evaluation/intent/reports/multisignal_sft/macbert_base_20260517_v1",
  "model_name": "hfl/chinese-macbert-base",
  "epochs": 3,
  "batch_size": 8,
  "learning_rate": 2e-05,
  "max_length": 256,
  "weight_decay": 0.01,
  "warmup_ratio": 0.1,
  "seed": 42,
  "gold_weight": 1.0,
  "silver_weight": 0.4,
  "dry_run": false,
  "label_group": "boundary_signals_v1",
  "include_history": false
}
```

## Dataset Summary

```json
{
  "train": {
    "rows": 1358,
    "active_signal_counts": {
      "soft_doubt": 56,
      "follow_up": 329,
      "needs_clarification": 230,
      "ask_source": 126,
      "multi_question": 316,
      "complex": 153
    }
  },
  "dev": {
    "rows": 24,
    "active_signal_counts": {
      "soft_doubt": 4,
      "follow_up": 4,
      "needs_clarification": 4,
      "ask_source": 4,
      "multi_question": 4,
      "complex": 8
    }
  },
  "calibration": {
    "rows": 10,
    "active_signal_counts": {
      "soft_doubt": 5,
      "follow_up": 0,
      "needs_clarification": 0,
      "ask_source": 0,
      "multi_question": 0,
      "complex": 0
    }
  },
  "heldout": {
    "rows": 30,
    "active_signal_counts": {
      "soft_doubt": 5,
      "follow_up": 5,
      "needs_clarification": 5,
      "ask_source": 5,
      "multi_question": 5,
      "complex": 5
    }
  }
}
```

## Thresholds

```json
{
  "soft_doubt": 0.1,
  "follow_up": 0.5,
  "needs_clarification": 0.5,
  "ask_source": 0.5,
  "multi_question": 0.5,
  "complex": 0.5
}
```

## Metrics

```json
{
  "history": [
    {
      "epoch": 1,
      "train_loss": 0.16783,
      "dev_micro_f1@0.5": 0.444444
    },
    {
      "epoch": 2,
      "train_loss": 0.097812,
      "dev_micro_f1@0.5": 0.634146
    },
    {
      "epoch": 3,
      "train_loss": 0.078193,
      "dev_micro_f1@0.5": 0.651163
    }
  ],
  "train": {
    "rows": 1358,
    "per_signal": {
      "soft_doubt": {
        "precision": 0.395683,
        "recall": 0.982143,
        "f1": 0.564103,
        "support": {
          "positive": 56,
          "negative": 1302
        },
        "tp": 55,
        "fp": 84,
        "fn": 1,
        "tn": 1218
      },
      "follow_up": {
        "precision": 0.767507,
        "recall": 0.832827,
        "f1": 0.798834,
        "support": {
          "positive": 329,
          "negative": 1029
        },
        "tp": 274,
        "fp": 83,
        "fn": 55,
        "tn": 946
      },
      "needs_clarification": {
        "precision": 1.0,
        "recall": 0.43913,
        "f1": 0.610272,
        "support": {
          "positive": 230,
          "negative": 1128
        },
        "tp": 101,
        "fp": 0,
        "fn": 129,
        "tn": 1128
      },
      "ask_source": {
        "precision": 0.973684,
        "recall": 0.880952,
        "f1": 0.925,
        "support": {
          "positive": 126,
          "negative": 1232
        },
        "tp": 111,
        "fp": 3,
        "fn": 15,
        "tn": 1229
      },
      "multi_question": {
        "precision": 0.97411,
        "recall": 0.952532,
        "f1": 0.9632,
        "support": {
          "positive": 316,
          "negative": 1042
        },
        "tp": 301,
        "fp": 8,
        "fn": 15,
        "tn": 1034
      },
      "complex": {
        "precision": 0.971831,
        "recall": 0.45098,
        "f1": 0.616071,
        "support": {
          "positive": 153,
          "negative": 1205
        },
        "tp": 69,
        "fp": 2,
        "fn": 84,
        "tn": 1203
      }
    },
    "micro": {
      "precision": 0.835014,
      "recall": 0.752893,
      "f1": 0.79183,
      "tp": 911,
      "fp": 180,
      "fn": 299
    },
    "macro": {
      "f1": 0.746247
    },
    "exact_match_accuracy": 0.737113
  },
  "dev": {
    "rows": 24,
    "per_signal": {
      "soft_doubt": {
        "precision": 0.8,
        "recall": 1.0,
        "f1": 0.888889,
        "support": {
          "positive": 4,
          "negative": 20
        },
        "tp": 4,
        "fp": 1,
        "fn": 0,
        "tn": 19
      },
      "follow_up": {
        "precision": 0.8,
        "recall": 1.0,
        "f1": 0.888889,
        "support": {
          "positive": 4,
          "negative": 20
        },
        "tp": 4,
        "fp": 1,
        "fn": 0,
        "tn": 19
      },
      "needs_clarification": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": {
          "positive": 4,
          "negative": 20
        },
        "tp": 0,
        "fp": 0,
        "fn": 4,
        "tn": 20
      },
      "ask_source": {
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "support": {
          "positive": 4,
          "negative": 20
        },
        "tp": 4,
        "fp": 0,
        "fn": 0,
        "tn": 20
      },
      "multi_question": {
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "support": {
          "positive": 4,
          "negative": 20
        },
        "tp": 4,
        "fp": 0,
        "fn": 0,
        "tn": 20
      },
      "complex": {
        "precision": 1.0,
        "recall": 0.125,
        "f1": 0.222222,
        "support": {
          "positive": 8,
          "negative": 16
        },
        "tp": 1,
        "fp": 0,
        "fn": 7,
        "tn": 16
      }
    },
    "micro": {
      "precision": 0.894737,
      "recall": 0.607143,
      "f1": 0.723404,
      "tp": 17,
      "fp": 2,
      "fn": 11
    },
    "macro": {
      "f1": 0.666667
    },
    "exact_match_accuracy": 0.5
  },
  "calibration": {
    "rows": 10,
    "per_signal": {
      "soft_doubt": {
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "support": {
          "positive": 5,
          "negative": 5
        },
        "tp": 5,
        "fp": 0,
        "fn": 0,
        "tn": 5
      },
      "follow_up": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": {
          "positive": 0,
          "negative": 10
        },
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "tn": 10
      },
      "needs_clarification": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": {
          "positive": 0,
          "negative": 10
        },
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "tn": 10
      },
      "ask_source": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": {
          "positive": 0,
          "negative": 10
        },
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "tn": 10
      },
      "multi_question": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": {
          "positive": 0,
          "negative": 10
        },
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "tn": 10
      },
      "complex": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": {
          "positive": 0,
          "negative": 10
        },
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "tn": 10
      }
    },
    "micro": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "tp": 5,
      "fp": 0,
      "fn": 0
    },
    "macro": {
      "f1": 0.166667
    },
    "exact_match_accuracy": 1.0
  },
  "heldout": {
    "rows": 30,
    "per_signal": {
      "soft_doubt": {
        "precision": 0.8,
        "recall": 0.8,
        "f1": 0.8,
        "support": {
          "positive": 5,
          "negative": 25
        },
        "tp": 4,
        "fp": 1,
        "fn": 1,
        "tn": 24
      },
      "follow_up": {
        "precision": 0.8,
        "recall": 0.8,
        "f1": 0.8,
        "support": {
          "positive": 5,
          "negative": 25
        },
        "tp": 4,
        "fp": 1,
        "fn": 1,
        "tn": 24
      },
      "needs_clarification": {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "support": {
          "positive": 5,
          "negative": 25
        },
        "tp": 0,
        "fp": 0,
        "fn": 5,
        "tn": 25
      },
      "ask_source": {
        "precision": 1.0,
        "recall": 0.8,
        "f1": 0.888889,
        "support": {
          "positive": 5,
          "negative": 25
        },
        "tp": 4,
        "fp": 0,
        "fn": 1,
        "tn": 25
      },
      "multi_question": {
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "support": {
          "positive": 5,
          "negative": 25
        },
        "tp": 5,
        "fp": 0,
        "fn": 0,
        "tn": 25
      },
      "complex": {
        "precision": 1.0,
        "recall": 0.2,
        "f1": 0.333333,
        "support": {
          "positive": 5,
          "negative": 25
        },
        "tp": 1,
        "fp": 0,
        "fn": 4,
        "tn": 25
      }
    },
    "micro": {
      "precision": 0.9,
      "recall": 0.6,
      "f1": 0.72,
      "tp": 18,
      "fp": 2,
      "fn": 12
    },
    "macro": {
      "f1": 0.637037
    },
    "exact_match_accuracy": 0.566667
  }
}
```
