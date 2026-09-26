# Research Journal (Example)

This file contains interpretations, insights, and conclusions from the LoRA rank ablation experiment. Unlike history.md, this focuses on understanding rather than chronology.

---

## 2025-01-15 — Experiment Complete: Rank 16 Optimal for SST-2

### Hypothesis Assessment: **Supported**

Our hypothesis that "LoRA rank 16 will provide the best accuracy/efficiency tradeoff" was confirmed by the results. Rank 16 achieved 0.874 accuracy while rank 32 only reached 0.875 (+0.1%), despite requiring 19% more training time and memory.

### Key Findings

#### 1. Performance Saturation Between Rank 16-32

The marginal gain from rank 16 to 32 (0.001 accuracy) suggests we've reached the capacity limit useful for this task. This saturation point indicates:

- **SST-2 complexity ceiling**: The task may not require high-rank adaptations. Sentiment classification on this dataset appears to need relatively simple feature transformations.
- **Diminishing returns**: The cost/benefit ratio strongly favors rank 16.

#### 2. Rank 4 Surprisingly Competitive

Rank 4 achieved 0.866 accuracy (only -0.8% behind the best), which was unexpected. This suggests:

- **Low intrinsic dimensionality**: The task-specific adaptation may live in a low-dimensional subspace. This aligns with recent LoRA theory suggesting many NLP tasks have low effective rank.
- **Deployment opportunity**: For extremely memory-constrained environments (edge devices, mobile), rank 4 could be viable with acceptable performance degradation.

#### 3. Linear Scaling of Resources

Training time and memory scaled approximately linearly with rank:
- Rank 4: 3.8h, 7.1GB
- Rank 8: 4.1h, 7.6GB  
- Rank 16: 4.36h, 8.2GB
- Rank 32: 5.2h, 9.8GB

This predictable scaling is useful for resource planning in future experiments.

#### 4. All Ranks Beat Baseline Substantially

Even rank 4 achieved +1.5% over baseline (0.853). This suggests:
- **LoRA effectiveness**: Parameter-efficient fine-tuning works well for this task
- **Baseline quality**: The unfine-tuned RoBERTa baseline had room for improvement

### Unexpected Results

**Lower ranks more competitive than expected**: We anticipated a steeper performance drop at rank 4-8. The strong performance of low ranks was surprising and valuable.

**No convergence issues**: All ranks converged smoothly without instability, suggesting our learning rate (2e-4) and training schedule (3 epochs) were appropriate across the rank spectrum.

### Limitations and Caveats

1. **Single-task evaluation**: SST-2 is a relatively simple binary sentiment classification task. Results may not generalize to:
   - Multi-class classification
   - Generation tasks
   - More complex reasoning tasks
   - Other GLUE tasks (e.g., MNLI, QQP)

2. **Single learning rate**: We fixed LR at 2e-4. Optimal learning rates may vary by rank, potentially changing the relative performance.

3. **No statistical significance testing**: Single seed (42) means we cannot assess variance. Results could be seed-dependent.

4. **No inference latency measurement**: We optimized for training efficiency and accuracy, but deployment inference speed could favor different ranks.

5. **Architecture-specific**: RoBERTa-base findings may not transfer to:
   - Larger models (RoBERTa-large, GPT-2, T5)
   - Smaller models
   - Different architectures (encoder-only vs decoder-only)

### Theoretical Implications

The strong performance of low ranks (especially rank 4) supports the hypothesis that task-specific adaptations for fine-tuning exist in low-dimensional subspaces. This aligns with:

- **Intrinsic dimensionality research** (Li et al., 2018)
- **LoRA theoretical analysis** (Hu et al., 2021)
- **Low-rank adaptation principles**

### Recommended Next Steps

#### Immediate Follow-ups

1. **Learning rate ablation with rank 16**: Test LRs [1e-4, 2e-4, 5e-4, 1e-3] to optimize the chosen rank
   
2. **Multi-seed validation**: Run 3-5 seeds to quantify variance and confirm rank 16's superiority is statistically significant

3. **Inference latency study**: Measure actual deployment performance across ranks to complete the efficiency picture

#### Broader Research Directions

1. **Cross-task validation**: Test rank 16 on other GLUE tasks (MNLI, QNLI, QQP) to validate generalization
   
2. **Model scaling**: Repeat ablation with RoBERTa-large to see if optimal rank changes with model size
   
3. **Rank 4 deep dive**: Investigate why rank 4 performs so well - analyze learned weight matrices, visualize adaptation subspace

4. **Hybrid approaches**: Explore variable ranks per layer (e.g., lower ranks for early layers, higher for later layers)

### Production Recommendation

**Use rank 16 for production deployments** targeting maximum accuracy with reasonable efficiency.

**Exception cases:**
- **Extreme memory constraints**: Use rank 8 (acceptable -0.3% accuracy tradeoff)
- **Edge/mobile deployment**: Consider rank 4 (-0.8% accuracy but significantly lighter)
- **Maximum accuracy regardless of cost**: Rank 32 offers +0.1% if critical

### Conclusion

This experiment successfully identified rank 16 as the optimal choice for LoRA fine-tuning of RoBERTa-base on SST-2. The clear saturation pattern and predictable resource scaling provide actionable guidance for future experiments. The surprising competitiveness of low ranks opens interesting research directions on the intrinsic dimensionality of fine-tuning tasks.

**Overall confidence in conclusions: High** - Clear trends, substantial improvements over baseline, hypothesis confirmed. Main limitation is single-task evaluation; cross-task validation would increase confidence further.

---
