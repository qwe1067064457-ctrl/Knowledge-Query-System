# Multi-Signal SFT Baseline Run

## Config

```json
{
  "task_name": "required_signals_multilabel",
  "bundle_dir": "/tmp/intent_sft_multisignal_bundle_v3",
  "output_dir": "/Users/genius/Developer/Ai_Project/Skill-First-Hybrid-RAG/evaluation/intent/reports/multisignal_sft/macbert_base_20260518_v2",
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
    "rows": 1416,
    "active_signal_counts": {
      "soft_doubt": 56,
      "follow_up": 341,
      "needs_clarification": 250,
      "ask_source": 132,
      "multi_question": 319,
      "complex": 163
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
    "rows": 49,
    "active_signal_counts": {
      "soft_doubt": 5,
      "follow_up": 7,
      "needs_clarification": 6,
      "ask_source": 10,
      "multi_question": 6,
      "complex": 7
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
  "soft_doubt": 0.45,
  "follow_up": 0.5,
  "needs_clarification": 0.45,
  "ask_source": 0.5,
  "multi_question": 0.5,
  "complex": 0.3
}
```

## Metrics

```json
{
  "history": [
    {
      "epoch": 1,
      "train_loss": 0.171883,
      "dev_micro_f1@0.5": 0.526316
    },
    {
      "epoch": 2,
      "train_loss": 0.101323,
      "dev_micro_f1@0.5": 0.791667
    },
    {
      "epoch": 3,
      "train_loss": 0.081286,
      "dev_micro_f1@0.5": 0.808511
    }
  ],
  "train": {
    "rows": 1416,
    "per_signal": {
      "soft_doubt": {
        "precision": 1.0,
        "recall": 0.696429,
        "f1": 0.821053,
        "support": {
          "positive": 56,
          "negative": 1360
        },
        "tp": 39,
        "fp": 0,
        "fn": 17,
        "tn": 1360
      },
      "follow_up": {
        "precision": 0.754054,
        "recall": 0.818182,
        "f1": 0.78481,
        "support": {
          "positive": 341,
          "negative": 1075
        },
        "tp": 279,
        "fp": 91,
        "fn": 62,
        "tn": 984
      },
      "needs_clarification": {
        "precision": 0.884058,
        "recall": 0.488,
        "f1": 0.628866,
        "support": {
          "positive": 250,
          "negative": 1166
        },
        "tp": 122,
        "fp": 16,
        "fn": 128,
        "tn": 1150
      },
      "ask_source": {
        "precision": 0.991525,
        "recall": 0.886364,
        "f1": 0.936,
        "support": {
          "positive": 132,
          "negative": 1284
        },
        "tp": 117,
        "fp": 1,
        "fn": 15,
        "tn": 1283
      },
      "multi_question": {
        "precision": 0.962733,
        "recall": 0.971787,
        "f1": 0.967239,
        "support": {
          "positive": 319,
          "negative": 1097
        },
        "tp": 310,
        "fp": 12,
        "fn": 9,
        "tn": 1085
      },
      "complex": {
        "precision": 0.850649,
        "recall": 0.803681,
        "f1": 0.826498,
        "support": {
          "positive": 163,
          "negative": 1253
        },
        "tp": 131,
        "fp": 23,
        "fn": 32,
        "tn": 1230
      }
    },
    "micro": {
      "precision": 0.874671,
      "recall": 0.791435,
      "f1": 0.830974,
      "tp": 998,
      "fp": 143,
      "fn": 263
    },
    "macro": {
      "f1": 0.827411
    },
    "exact_match_accuracy": 0.795198
  },
  "dev": {
    "rows": 24,
    "per_signal": {
      "soft_doubt": {
        "precision": 1.0,
        "recall": 0.25,
        "f1": 0.4,
        "support": {
          "positive": 4,
          "negative": 20
        },
        "tp": 1,
        "fp": 0,
        "fn": 3,
        "tn": 20
      },
      "follow_up": {
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
      "needs_clarification": {
        "precision": 1.0,
        "recall": 0.75,
        "f1": 0.857143,
        "support": {
          "positive": 4,
          "negative": 20
        },
        "tp": 3,
        "fp": 0,
        "fn": 1,
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
        "precision": 0.8,
        "recall": 0.5,
        "f1": 0.615385,
        "support": {
          "positive": 8,
          "negative": 16
        },
        "tp": 4,
        "fp": 1,
        "fn": 4,
        "tn": 15
      }
    },
    "micro": {
      "precision": 0.952381,
      "recall": 0.714286,
      "f1": 0.816327,
      "tp": 20,
      "fp": 1,
      "fn": 8
    },
    "macro": {
      "f1": 0.812088
    },
    "exact_match_accuracy": 0.75
  },
  "calibration": {
    "rows": 49,
    "per_signal": {
      "soft_doubt": {
        "precision": 1.0,
        "recall": 0.6,
        "f1": 0.75,
        "support": {
          "positive": 5,
          "negative": 44
        },
        "tp": 3,
        "fp": 0,
        "fn": 2,
        "tn": 44
      },
      "follow_up": {
        "precision": 0.777778,
        "recall": 1.0,
        "f1": 0.875,
        "support": {
          "positive": 7,
          "negative": 42
        },
        "tp": 7,
        "fp": 2,
        "fn": 0,
        "tn": 40
      },
      "needs_clarification": {
        "precision": 1.0,
        "recall": 0.833333,
        "f1": 0.909091,
        "support": {
          "positive": 6,
          "negative": 43
        },
        "tp": 5,
        "fp": 0,
        "fn": 1,
        "tn": 43
      },
      "ask_source": {
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "support": {
          "positive": 10,
          "negative": 39
        },
        "tp": 10,
        "fp": 0,
        "fn": 0,
        "tn": 39
      },
      "multi_question": {
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "support": {
          "positive": 6,
          "negative": 43
        },
        "tp": 6,
        "fp": 0,
        "fn": 0,
        "tn": 43
      },
      "complex": {
        "precision": 0.857143,
        "recall": 0.857143,
        "f1": 0.857143,
        "support": {
          "positive": 7,
          "negative": 42
        },
        "tp": 6,
        "fp": 1,
        "fn": 1,
        "tn": 41
      }
    },
    "micro": {
      "precision": 0.925,
      "recall": 0.902439,
      "f1": 0.91358,
      "tp": 37,
      "fp": 3,
      "fn": 4
    },
    "macro": {
      "f1": 0.898539
    },
    "exact_match_accuracy": 0.857143
  },
  "heldout": {
    "rows": 30,
    "per_signal": {
      "soft_doubt": {
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
      },
      "follow_up": {
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
      "needs_clarification": {
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
      "ask_source": {
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
        "precision": 0.833333,
        "recall": 1.0,
        "f1": 0.909091,
        "support": {
          "positive": 5,
          "negative": 25
        },
        "tp": 5,
        "fp": 1,
        "fn": 0,
        "tn": 24
      }
    },
    "micro": {
      "precision": 0.961538,
      "recall": 0.833333,
      "f1": 0.892857,
      "tp": 25,
      "fp": 1,
      "fn": 5
    },
    "macro": {
      "f1": 0.855219
    },
    "exact_match_accuracy": 0.8
  }
}
```
