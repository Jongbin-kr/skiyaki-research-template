# Grill Me Skill

## Purpose

Clarify experimental decisions through focused questioning before creating detailed plans.

## When to Use

- User request lacks clear research objective
- Baseline for comparison is undefined
- Success criteria are not specified
- Important hyperparameters are unspecified
- Ablation scope is ambiguous

## When NOT to Use

- Information is already in project-plan.md
- Information is in recent experiment plans
- Question is about implementation details (defer to planning phase)

## Procedure

1. **Identify Gaps**:
   - Check project-plan.md for stable configuration
   - Review recent experiments for similar work
   - List unknowns that affect experiment design

2. **Prioritize Questions**:
   - Focus on research objective and hypothesis
   - Then baseline and primary metric
   - Then success criteria
   - Then experimental parameters
   - Ask one question at a time

3. **Handle Responses**:
   - If answer is vague, ask for specifics
   - If answer is "I don't know", suggest reasonable defaults
   - If answer conflicts with past experiments, clarify intent
   - If answer is clear, move to next question

4. **Completion**:
   - Stop when research objective, baseline, metric, and success criteria are clear
   - Document resolved decisions for plan creation
   - Return summary to Main Agent

## Output

- Resolved research objective
- Baseline for comparison
- Primary and secondary metrics
- Success criteria
- Key experimental parameters
- Documented assumptions and defaults
