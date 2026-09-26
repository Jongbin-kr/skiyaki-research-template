# Research Clarification Policy

## Purpose

This document defines the strategy for systematically clarifying research objectives through targeted questioning. Use this policy to guide the grill-me skill workflow.

---

## Question Priority Order

Ask questions in this order to efficiently resolve critical experimental decisions:

### 1. Metric Definition (HIGHEST PRIORITY)

**Why First:** Without clear metrics, no experiment can be evaluated objectively.

**Key Questions:**
- "What metric(s) will you use to evaluate success?"
- "Is this measured on validation set, test set, or both?"
- "Are there secondary metrics to track alongside the primary metric?"

**Common Vague Answers & Follow-ups:**
- "Make it better" → "Better according to which metric? Accuracy, F1, perplexity, BLEU?"
- "Good performance" → "What threshold or improvement would indicate good performance?"
- "Industry standard" → "Which specific metric is standard for this task?"

---

### 2. Baseline Identification (SECOND PRIORITY)

**Why Second:** Comparisons require a reference point. Without a baseline, improvements cannot be measured.

**Key Questions:**
- "What baseline will you compare against?"
- "Is the baseline a prior experiment, a known model, or a simple heuristic?"
- "Do you have baseline metric values, or do we need to establish them?"

**Common Vague Answers & Follow-ups:**
- "The current model" → "Which specific experiment or checkpoint should I use as baseline?"
- "Standard approach" → "Can you name the specific model or configuration?"
- "Previous work" → "Do you have run IDs or results I should reference?"

**Baseline Discovery:**
- Check `experiments/*/results.yaml` for comparable past experiments
- Check `project-log.md` for documented baselines
- If no baseline exists, suggest: "Should we first run a baseline experiment?"

---

### 3. Success Criteria (THIRD PRIORITY)

**Why Third:** Defines when to stop iterating and when an experiment achieves its goal.

**Key Questions:**
- "What would make this experiment successful?"
- "Are you looking for statistical significance, absolute improvement, or qualitative insight?"
- "Is there a minimum improvement threshold?"

**Common Vague Answers & Follow-ups:**
- "Better than baseline" → "By how much? Any improvement, or a specific percentage?"
- "See what happens" → "Are you exploring broadly, or testing a specific hypothesis?"
- "Competitive results" → "Competitive with what? A leaderboard benchmark or internal model?"

**Success Criteria Types:**
- **Absolute threshold:** "Accuracy > 85%"
- **Relative improvement:** "5% better than baseline"
- **Statistical significance:** "p < 0.05 on paired t-test"
- **Exploratory:** "Understand which LoRA ranks work best" (no numeric threshold)

---

### 4. Experimental Parameters (LOWEST PRIORITY)

**Why Last:** Parameters can often use reasonable defaults. Only ask if critical to design.

**Key Questions:**
- "Which hyperparameters are you interested in varying?"
- "Do you have preferred ranges or values?"
- "Are there hardware constraints (GPU memory, time limits)?"

**When to Ask:**
- Ablation studies (which factors to vary?)
- Architecture choices (model size, number of layers)
- Training regimes (learning rate ranges, batch sizes)

**When to Defer:**
- Implementation details ("How should I structure the code?")
- Optimization tricks ("Should I use gradient accumulation?")
- Logging preferences ("How often to log?")

---

## Stable Project Configuration

These settings are defined in `project-plan.md` and **MUST NEVER be re-asked** during grill-me sessions:

### Infrastructure Settings
- **W&B entity** (`wandb.entity`) - Organization or user account
- **W&B project** (`wandb.project`) - Project name for experiment tracking
- **Hugging Face namespace** (`huggingface.namespace`) - Organization/user for model uploads
- **SSH host** (`execution.ssh_host`) - Remote server alias
- **Remote project root** (`execution.remote_project_root`) - Remote working directory
- **Slurm partition** (`slurm.partition`) - Default cluster partition
- **Slurm account** (`slurm.account`) - Compute allocation account
- **Slurm QoS** (`slurm.qos`) - Quality of service tier

### Policy Settings
- **Environment manager** (`environment.manager`) - miniconda, uv, or venv
- **Execution target** (`execution.default_target`) - local or ssh
- **GPU requirements** (`execution.require_slurm_for_gpu`) - Slurm enforcement
- **CPU requirements** (`execution.require_slurm_for_cpu_heavy`) - Slurm enforcement
- **W&B mode** (`wandb.mode`) - online or offline
- **HF visibility** (`huggingface.private`) - Default model privacy
- **Checkpoint policy** (`huggingface.push_policy`) - When to upload models

### How to Use Stable Settings

**DO:**
- Read `project-plan.md` at the start of grill-me
- Reference these settings when planning experiments
- Assume they are correct and current

**DON'T:**
- Ask "What's your W&B entity?" if it's in project-plan.md
- Ask "Should I use Slurm?" if policies are already defined
- Ask "Where should I upload models?" if namespace is configured

**Exception:** If project-plan.md is missing or incomplete, asking about infrastructure is appropriate.

---

## Termination Criteria

Stop questioning when all critical experimental decisions are resolved:

### Minimum Requirements for Completion

You **MUST** have clear answers to:
1. ✅ **Metric**: Primary evaluation metric is defined
2. ✅ **Baseline**: Comparison reference is identified
3. ✅ **Success Criteria**: Definition of successful outcome exists

