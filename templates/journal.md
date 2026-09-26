# Experiment Journal

This file records interpretations, insights, and conclusions.

## Format Guidelines

- Focus on "why" and "what does this mean", not just "what happened"
- Compare results to hypotheses
- Note unexpected findings
- Suggest follow-up experiments
- Document limitations

---

## Final Conclusions

[Written after experiment completes]

### Hypothesis Assessment

[Was your hypothesis supported, refuted, or unclear?]

### Key Findings

[What did you learn?]

1. [Finding 1]
2. [Finding 2]

### Unexpected Results

[Anything surprising?]

### Limitations

[What conclusions can you NOT make?]

1. [Limitation 1]
2. [Limitation 2]

### Recommended Next Steps

[What should be investigated next?]

1. [Next experiment 1]
2. [Next experiment 2]

---

## Intermediate Observations

[Optional: notes during execution]

### [YYYY-MM-DD] — Observation

[Any interesting observations during training or evaluation]

---

## Example Entry (Remove This)

## Final Conclusions

### Hypothesis Assessment

**Hypothesis**: LoRA rank 16+ would saturate performance gains.

**Result**: Supported. Rank 16 achieved 87.4% accuracy. Rank 32 only improved to 87.5% (+0.1%), not worth the 2× memory cost.

### Key Findings

1. Rank 16 provides the best accuracy/efficiency tradeoff
2. Ranks below 8 significantly hurt performance (-3% accuracy)
3. Memory usage scales linearly with rank as expected
4. Training time increased less than expected (rank 32 only +15% vs rank 8)

### Unexpected Results

- Rank 4 was more effective than anticipated (only -1.5% vs baseline)
- Could be useful for extremely memory-constrained deployment

### Limitations

1. Only tested on one dataset (GLUE SST-2)
2. Only tested one base model (RoBERTa-base)
3. Did not test interaction with other hyperparameters (learning rate, etc.)
4. Did not measure inference latency

### Recommended Next Steps

1. **High Priority**: Learning rate ablation with rank 16
   - Hypothesis: Default LR may not be optimal for rank 16
   
2. **Medium Priority**: Generalization check across GLUE tasks
   - Verify rank 16 is optimal for other tasks
   
3. **Low Priority**: Inference latency benchmark
   - Measure actual deployment impact of different ranks

---
