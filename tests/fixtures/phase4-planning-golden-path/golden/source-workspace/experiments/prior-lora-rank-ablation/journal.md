# Research Journal

## 2025-02-03 — Rank 16 Selected for Efficiency

### Hypothesis Assessment

Supported. Rank 16 reached `0.874` validation accuracy, only `0.001` below the rank-32 maximum of `0.875`, while rank 32 required `0.84` more training hours and `1.6 GB` more peak GPU memory.

### Findings

- All LoRA ranks exceeded the unfine-tuned `0.853` accuracy reference.
- Rank 16 is the efficiency-selected configuration under the plan's within-`0.002` selection rule.
- Rank 32 is the absolute accuracy maximum, not the recommended resource tradeoff.
- The structured measurements are recorded in [`results.yaml`](results.yaml); reproducible controls are in [`jobs/train.yaml`](jobs/train.yaml) and [`jobs/evaluate.yaml`](jobs/evaluate.yaml).

### Limitations

Only seed `17` was tested. The `0.001` difference between ranks 16 and 32 is too small to treat as stable without repeated seeds.

### Next Step and Duplication Assessment

A follow-up on the same model, dataset, LoRA technique, and overlapping rank range should be classified as a **near duplicate** if it narrows the matrix to `[8, 16, 32]` and adds multiple seeds. The narrower matrix and added seed coverage are the traceable differences; repeating `[4, 8, 16, 32]` at seed `17` would be an exact duplicate.