You **SHOULD** have clear answers to (ask if relevant):
4. ✅ **Experimental Scope**: What is being varied/tested
5. ✅ **Parameters**: Key hyperparameters or ranges (if applicable)

### Signs You Should Stop

- All three minimum requirements are satisfied
- User says "that's enough" or "let's move forward"
- Follow-up questions would be about implementation details
- Further questions require experimentation to answer

### Signs You Should Continue

- User answers "I don't know" to metric or baseline questions
- Success criteria are still vague ("better results")
- Experimental scope is ambiguous ("try different settings")
- Critical information conflicts with project history

---

## Handling Vague Answers

### Strategy 1: Request Specificity

**Vague:** "I want to improve the model"  
**Follow-up:** "Improve according to which metric? Accuracy, F1 score, perplexity?"

**Vague:** "Make it faster"  
**Follow-up:** "Faster training time, faster inference, or both? By how much?"

**Vague:** "Try some different values"  
**Follow-up:** "Which parameters should I vary? Learning rate, batch size, model size?"

### Strategy 2: Offer Concrete Options

**Vague:** "Standard baseline"  
**Follow-up:** "I see three options: (1) your prior experiment X, (2) the unmodified base model, (3) the published benchmark. Which should I use?"

**Vague:** "Good performance"  
**Follow-up:** "Should I aim for: (1) 90%+ accuracy, (2) 5% improvement over baseline, or (3) state-of-the-art results?"

### Strategy 3: Propose Reasonable Defaults

**Vague:** "Whatever makes sense"  
**Response:** "I'll use accuracy on the validation set as the primary metric, with loss as a secondary metric. Does that work?"

**Vague:** "I'm not sure about the threshold"  
**Response:** "Typical improvements in this domain are 2-5%. Should I aim for at least 3% improvement over baseline?"

### Strategy 4: Check Project History

**Vague:** "Like we did before"  
**Action:** Check `experiments/*/plan.md` and `project-log.md` for prior decisions

**Vague:** "The usual setup"  
**Action:** Reference project-plan.md for established evaluation principles

### Strategy 5: Escalate Unknowns

If the user genuinely doesn't know critical information:

**For Metrics:**
- Suggest domain-standard metrics
- Offer to research appropriate evaluation approaches
- Propose exploratory experiment to determine suitable metrics

**For Baselines:**
- Suggest running a baseline establishment experiment first
- Propose using the simplest reasonable model as reference
- Offer to check literature for standard comparisons

**For Success Criteria:**
- Suggest treating the experiment as exploratory
- Propose documenting observations rather than pass/fail criteria
- Offer iterative refinement after initial results

---

## Anti-Patterns to Avoid

### ❌ Don't: Re-ask Stable Configuration
**Wrong:** "What's your W&B entity for this experiment?"  
**Right:** Read project-plan.md and use the configured entity

### ❌ Don't: Ask Implementation Questions During Grill
**Wrong:** "Should I use bfloat16 or float16 for training?"  
**Right:** Defer to planning phase: "I'll determine the optimal dtype during plan creation"

### ❌ Don't: Over-specify Before Experimentation
**Wrong:** "What should the optimal learning rate be?"  
**Right:** "Are you searching for learning rate, or using a known good value?"

### ❌ Don't: Ask Multiple Questions at Once
**Wrong:** "What's your metric, baseline, and success criteria?"  
**Right:** Ask for metric first, then baseline after answer is clear

### ❌ Don't: Accept Contradictions Without Clarification
**Wrong:** User says "compare to experiment X" but also "this is a brand new approach"  
**Right:** "You mentioned comparing to X, but also that this is new. Should I compare to X's metrics, or establish a new baseline?"

---

## Example Grill Session

**Context:** User says "I want to train a smaller model"

### Round 1: Metric
**Agent:** "What metric will you use to evaluate the smaller model?"  
**User:** "Performance"  
**Agent:** "Performance measured by which metric? Accuracy, F1, perplexity, or something else?"  
**User:** "Accuracy on the test set"  
✅ Metric resolved: Test accuracy

### Round 2: Baseline
**Agent:** "What baseline will you compare the smaller model against?"  
**User:** "The current model"  
**Agent:** "Which specific experiment should I use? I see experiment-A (rank-16) and experiment-B (rank-32) in the history."  
**User:** "Use experiment-B"  
✅ Baseline resolved: experiment-B (rank-32)

### Round 3: Success Criteria
**Agent:** "What would make this smaller model experiment successful?"  
**User:** "If it's not much worse"  
**Agent:** "How much accuracy drop would be acceptable? Within 1%, 2%, or 5% of the baseline?"  
**User:** "Within 2% is fine"  
✅ Success criteria resolved: ≥ (baseline - 2%) accuracy

### Round 4: Parameters
**Agent:** "How much smaller should the model be? Reduced LoRA rank, fewer layers, or smaller base model?"  
**User:** "Try LoRA ranks 4 and 8"  
✅ Parameters resolved: Ablation over ranks [4, 8] vs baseline rank 32

**Result:** All critical decisions resolved. Ready to create experiment plan.

---

## Summary

**Question Priority:**
1. Metric (what to measure)
2. Baseline (what to compare against)
3. Success criteria (when to consider it successful)
4. Parameters (what to vary)

**Stable Settings:** Never re-ask for infrastructure configuration in project-plan.md

**Termination:** Stop when metric, baseline, and success criteria are clear

**Vague Answers:** Request specificity, offer options, propose defaults, check history, escalate unknowns

**Goal:** Efficient clarification with minimal user frustration, enabling confident experiment planning
